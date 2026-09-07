import os
import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from detector import AscendYoloDetector
from composition import analyze_composition
from image_quality import analyze_brightness


detector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global detector

    detector = AscendYoloDetector(
        "/root/photo-ai/backend/models/yolov5s_nms.om",
        person_only=True
    )

    yield

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
