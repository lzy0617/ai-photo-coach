import importlib.util
import types
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from services.vlm_client import VLMTimeoutError


# Ascend runtime modules are only present on Orange Pi. The deep route test does
# not initialize or exercise the detector.
sys.modules.setdefault(
    "detector",
    types.SimpleNamespace(AscendYoloDetector=object),
)
APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("edge_backend_app", APP_PATH)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)


class SuccessfulVLM:
    def __init__(self):
        self.metrics = None

    def analyze(self, image_bytes, metrics):
        assert image_bytes == b"jpeg-data"
        self.metrics = metrics
        return {
            "scene": {"type": "portrait", "description": "户外人像"},
            "lighting": {"type": "side", "quality": "soft", "problem": None},
            "background": {"quality": "good", "distractions": []},
            "pose": {"quality": "natural", "problems": []},
            "suggestions": [],
        }


class TimedOutVLM:
    def analyze(self, image_bytes, metrics):
        raise VLMTimeoutError("late")


METRICS = {
    "detection": {"persons": [{"confidence": 0.96, "bbox_norm": {"x1": .4, "y1": .1, "x2": .7, "y2": .8}}]},
    "composition": {"status": "ok", "score": 78},
}


def test_deep_route_preserves_and_forwards_fast_analysis():
    fake = SuccessfulVLM()
    app_module.vlm_client = fake
    client = TestClient(app_module.app)

    response = client.post(
        "/api/deep-analyze",
        files={"image": ("frame.jpg", b"jpeg-data", "image/jpeg")},
        data={"metrics": __import__("json").dumps(METRICS)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["fast_analysis"] == METRICS
    assert fake.metrics == METRICS
    assert payload["deep_analysis"]["scene"]["type"] == "portrait"


def test_deep_route_timeout_degrades_without_losing_fast_analysis():
    app_module.vlm_client = TimedOutVLM()
    client = TestClient(app_module.app)

    response = client.post(
        "/api/deep-analyze",
        files={"image": ("frame.jpg", b"jpeg-data", "image/jpeg")},
        data={"metrics": __import__("json").dumps(METRICS)},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": False,
        "mode": "deep",
        "error": "VLM_TIMEOUT",
        "message": "AI 深度分析请求超时，请稍后重试",
        "fast_analysis": METRICS,
    }


def test_deep_route_rejects_metrics_without_yolo_data():
    app_module.vlm_client = SuccessfulVLM()
    response = TestClient(app_module.app).post(
        "/api/deep-analyze",
        files={"image": ("frame.jpg", b"jpeg-data", "image/jpeg")},
        data={"metrics": '{"composition": {}}'},
    )
    assert response.status_code == 422
