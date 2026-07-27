"""The AI must never be able to take the request down."""

from __future__ import annotations

import io

import anthropic
import httpx
import pytest
from PIL import Image

from analysis import ai
from analysis.pipeline import analyse


def _image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (1280, 720), (200, 60, 40)).save(buffer, "JPEG")
    return buffer.getvalue()


class _FakeMessages:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def create(self, **_):
        raise self._exc


class _FakeClient:
    def __init__(self, exc: Exception) -> None:
        self.messages = _FakeMessages(exc)

    async def close(self) -> None:
        return None


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc", "code"),
    [
        (anthropic.APIConnectionError(request=_request()), "ai_unreachable"),
        (
            anthropic.RateLimitError(
                "rate limited",
                response=httpx.Response(429, request=_request()),
                body=None,
            ),
            "ai_rate_limited",
        ),
        (
            anthropic.NotFoundError(
                "no such model",
                response=httpx.Response(404, request=_request()),
                body=None,
            ),
            "ai_model_not_found",
        ),
        (
            anthropic.APIStatusError(
                "server error",
                response=httpx.Response(503, request=_request()),
                body=None,
            ),
            "ai_api_error",
        ),
        (RuntimeError("something unexpected"), "ai_failed"),
    ],
)
async def test_every_ai_failure_still_returns_the_deterministic_analysis(
    monkeypatch, exc: Exception, code: str
) -> None:
    monkeypatch.setattr(ai, "is_configured", lambda: True)
    monkeypatch.setattr(ai, "_client", lambda: _FakeClient(exc))

    result = await analyse(_image_bytes(), include_ai=True, use_cache=False)

    assert result["success"] is True
    assert result["ai"] is None
    assert result["aiError"]["code"] == code
    # The whole point: the measurements are all still there.
    assert result["scores"]["overall"] >= 0
    assert result["color"]["palette"]
    assert result["quality"]["sharpness"] is not None


@pytest.mark.asyncio
async def test_a_missing_key_degrades_rather_than_erroring(monkeypatch) -> None:
    monkeypatch.setattr(ai, "is_configured", lambda: False)
    result = await analyse(_image_bytes(), include_ai=True, use_cache=False)
    assert result["ai"] is None
    assert result["aiError"]["code"] == "ai_not_configured"
    assert "Every measurement below is live" in result["aiError"]["message"]
    assert result["scores"]["colorImpact"] is not None


@pytest.mark.asyncio
async def test_ai_disabled_by_config(monkeypatch) -> None:
    monkeypatch.setattr(ai.settings, "ai_enabled", False)
    result, error, usage = await ai.analyse(Image.new("RGB", (100, 100)), {}, {})
    assert result is None
    assert error["code"] == "ai_disabled"
    assert usage is None


def test_the_output_schema_forbids_extra_fields_and_requires_every_key() -> None:
    schema = ai.OUTPUT_SCHEMA["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def test_the_system_prompt_is_frozen() -> None:
    """The cached prefix must not contain anything that varies per request."""
    for volatile in ("http", "{", "}", "202"):
        assert volatile not in ai.SYSTEM_PROMPT, f"'{volatile}' would break the prompt cache"


def test_grounding_payload_excludes_pixel_coordinates() -> None:
    metrics = {
        "image": {"width": 1280},
        "text": {"blocks": [{"text": "HI", "bboxPx": {"x": 1}, "capHeightPx": 100}]},
        "faces": {"detector": "yunet", "count": 1, "faces": [{"areaPercent": 10, "bboxPx": {"x": 1}}]},
    }
    payload = ai._grounding_payload(metrics, {"overall": 70})
    assert "bboxPx" not in payload["text"]["blocks"][0]
    assert "bboxPx" not in payload["faces"]["faces"][0]
    assert payload["scores"]["overall"] == 70


def test_cost_estimate_uses_published_rates() -> None:
    # 1M input + 1M output at Opus 4.8 rates.
    assert ai._cost(1_000_000, 1_000_000, 0, 0) == pytest.approx(30.0)
    assert ai._cost(0, 0, 1_000_000, 0) == pytest.approx(0.5)
