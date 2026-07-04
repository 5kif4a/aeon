"""Agent dialogue orchestration: prompts, streaming, retries, Redis history.

Prompts are authored in English; a per-request directive tells the model which
language to reply in, based on the user's profile language.
"""

import json
import re
from collections.abc import Awaitable, Callable
from datetime import date

import redis.asyncio as aioredis

from app.agents import (
    AGENT_HISTORY_LIMIT,
    GEMINI_HISTORY_LIMIT,
    GEMINI_HISTORY_TEXT_LIMIT,
    agent_name,
    agent_role,
    agent_system_prompt,
)
from app.clients import gemini
from app.core.config import get_settings
from app.db.models import User
from app.i18n import LANGUAGE_IN_ENGLISH, normalize_language

OnText = Callable[[str], Awaitable[None]]

NOT_SPECIFIED = "not specified"

_redis_client: aioredis.Redis | None = None
_redis_failed = False


# --- prompt building ---------------------------------------------------------


def _language_directive(language: str) -> str:
    return f"Always reply in {LANGUAGE_IN_ENGLISH[normalize_language(language)]}, regardless of the language of the context."


def _build_system_prompt(agent_id: str, language: str) -> str:
    return (
        f"{agent_system_prompt(agent_id)}\n\n"
        "Answer concisely, clearly, and to the point. "
        "Response structure: first a direct thesis, then 1-2 short paragraphs of explanation, then a single next question or practical step. "
        "If the question is broad, do not lay out every option at once: pick the most important direction and gently clarify the intent. "
        "If you ask a question, ask only one. "
        "Keep it compact: usually 5-8 sentences. Do not add technical notes, character counts, length checks, or comments about the response format. "
        f"{_language_directive(language)}"
    )


def _compact_history(history: list[dict]) -> list[dict]:
    compact = []
    for item in (history or [])[-GEMINI_HISTORY_LIMIT:]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        compact.append(
            {"role": str(item.get("role", ""))[:20], "text": text[:GEMINI_HISTORY_TEXT_LIMIT]}
        )
    return compact


def _build_user_prompt(
    agent_id: str,
    message: str,
    user: User | None,
    history: list[dict],
    language: str,
    diary: list[str] | None = None,
    active_goal: str = "",
) -> str:
    context = {
        "agent": agent_name(agent_id, language),
        "agent_role": agent_role(agent_id, language),
        "name": (user.name if user else "") or NOT_SPECIFIED,
        "age": _age_label(user),
        "location": ((user.location or user.country) if user else "") or NOT_SPECIFIED,
        "interests": (user.interests if user else "") or NOT_SPECIFIED,
        "main_goal": (user.main_goal if user else "") or NOT_SPECIFIED,
        "active_goal": active_goal or NOT_SPECIFIED,
        "current_problem": (user.current_problem if user else "") or NOT_SPECIFIED,
        "recent_diary": (diary or [])[:3],
        "recent_dialogue": _compact_history(history),
    }
    return (
        "User context:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        "User's question or request:\n"
        f"{message or 'Give a short, thoughtful piece of advice for today.'}"
    )


def _age_label(user: User | None) -> str:
    if user is None or user.birth_date is None:
        return NOT_SPECIFIED
    today = date.today()
    age = today.year - user.birth_date.year
    if (today.month, today.day) < (user.birth_date.month, user.birth_date.day):
        age -= 1
    return str(age)


def _request_body(agent_id: str, prompt: str, language: str) -> dict:
    settings = get_settings()
    return {
        "systemInstruction": {"parts": [{"text": _build_system_prompt(agent_id, language)}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.72,
            "maxOutputTokens": settings.gemini_max_output_tokens,
        },
    }


def _continuation_body(agent_id: str, partial_answer: str, language: str) -> dict:
    settings = get_settings()
    return {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        f"{agent_system_prompt(agent_id)}\n\n"
                        "Finish the truncated thought briefly: 3-5 sentences. "
                        "Do not repeat the beginning, do not add technical comments. "
                        f"{_language_directive(language)}"
                    )
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"Continue and finish this truncated answer:\n{partial_answer[-900:]}"}
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": min(settings.gemini_max_output_tokens, 450),
        },
    }


def _retry_body(agent_id: str, message: str, language: str) -> dict:
    settings = get_settings()
    return {
        "systemInstruction": {
            "parts": [
                {
                    "text": (
                        f"{agent_system_prompt(agent_id)}\n\n"
                        "Answer in plain text. Do not return JSON, markdown tables, technical comments, "
                        "or length checks. If the question is short, give a short but complete answer. "
                        f"{_language_directive(language)}"
                    )
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": message or "Give a short piece of advice for today."}],
            }
        ],
        "generationConfig": {
            "temperature": 0.65,
            "maxOutputTokens": min(settings.gemini_max_output_tokens, 1200),
        },
    }


# --- answer post-processing --------------------------------------------------


def sanitize_answer(text: str) -> str:
    cleaned_lines = []
    for line in str(text or "").splitlines():
        normalized = line.strip().strip("*_` ").lower()
        # Strip meta lines the model sometimes emits, in either language.
        if re.search(r"character\s+count|count\s+check|~?\d+\s*characters", normalized):
            continue
        if re.search(r"провер(ка|ку)\s+длин|подсч[её]т\s+символ|~?\d+\s*знак", normalized):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _is_incomplete(text: str, reason: str = "") -> bool:
    stripped = str(text or "").strip()
    if not stripped:
        return False
    if reason == "MAX_TOKENS":
        return True
    if len(stripped) < 500:
        return False
    return stripped[-1] not in '.!?…»”")]:'


async def _complete_if_needed(
    agent_id: str, text: str, reason: str, language: str, on_text: OnText | None = None
) -> str:
    if not _is_incomplete(text, reason):
        return text
    try:
        result = await gemini.generate_content(
            _continuation_body(agent_id, text, language), timeout=18
        )
    except Exception:
        return text
    continuation = sanitize_answer(gemini.extract_text(result))
    if not continuation:
        return text
    completed = f"{text.rstrip()}\n\n{continuation.lstrip()}".strip()
    if on_text:
        await on_text(completed)
    return completed


async def _retry(
    agent_id: str, message: str, language: str, previous_result: dict | None = None
) -> str:
    result = await gemini.generate_content(_retry_body(agent_id, message, language))
    text = sanitize_answer(gemini.extract_text(result))
    if text:
        return text
    details = gemini.describe_empty_response(result or previous_result)
    raise gemini.GeminiError(f"Gemini returned an empty answer{details}")


# --- public generation API ---------------------------------------------------


async def generate_answer(
    agent_id: str,
    message: str,
    user: User | None,
    history: list[dict],
    language: str,
    diary: list[str] | None = None,
    active_goal: str = "",
) -> str:
    prompt = _build_user_prompt(agent_id, message, user, history, language, diary, active_goal)
    result = await gemini.generate_content(_request_body(agent_id, prompt, language))
    text = sanitize_answer(gemini.extract_text(result))
    text = await _complete_if_needed(agent_id, text, gemini.finish_reason(result), language)
    if not text:
        return await _retry(agent_id, message, language, result)
    return text


async def generate_answer_stream(
    agent_id: str,
    message: str,
    user: User | None,
    history: list[dict],
    on_text: OnText,
    language: str,
    diary: list[str] | None = None,
    active_goal: str = "",
) -> str:
    prompt = _build_user_prompt(agent_id, message, user, history, language, diary, active_goal)
    text = ""
    reason = ""
    async for chunk in gemini.stream_generate_content(_request_body(agent_id, prompt, language)):
        reason = gemini.finish_reason(chunk) or reason
        delta = gemini.extract_text(chunk)
        if not delta:
            continue
        text += delta
        await on_text(text)
    text = sanitize_answer(text)
    text = await _complete_if_needed(agent_id, text, reason, language, on_text)
    if not text:
        retry_text = await _retry(agent_id, message, language)
        await on_text(retry_text)
        return retry_text
    return text


# --- Redis dialogue history --------------------------------------------------


def _history_key(chat_id: int, agent_id: str) -> str:
    return f"aeon:agent_history:{chat_id}:{agent_id}"


async def _get_redis() -> aioredis.Redis | None:
    global _redis_client, _redis_failed
    if _redis_client is not None:
        return _redis_client
    settings = get_settings()
    if _redis_failed or not settings.redis_url:
        return None
    try:
        client = aioredis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
        )
        await client.ping()
        _redis_client = client
        return client
    except Exception:
        _redis_failed = True
        return None


async def get_history(chat_id: int, agent_id: str) -> list[dict]:
    client = await _get_redis()
    if client is None:
        return []
    try:
        raw_items = await client.lrange(_history_key(chat_id, agent_id), 0, -1)
    except Exception:
        return []
    history = []
    for raw_item in raw_items:
        try:
            item = json.loads(raw_item)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(item, dict) and item.get("text"):
            history.append(item)
    return history[-AGENT_HISTORY_LIMIT:]


async def append_history(chat_id: int, agent_id: str, user_text: str, agent_text: str) -> None:
    client = await _get_redis()
    if client is None:
        return
    settings = get_settings()
    key = _history_key(chat_id, agent_id)
    entries = [
        {"role": "user", "text": str(user_text or "")[:1200]},
        {"role": "agent", "text": str(agent_text or "")[:1800]},
    ]
    try:
        pipe = client.pipeline()
        for entry in entries:
            pipe.rpush(key, json.dumps(entry, ensure_ascii=False))
        pipe.ltrim(key, -AGENT_HISTORY_LIMIT, -1)
        if settings.redis_agent_history_ttl > 0:
            pipe.expire(key, settings.redis_agent_history_ttl)
        await pipe.execute()
    except Exception:
        pass
