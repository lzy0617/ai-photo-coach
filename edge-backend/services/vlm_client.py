import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional

import httpx


logger = logging.getLogger(__name__)


class VLMError(Exception):
    """Base error for a recoverable cloud VLM failure."""

    code = "VLM_UNAVAILABLE"
    public_message = "AI 深度分析暂时不可用"


class VLMTimeoutError(VLMError):
    code = "VLM_TIMEOUT"
    public_message = "AI 深度分析请求超时，请稍后重试"


class VLMInvalidResponseError(VLMError):
    code = "VLM_INVALID_RESPONSE"
    public_message = "AI 深度分析返回格式异常，请稍后重试"


def _json_from_text(value: str) -> Any:
    text = value.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except (TypeError, ValueError):
        # Some model servers add a short sentence around the JSON object.
        decoder = json.JSONDecoder()
        starts = [position for position in (text.find("{"), text.find("[")) if position >= 0]
        if not starts:
            raise VLMInvalidResponseError("VLM content does not contain JSON")
        try:
            parsed, _ = decoder.raw_decode(text[min(starts):])
            return parsed
        except ValueError as exc:
            raise VLMInvalidResponseError("VLM content is not valid JSON") from exc


def _unwrap_payload(payload: Any) -> Dict[str, Any]:
    current = payload
    for _ in range(8):
        if isinstance(current, str):
            current = _json_from_text(current)
            continue

        if not isinstance(current, dict):
            raise VLMInvalidResponseError("VLM analysis must be a JSON object")

        if any(key in current for key in ("scene", "lighting", "background", "pose", "suggestions")):
            return current

        choices = current.get("choices")
        if isinstance(choices, list) and choices:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get("message")
                if isinstance(message, dict) and "content" in message:
                    current = message["content"]
                    continue

        for key in ("deep_analysis", "analysis", "result", "data", "output", "response", "content"):
            if key in current:
                current = current[key]
                break
        else:
            raise VLMInvalidResponseError("VLM response does not contain photography analysis")

    raise VLMInvalidResponseError("VLM response nesting is too deep")


def _section(value: Any, fields) -> Dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    result = {field: source.get(field) for field in fields}
    if isinstance(value, str) and fields:
        result[fields[0]] = value
    return result


def normalize_vlm_response(payload: Any) -> Dict[str, Any]:
    """Convert common ModelArts/model-server wrappers to the frontend contract."""
    analysis = _unwrap_payload(payload)

    raw_suggestions = analysis.get("suggestions", [])
    if not isinstance(raw_suggestions, list):
        raw_suggestions = []

    suggestions = []
    for index, item in enumerate(raw_suggestions):
        if isinstance(item, str) and item.strip():
            suggestions.append({
                "priority": index + 1,
                "type": "general",
                "action": item.strip(),
                "reason": "",
            })
        elif isinstance(item, dict):
            action = item.get("action") or item.get("suggestion") or item.get("advice")
            if not isinstance(action, str) or not action.strip():
                continue
            priority = item.get("priority", index + 1)
            if not isinstance(priority, (int, float)):
                priority = index + 1
            suggestions.append({
                "priority": priority,
                "type": item.get("type") if isinstance(item.get("type"), str) else "general",
                "action": action.strip(),
                "reason": item.get("reason") if isinstance(item.get("reason"), str) else "",
            })

    suggestions.sort(key=lambda item: item["priority"])
    background = _section(analysis.get("background"), ("quality", "distractions"))
    pose = _section(analysis.get("pose"), ("quality", "problems"))
    if not isinstance(background["distractions"], list):
        background["distractions"] = []
    if not isinstance(pose["problems"], list):
        pose["problems"] = []

    visual_expression = analysis.get("visual_expression", analysis.get("expression"))
    if isinstance(visual_expression, dict):
        visual_expression = (
            visual_expression.get("description")
            or visual_expression.get("summary")
            or visual_expression.get("quality")
        )
    if not isinstance(visual_expression, str):
        visual_expression = None

    return {
        "scene": _section(analysis.get("scene"), ("type", "description")),
        "lighting": _section(analysis.get("lighting"), ("type", "quality", "problem")),
        "background": background,
        "pose": pose,
        "visual_expression": visual_expression,
        "suggestions": suggestions,
    }


class VLMClient:
    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout_seconds: float = 90.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_url = api_url or os.getenv(
            "VLM_API_URL",
            "http://127.0.0.1:18000/analyze",
        )
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
        )

    def analyze(self, image_bytes: bytes, metrics: Dict[str, Any]) -> Dict[str, Any]:
        if not image_bytes:
            raise ValueError("image_bytes must not be empty")
        if not isinstance(metrics, dict):
            raise ValueError("metrics must be a JSON object")

        started = time.perf_counter()
        try:
            response = self._client.post(
                self.api_url,
                files={"image": ("frame.jpg", image_bytes, "image/jpeg")},
                data={"cv_metrics": json.dumps(metrics, ensure_ascii=False)},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("VLM request timed out: %s", self.api_url)
            raise VLMTimeoutError("VLM request timed out") from exc
        except httpx.HTTPStatusError as exc:
            logger.warning("VLM returned HTTP %s", exc.response.status_code)
            raise VLMError("VLM returned an HTTP error") from exc
        except httpx.RequestError as exc:
            logger.warning("Cannot connect to VLM: %s", exc)
            raise VLMError("Cannot connect to VLM") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("VLM returned malformed JSON")
            raise VLMInvalidResponseError("VLM returned malformed JSON") from exc

        result = normalize_vlm_response(payload)
        logger.info("VLM analysis completed in %.2f seconds", time.perf_counter() - started)
        return result

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
