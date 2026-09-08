import json

import httpx
import pytest

from services.vlm_client import (
    VLMClient,
    VLMInvalidResponseError,
    VLMTimeoutError,
    normalize_vlm_response,
)


def test_client_sends_image_and_cv_metrics_and_normalizes_response():
    captured = {}

    def handler(request):
        captured["content"] = request.content
        return httpx.Response(200, json={
            "result": """```json
            {"scene":{"type":"portrait","description":"户外人像"},
             "lighting":{"type":"side","quality":"soft","problem":"右脸略暗"},
             "background":{"quality":"poor","distractions":["路牌"]},
             "pose":{"quality":"natural","problems":[]},
             "suggestions":[{"priority":1,"type":"background","action":"向右移动半步","reason":"避开路牌"}]}
            ```""",
        })

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = VLMClient(api_url="http://vlm.test/analyze", client=http_client)
    metrics = {"detection": {"persons": []}, "composition": {"status": "no_person"}}

    result = client.analyze(b"jpeg-data", metrics)

    body = captured["content"].decode("utf-8")
    assert 'name="image"' in body
    assert 'name="cv_metrics"' in body
    assert json.dumps(metrics, ensure_ascii=False) in body
    assert result["scene"]["description"] == "户外人像"
    assert result["suggestions"][0]["action"] == "向右移动半步"


def test_timeout_becomes_recoverable_vlm_error():
    def handler(request):
        raise httpx.ReadTimeout("late", request=request)

    client = VLMClient(
        api_url="http://vlm.test/analyze",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(VLMTimeoutError):
        client.analyze(b"jpeg-data", {"persons": [], "composition": {}})


def test_malformed_http_json_becomes_invalid_response_error():
    client = VLMClient(
        api_url="http://vlm.test/analyze",
        client=httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"not-json")
        )),
    )
    with pytest.raises(VLMInvalidResponseError):
        client.analyze(b"jpeg-data", {"persons": [], "composition": {}})


@pytest.mark.parametrize("payload", ["not json", {}, {"result": "still not json"}])
def test_invalid_model_output_is_rejected(payload):
    with pytest.raises(VLMInvalidResponseError):
        normalize_vlm_response(payload)


def test_string_suggestions_are_normalized():
    result = normalize_vlm_response({"analysis": {"suggestions": ["换一个角度"]}})
    assert result["suggestions"] == [{
        "priority": 1,
        "type": "general",
        "action": "换一个角度",
        "reason": "",
    }]
