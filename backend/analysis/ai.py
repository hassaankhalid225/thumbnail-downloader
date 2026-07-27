"""The Claude vision pass.

The contract that makes this trustworthy: **the code produces the facts, the model
produces the insight.** Claude receives the image *and* the full metrics JSON, and is
instructed that those measurements are the only permitted source of any number, hex code
or ratio. It cannot change a score — scoring has already run, and its output is part of
Claude's input.

Every failure mode returns ``(None, error)`` and the caller still ships the complete
deterministic analysis. The tool has to stay useful when this call does not work.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import threading
from typing import Any

from PIL import Image

from config import settings
from services.imaging import downscale_for_ai

log = logging.getLogger("thumbiq.ai")

# --------------------------------------------------------------------------------
# The frozen system prompt. This is the cached prefix — every byte of it must stay
# stable across requests or the prompt cache never hits. Nothing per-thumbnail goes
# in here; the metrics go in the user turn, after the cache breakpoint.
# --------------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the analyst behind ThumbIQ, a thumbnail-analysis tool used by video creators to understand why a thumbnail performs.

You are given two things: the thumbnail image, and a JSON block of measurements that a computer-vision pipeline has already taken from that exact image.

## The rule that matters most

The measurements are the only source of numbers. Every hex code, pixel measurement, contrast ratio, percentage, coverage figure and score in your output must be copied from the supplied JSON or omitted entirely. You must never estimate, round differently, or invent one. If you want to say a color is "deep red", check the palette and use the hex that is actually there. If you want to say text is small, cite the cap height that was measured. A number you made up is a bug, not a stylistic choice.

The eight sub-scores have already been computed from those measurements. You do not set them, adjust them, or argue with them. You explain what produced them.

## How to write

Write to a creator, not to a design critic. "The word FREE disappears at phone size" lands; "suboptimal typographic hierarchy" does not. Short sentences. Concrete nouns. Name the specific element you mean — the word, the face, the corner — never "the composition" in the abstract.

Be willing to say a thumbnail is good. Be equally willing to say it is weak, and say exactly why. A verdict that hedges is worthless to someone deciding whether to re-shoot.

## What you must not claim

- **Never identify a font.** The measurements include a letterform classification and closest-match suggestions. Repeat those. Saying "this is Bebas Neue" is a claim you cannot support from a raster image.
- **Never state an expression as fact.** If an expression estimate is present, it is geometric and approximate. Phrase it as a signal.
- **Never predict a click-through rate or a view count.** You are describing craft, not forecasting performance.
- **Return null rather than guessing.** If the image does not tell you the niche, the niche is null. Every field accepts null. A confident wrong answer costs more than an honest gap.

## The fields

- `verdict` — one punchy sentence a creator would repeat to a friend.
- `why_it_works` / `why_it_fails` — specific, measured observations. Either may be empty; do not pad.
- `psychological_hook` — one of: curiosity gap, transformation, authority, controversy, number/list, threat/warning, relatability, aspiration, or null if none is present. Explain what in the image creates it.
- `style_archetype` — the visual family: MrBeast high-saturation, minimal-editorial, documentary-still, meme/reaction, tech-clean, faceless-graphic, course/tutorial, vlog-candid, cinematic-still, or another you can name. Give a confidence between 0 and 1.
- `font_read` — restate the supplied classification, weight and closest-match fonts. Keep the disclaimer.
- `color_story` — what this palette communicates emotionally, grounded in the measured hexes and harmony type.
- `text_placement_critique` — where the text sits, what it collides with, whether it survives at phone size. Cite the measured quadrants and cap heights.
- `target_audience` / `likely_niche` — inferred from visual cues, or null.
- `improvements` — exactly five, ordered 1 to 5 by impact. Each is a concrete change to *this* image: which element, which direction, how far. "Move the word FREE up 12% — it currently sits under the duration pill" is an improvement. "Improve text hierarchy" is not. Include why it matters and what it would change.
- `recreate_recipe` — how to build a *different* thumbnail in this style: palette hexes from the measurements, the font style class, the layout structure, and how the subject is treated. This is a recipe, not a copy. It exists so a creator can build their own, and it must never read as instructions to reproduce this image.
"""

# --------------------------------------------------------------------------------
# Structured output schema — enforced by output_config.format, so the frontend never
# parses prose and never has to defend against a missing field.
# --------------------------------------------------------------------------------

_nullable_string = {"type": ["string", "null"]}

OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string"},
            "why_it_works": {"type": "array", "items": {"type": "string"}},
            "why_it_fails": {"type": "array", "items": {"type": "string"}},
            "psychological_hook": {
                "type": ["object", "null"],
                "properties": {
                    "type": {"type": "string"},
                    "explanation": {"type": "string"},
                },
                "required": ["type", "explanation"],
                "additionalProperties": False,
            },
            "style_archetype": {
                "type": ["object", "null"],
                "properties": {
                    "name": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["name", "confidence"],
                "additionalProperties": False,
            },
            "font_read": {
                "type": ["object", "null"],
                "properties": {
                    "classification": _nullable_string,
                    "weight": _nullable_string,
                    "closest_google_fonts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "confidence": {"type": "number"},
                            },
                            "required": ["name", "confidence"],
                            "additionalProperties": False,
                        },
                    },
                    "disclaimer": {"type": "string"},
                },
                "required": ["classification", "weight", "closest_google_fonts", "disclaimer"],
                "additionalProperties": False,
            },
            "color_story": _nullable_string,
            "text_placement_critique": _nullable_string,
            "target_audience": _nullable_string,
            "likely_niche": _nullable_string,
            "improvements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "priority": {"type": "integer"},
                        "change": {"type": "string"},
                        "why": {"type": "string"},
                        "expected_impact": {"type": "string"},
                    },
                    "required": ["priority", "change", "why", "expected_impact"],
                    "additionalProperties": False,
                },
            },
            "recreate_recipe": {
                "type": ["object", "null"],
                "properties": {
                    "palette": {"type": "array", "items": {"type": "string"}},
                    "font_style": _nullable_string,
                    "layout": _nullable_string,
                    "subject_treatment": _nullable_string,
                },
                "required": ["palette", "font_style", "layout", "subject_treatment"],
                "additionalProperties": False,
            },
        },
        "required": [
            "verdict", "why_it_works", "why_it_fails", "psychological_hook",
            "style_archetype", "font_read", "color_story", "text_placement_critique",
            "target_audience", "likely_niche", "improvements", "recreate_recipe",
        ],
        "additionalProperties": False,
    },
}


# --------------------------------------------------------------------------------
# Usage accounting — surfaced on /api/health so the running cost is never a surprise.
# --------------------------------------------------------------------------------


class _UsageLedger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls = 0
        self.failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_tokens = 0
        self.cache_write_tokens = 0

    def record(self, usage: Any) -> dict[str, Any]:
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)

        with self._lock:
            self.calls += 1
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.cache_read_tokens += cache_read
            self.cache_write_tokens += cache_write

        return {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "cacheReadTokens": cache_read,
            "cacheWriteTokens": cache_write,
            "estimatedCostUsd": round(
                _cost(input_tokens, output_tokens, cache_read, cache_write), 6
            ),
        }

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "calls": self.calls,
                "failures": self.failures,
                "inputTokens": self.input_tokens,
                "outputTokens": self.output_tokens,
                "cacheReadTokens": self.cache_read_tokens,
                "cacheWriteTokens": self.cache_write_tokens,
                "estimatedCostUsd": round(
                    _cost(
                        self.input_tokens,
                        self.output_tokens,
                        self.cache_read_tokens,
                        self.cache_write_tokens,
                    ),
                    4,
                ),
            }


def _cost(input_tokens: int, output_tokens: int, cache_read: int, cache_write: int) -> float:
    million = 1_000_000
    return (
        input_tokens / million * settings.ai_input_cost_per_mtok
        + output_tokens / million * settings.ai_output_cost_per_mtok
        + cache_read / million * settings.ai_cache_read_cost_per_mtok
        + cache_write / million * settings.ai_cache_write_cost_per_mtok
    )


usage_ledger = _UsageLedger()


# --------------------------------------------------------------------------------


def is_configured() -> bool:
    if not settings.ai_enabled:
        return False
    if settings.anthropic_api_key:
        return True
    import os

    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _client():
    import anthropic

    if settings.anthropic_api_key:
        return anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key, timeout=settings.ai_timeout
        )
    # No explicit key: let the SDK resolve ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an
    # `ant auth login` profile from the environment.
    return anthropic.AsyncAnthropic(timeout=settings.ai_timeout)


def _encode(image: Image.Image) -> tuple[str, str]:
    """Base64 JPEG at a 1568 px long edge — larger buys nothing and costs tokens."""
    prepared = downscale_for_ai(image)
    buffer = io.BytesIO()
    prepared.convert("RGB").save(buffer, "JPEG", quality=88, optimize=True)
    return base64.standard_b64encode(buffer.getvalue()).decode("ascii"), "image/jpeg"


def _grounding_payload(metrics: dict[str, Any], scores: dict[str, Any]) -> dict[str, Any]:
    """Exactly the facts Claude is allowed to cite — nothing more, nothing derived."""
    color = metrics.get("color") or {}
    text = metrics.get("text") or {}
    return {
        "image": metrics.get("image"),
        "scores": {k: v for k, v in scores.items() if k not in ("labels", "weights")},
        "color": {
            "palette": color.get("palette"),
            "harmony": color.get("harmony"),
            "temperature": color.get("temperature"),
            "saturation": color.get("saturation"),
            "brightness": {
                k: v for k, v in (color.get("brightness") or {}).items() if k != "histogram"
            },
        },
        "text": {
            "textSource": text.get("textSource"),
            "recognitionAvailable": text.get("recognitionAvailable"),
            "blocks": [
                {k: v for k, v in block.items() if k != "bboxPx"}
                for block in (text.get("blocks") or [])
            ],
            "wordCount": text.get("wordCount"),
            "wordCountVerdict": text.get("wordCountVerdict"),
            "textAreaRatio": text.get("textAreaRatio"),
            "fontRead": text.get("fontRead"),
        },
        "mobileLegibility": metrics.get("mobileLegibility"),
        "composition": metrics.get("composition"),
        "faces": {
            "detector": (metrics.get("faces") or {}).get("detector"),
            "count": (metrics.get("faces") or {}).get("count"),
            "faces": [
                {k: v for k, v in face.items() if k != "bboxPx"}
                for face in ((metrics.get("faces") or {}).get("faces") or [])
            ],
        },
        "safeZones": {"collisions": (metrics.get("safeZones") or {}).get("collisions")},
        "quality": metrics.get("quality"),
        "contrast": metrics.get("contrast"),
    }


async def analyse(
    image: Image.Image, metrics: dict[str, Any], scores: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Return ``(ai_result, error, usage)``. Never raises."""
    if not settings.ai_enabled:
        return None, {
            "code": "ai_disabled",
            "message": "AI analysis is turned off on this deployment.",
            "retryable": False,
        }, None

    if not is_configured():
        return None, {
            "code": "ai_not_configured",
            "message": "No Anthropic API key is configured, so the AI verdict is unavailable. "
            "Every measurement below is live.",
            "retryable": False,
        }, None

    try:
        import anthropic
    except ImportError:
        return None, {
            "code": "ai_sdk_missing",
            "message": "The anthropic SDK is not installed.",
            "retryable": False,
        }, None

    data, media_type = await asyncio.to_thread(_encode, image)
    grounding = json.dumps(_grounding_payload(metrics, scores), separators=(",", ":"), sort_keys=True)

    client = _client()
    try:
        response = await client.messages.create(
            model=settings.ai_model,
            max_tokens=settings.ai_max_tokens,
            thinking={"type": "adaptive"},
            output_config={"effort": settings.ai_effort, "format": OUTPUT_SCHEMA},
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    # The breakpoint sits at the end of the frozen prefix. Everything
                    # that varies per thumbnail is in the user turn, after it.
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": data,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Here is the thumbnail, and here are the measurements taken "
                                "from it. Use only these numbers.\n\n<measurements>\n"
                                f"{grounding}\n</measurements>"
                            ),
                        },
                    ],
                }
            ],
        )
    except anthropic.NotFoundError as exc:
        log.error("AI model not found: %s", exc)
        usage_ledger.record_failure()
        return None, _error("ai_model_not_found", f"Model {settings.ai_model} is not available to this key.", False), None
    except anthropic.AuthenticationError:
        usage_ledger.record_failure()
        return None, _error("ai_auth_failed", "The Anthropic API key was rejected.", False), None
    except anthropic.RateLimitError as exc:
        usage_ledger.record_failure()
        retry_after = None
        try:
            retry_after = int(exc.response.headers.get("retry-after", "0")) or None
        except Exception:
            pass
        message = "Claude is rate-limited right now. Everything below is still live."
        if retry_after:
            message = f"Claude is rate-limited for another {retry_after}s. Everything below is still live."
        return None, _error("ai_rate_limited", message, True), None
    except anthropic.APIStatusError as exc:
        usage_ledger.record_failure()
        retryable = exc.status_code >= 500
        return None, _error(
            "ai_api_error",
            f"Claude returned {exc.status_code}. Everything below is still live.",
            retryable,
        ), None
    except anthropic.APIConnectionError:
        usage_ledger.record_failure()
        return None, _error(
            "ai_unreachable",
            "Could not reach Claude. Everything below is still live.",
            True,
        ), None
    except Exception as exc:  # noqa: BLE001 — the AI path must never take the request down
        log.exception("unexpected AI failure")
        usage_ledger.record_failure()
        return None, _error("ai_failed", f"AI analysis failed: {type(exc).__name__}.", True), None
    finally:
        await client.close()

    if getattr(response, "stop_reason", None) == "refusal":
        usage_ledger.record_failure()
        return None, _error(
            "ai_refused",
            "Claude declined to analyse this image. Everything below is still live.",
            False,
        ), None

    usage = usage_ledger.record(response.usage)

    text_block = next((b.text for b in response.content if b.type == "text"), None)
    if not text_block:
        return None, _error("ai_empty", "Claude returned no analysis.", True), usage

    try:
        parsed = json.loads(text_block)
    except json.JSONDecodeError:
        return None, _error("ai_unparseable", "Claude's response was not valid JSON.", True), usage

    return parsed, None, usage


def _error(code: str, message: str, retryable: bool) -> dict[str, Any]:
    return {"code": code, "message": message, "retryable": retryable}
