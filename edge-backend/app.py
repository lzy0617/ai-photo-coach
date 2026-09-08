import os
import json
import logging
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from detector import AscendYoloDetector
from composition import analyze_composition
from image_quality import analyze_brightness
from services.vlm_client import VLMClient, VLMError


detector = None
vlm_client = None
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global detector, vlm_client

    detector = AscendYoloDetector(
        "/root/photo-ai/backend/models/yolov5s_nms.om",
        person_only=True
    )
    vlm_client = VLMClient()

    yield

    if vlm_client:
        vlm_client.close()
    if detector:
        detector.close()


app = FastAPI(
    title="AI Photography Assistant",
    version="0.1.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": "OrangePi AI Pro 20T",
        "accelerator": "Ascend 310B1",
        "model": "YOLOv5s"
    }


@app.post("/api/analyze-fast")
async def analyze_fast(
    image: UploadFile = File(...)
):
    data = await image.read()

    with tempfile.NamedTemporaryFile(
        suffix=".jpg",
        delete=False
    ) as f:
        f.write(data)
        path = f.name

    try:
        detection = detector.detect(path)

        composition = analyze_composition(
            detection["image_width"],
            detection["image_height"],
            detection["persons"]
        )

        brightness = analyze_brightness(
            path
        )

        suggestions = list(
            composition.get(
                "suggestions",
                []
            )
        )

        return {
            "mode": "edge_fast",

            "backend": {
                "device":
                    "OrangePi AI Pro 20T",

                "accelerator":
                    "Ascend 310B1",

                "model":
                    "YOLOv5s"
            },

            "image": {
                "width":
                    detection["image_width"],

                "height":
                    detection["image_height"]
            },

            "detection": {
                "persons":
                    detection["persons"]
            },

            "composition":
                composition,

            "brightness":
                brightness,

            "suggestions":
                suggestions,

            "timing":
                detection["timing"]
        }

    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def _parse_metrics(raw_metrics: str):
    try:
        metrics = json.loads(raw_metrics)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="metrics 必须是合法 JSON") from exc

    if not isinstance(metrics, dict):
        raise HTTPException(status_code=422, detail="metrics 必须是 JSON 对象")

    persons = metrics.get("persons")
    if persons is None and isinstance(metrics.get("detection"), dict):
        persons = metrics["detection"].get("persons")
    if not isinstance(persons, list) or not isinstance(metrics.get("composition"), dict):
        raise HTTPException(
            status_code=422,
            detail="metrics 必须包含 YOLO persons 和 composition 数据",
        )
    return metrics


@app.post("/api/deep-analyze")
async def deep_analyze(
    image: UploadFile = File(...),
    metrics: str = Form(...),
):
    """Forward one user-selected YOLO/CV keyframe to the cloud VLM."""
    fast_analysis = _parse_metrics(metrics)
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="image 不能为空")
    if len(image_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="image 不能超过 20 MB")

    if vlm_client is None:
        logger.error("Deep analysis requested before VLM client initialization")
        return {
            "success": False,
            "mode": "deep",
            "error": "VLM_UNAVAILABLE",
            "message": "AI 深度分析暂时不可用",
            "fast_analysis": fast_analysis,
        }

    try:
        deep_analysis = await run_in_threadpool(
            vlm_client.analyze,
            image_bytes,
            fast_analysis,
        )
    except VLMError as exc:
        logger.warning("Deep analysis degraded to fast result: %s", exc)
        return {
            "success": False,
            "mode": "deep",
            "error": exc.code,
            "message": exc.public_message,
            "fast_analysis": fast_analysis,
        }
    except Exception:
        logger.exception("Unexpected deep analysis error")
        return {
            "success": False,
            "mode": "deep",
            "error": "VLM_UNAVAILABLE",
            "message": "AI 深度分析暂时不可用",
            "fast_analysis": fast_analysis,
        }

    return {
        "success": True,
        "mode": "deep",
        "fast_analysis": fast_analysis,
        "deep_analysis": deep_analysis,
    }
