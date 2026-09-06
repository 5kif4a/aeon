"""Async Gemini client: plain and streaming generation, embeddings, error reporting."""

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


# batchEmbedContents accepts at most this many texts per request.
EMBED_BATCH_LIMIT = 100


def _embedding_url(action: str) -> str:
    settings = get_settings()
    model = settings.rag_embedding_model.removeprefix("models/").strip()
    return f"{GEMINI_API_BASE}/models/{quote(model)}:{action}?key={quote(settings.gemini_api_key)}"


def _embedding_request(text: str, task_type: str, dimension: int) -> dict:
    return {
        "content": {"parts": [{"text": text}]},
        "taskType": task_type,
        "outputDimensionality": dimension,
    }


async def embed_texts(
    texts: list[str],
    task_type: str = "RETRIEVAL_DOCUMENT",
    timeout: float = 60,
    dimension: int | None = None,
) -> list[list[float]]:
    """Embed several texts with ``batchEmbedContents``; order matches ``texts``.

    Longer inputs are split into API-sized batches and sent sequentially.
    """
    if not texts:
        return []
    settings = get_settings()
    dimension = dimension or settings.rag_embedding_dim
    model = settings.rag_embedding_model.removeprefix("models/").strip()
    vectors: list[list[float]] = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        for start in range(0, len(texts), EMBED_BATCH_LIMIT):
            batch = texts[start : start + EMBED_BATCH_LIMIT]
            body = {
                "requests": [
                    {"model": f"models/{model}", **_embedding_request(text, task_type, dimension)}
                    for text in batch
                ]
            }
            response = await client.post(_embedding_url("batchEmbedContents"), json=body)
            if response.status_code >= 400:
                raise GeminiError(
                    f"Gemini embedding API failed with HTTP {response.status_code}: {response.text}",
                    status=response.status_code,
                )
            embeddings = response.json().get("embeddings") or []
            if len(embeddings) != len(batch):
                raise GeminiError(
                    f"Gemini returned {len(embeddings)} embeddings for {len(batch)} texts"
                )
            vectors.extend(
                [float(value) for value in item.get("values", [])] for item in embeddings
            )
    return vectors


async def embed_query(text: str, timeout: float = 5, dimension: int | None = None) -> list[float]:
    """Embed one search query with ``embedContent`` (taskType RETRIEVAL_QUERY)."""
    settings = get_settings()
    dimension = dimension or settings.rag_embedding_dim
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            _embedding_url("embedContent"),
            json=_embedding_request(text, "RETRIEVAL_QUERY", dimension),
        )
        if response.status_code >= 400:
            raise GeminiError(
                f"Gemini embedding API failed with HTTP {response.status_code}: {response.text}",
                status=response.status_code,
            )
        values = (response.json().get("embedding") or {}).get("values") or []
    if not values:
        raise GeminiError("Gemini returned an empty query embedding")
    return [float(value) for value in values]


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
