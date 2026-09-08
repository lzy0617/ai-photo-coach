import asyncio
import gc
import io
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv(
    "QWEN_MODEL_PATH",
    "/home/ma-user/work/models/Qwen3-VL-8B-Instruct",
)
DEVICE = os.getenv("QWEN_DEVICE", "npu:0")
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_EDGE = int(os.getenv("VLM_MAX_IMAGE_EDGE", "1280"))
MAX_NEW_TOKENS = int(os.getenv("VLM_MAX_NEW_TOKENS", "768"))


def build_prompt(metrics: Dict[str, Any]) -> str:
    metrics_json = json.dumps(metrics, ensure_ascii=False, separators=(",", ":"))
    return f"""你是一名专业但务实的人像摄影指导老师。请结合图片与下面由 YOLO/CV 计算出的数据进行分析。

YOLO/CV 数据是几何事实，不要重新估计或修改人物 bbox、位置、人物大小、三分法距离、左右留白和 headroom。你的任务是补充视觉语义：场景、背景干扰物、人物头部附近的杆子或路牌、光线方向与软硬、面部受光、姿态自然度和画面表达。

YOLO/CV 数据：
{metrics_json}

只输出一个合法 JSON 对象，不要输出 Markdown、解释或代码块。无法判断的单值字段使用 null，列表使用 []。suggestions 最多 3 条，并按重要程度排序：
{{
  "scene": {{"type": "英文短标签或 null", "description": "中文场景描述或 null"}},
  "lighting": {{"type": "英文短标签或 null", "quality": "英文短标签或 null", "problem": "中文问题描述或 null"}},
  "background": {{"quality": "英文短标签或 null", "distractions": ["中文干扰物描述"]}},
  "pose": {{"quality": "英文短标签或 null", "problems": ["中文姿态问题"]}},
  "visual_expression": "中文画面表达总结或 null",
  "suggestions": [
    {{"priority": 1, "type": "background|lighting|pose|composition|general", "action": "可执行的中文动作", "reason": "简短中文原因"}}
  ]
}}"""


def parse_model_json(text: str) -> Dict[str, Any]:
    content = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.I | re.S)
    if fenced:
        content = fenced.group(1).strip()

    try:
        result = json.loads(content)
    except ValueError:
        start = content.find("{")
        if start < 0:
            raise ValueError("model output does not contain a JSON object")
        try:
            result, _ = json.JSONDecoder().raw_decode(content[start:])
        except ValueError as exc:
            raise ValueError("model output is not valid JSON") from exc

    if not isinstance(result, dict):
        raise ValueError("model output must be a JSON object")
    return result


class QwenVLService:
    def __init__(self) -> None:
        self.model = None
        self.processor = None
        self.torch = None

    def load(self) -> None:
        if self.model is not None:
            return
        if not os.path.isdir(MODEL_PATH):
            raise RuntimeError(f"Qwen model directory does not exist: {MODEL_PATH}")

        # torch_npu registers the npu device on the ModelArts PyTorch runtime.
        import torch
        import torch_npu  # noqa: F401
        from transformers import AutoModelForImageTextToText, AutoProcessor

        logger.info("Loading Qwen3-VL from %s onto %s", MODEL_PATH, DEVICE)
        started = time.perf_counter()
        self.processor = AutoProcessor.from_pretrained(
            MODEL_PATH,
            local_files_only=True,
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL_PATH,
            dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            local_files_only=True,
        ).to(DEVICE)
        self.model.eval()
        self.torch = torch
        logger.info("Qwen3-VL loaded in %.2f seconds", time.perf_counter() - started)

    def analyze(self, image: Image.Image, metrics: Dict[str, Any]) -> Dict[str, Any]:
        if self.model is None or self.processor is None or self.torch is None:
            raise RuntimeError("Qwen3-VL is not loaded")

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": build_prompt(metrics)},
            ],
        }]
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(DEVICE)

        started = time.perf_counter()
        with self.torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
            )

        generated_ids = [
            output[len(input_ids):]
            for input_ids, output in zip(inputs["input_ids"], output_ids)
        ]
        text = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        result = parse_model_json(text)
        logger.info("Qwen3-VL inference completed in %.2f seconds", time.perf_counter() - started)
        return result

    def close(self) -> None:
        self.model = None
        self.processor = None
        gc.collect()
        if self.torch is not None and hasattr(self.torch, "npu"):
            self.torch.npu.empty_cache()


service = QwenVLService()
inference_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await run_in_threadpool(service.load)
    yield
    service.close()


app = FastAPI(
    title="Qwen3-VL Photography Analysis",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {
        "status": "ok" if service.model is not None else "loading",
        "model": os.path.basename(MODEL_PATH.rstrip("/")),
        "device": DEVICE,
    }


@app.post("/analyze")
async def analyze(
    image: UploadFile = File(...),
    cv_metrics: str = Form(...),
):
    try:
        metrics = json.loads(cv_metrics)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="cv_metrics must be valid JSON") from exc
    if not isinstance(metrics, dict):
        raise HTTPException(status_code=422, detail="cv_metrics must be a JSON object")
    if len(cv_metrics.encode("utf-8")) > 512 * 1024:
        raise HTTPException(status_code=413, detail="cv_metrics is too large")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="image must not be empty")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image is too large")

    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            frame = ImageOps.exif_transpose(source).convert("RGB")
            frame.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE), Image.Resampling.LANCZOS)
            frame.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="image cannot be decoded") from exc

    try:
        # One NPU and one shared model: queue requests instead of running generate concurrently.
        async with inference_lock:
            result = await run_in_threadpool(service.analyze, frame, metrics)
    except ValueError as exc:
        logger.warning("Qwen returned invalid structured output: %s", exc)
        raise HTTPException(status_code=502, detail="model returned invalid JSON") from exc
    except Exception as exc:
        logger.exception("Qwen inference failed")
        raise HTTPException(status_code=503, detail="model inference failed") from exc
    finally:
        frame.close()

    return {
        "success": True,
        "model": os.path.basename(MODEL_PATH.rstrip("/")),
        "analysis": result,
    }
