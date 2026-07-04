"""Async Gemini client: plain and streaming generation with error reporting."""

import json
from collections.abc import AsyncIterator
from urllib.parse import quote

import httpx

from app.core.config import get_settings

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def _build_url(action: str, stream: bool = False) -> str:
    settings = get_settings()
    model = settings.gemini_model.removeprefix("models/").strip()
    query = f"key={quote(settings.gemini_api_key)}"
    if stream:
        query += "&alt=sse"
    return f"{GEMINI_API_BASE}/models/{quote(model)}:{action}?{query}"


async def generate_content(request_body: dict, timeout: float = 45) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(_build_url("generateContent"), json=request_body)
        if response.status_code >= 400:
            raise GeminiError(
                f"Gemini API failed with HTTP {response.status_code}: {response.text}",
                status=response.status_code,
            )
        return response.json()


async def stream_generate_content(request_body: dict) -> AsyncIterator[dict]:
    async with httpx.AsyncClient(timeout=90) as client:
        async with client.stream(
            "POST", _build_url("streamGenerateContent", stream=True), json=request_body
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", errors="replace")
                raise GeminiError(
                    f"Gemini API failed with HTTP {response.status_code}: {body}",
                    status=response.status_code,
                )
            async for line in response.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if not data or data == "[DONE]":
                    continue
                yield json.loads(data)


def extract_text(result: dict) -> str:
    candidates = result.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
    return "".join(part.get("text", "") for part in parts)


def finish_reason(result: dict) -> str:
    candidates = result.get("candidates") or []
    return candidates[0].get("finishReason", "") if candidates else ""


def describe_empty_response(result: dict | None) -> str:
    if not result:
        return ""
    details = []
    reason = finish_reason(result)
    if reason:
        details.append(f"finishReason={reason}")
    block_reason = (result.get("promptFeedback") or {}).get("blockReason")
    if block_reason:
        details.append(f"blockReason={block_reason}")
    if not (result.get("candidates") or []):
        details.append("no candidates")
    return f" ({', '.join(details)})" if details else ""
