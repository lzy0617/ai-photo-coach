import importlib.util
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


CLOUD_VLM = Path(__file__).resolve().parents[1]
if str(CLOUD_VLM) not in sys.path:
    sys.path.insert(0, str(CLOUD_VLM))
spec = importlib.util.spec_from_file_location("cloud_vlm_app", CLOUD_VLM / "app.py")
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)


def test_prompt_treats_cv_geometry_as_fact():
    prompt = app_module.build_prompt({"composition": {"headroom": {"ratio": .1}}})
    assert "不要重新估计" in prompt
    assert '"ratio":0.1' in prompt
    assert "只输出一个合法 JSON 对象" in prompt


def test_json_code_fence_is_accepted():
    result = app_module.parse_model_json('```json\n{"scene":{"type":"portrait"}}\n```')
    assert result["scene"]["type"] == "portrait"


class FakeService:
    model = object()

    def analyze(self, image, metrics):
        assert image.mode == "RGB"
        assert metrics["composition"]["score"] == 80
        return {"scene": {"type": "portrait", "description": "户外人像"}, "suggestions": []}


def test_analyze_accepts_multipart_image_and_metrics():
    original = app_module.service
    app_module.service = FakeService()
    try:
        image = __import__("PIL.Image").Image.new("RGB", (8, 8), "white")
        output = __import__("io").BytesIO()
        image.save(output, format="JPEG")
        response = TestClient(app_module.app).post(
            "/analyze",
            files={"image": ("test.jpg", output.getvalue(), "image/jpeg")},
            data={"cv_metrics": json.dumps({"composition": {"score": 80}})},
        )
    finally:
        app_module.service = original

    assert response.status_code == 200
    assert response.json()["analysis"]["scene"]["description"] == "户外人像"
