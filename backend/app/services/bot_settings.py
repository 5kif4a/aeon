"""Runtime-editable bot settings (prompts, generation knobs) with code defaults.

Prompt building is synchronous and runs on every answer, so reads come from an
in-process cache. Writes go through the admin API and refresh the cache in the same
process; a periodic job refreshes it as well. The backend runs as a single replica.

Contract shared by agent_chat (reader) and the admin panel (writer):
  - get_text / get_int / get_float: cached read with a code default.
  - defaults(): every editable key with its code default and a short description.
  - refresh(session): reload overrides from the database into the cache.
  - set_value(session, key, value, admin_id) / delete_value(session, key, admin_id).
  - draft_overrides(mapping): context manager that shadows the cache for the current
    task only (used by the admin prompt preview; never persisted).
"""

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BotSetting
from app.services import events

logger = logging.getLogger(__name__)

RESPONSE_STYLE_KEY = "response_style"
TEMPERATURE_KEY = "temperature"
HISTORY_TURNS_KEY = "history_turns"
MAX_OUTPUT_TOKENS_KEY = "max_output_tokens"

SettingValue = str | int | float

# Inclusive bounds for numeric keys; text keys are capped by length only.
BOUNDS: dict[str, tuple[float, float]] = {
    TEMPERATURE_KEY: (0.0, 2.0),
    HISTORY_TURNS_KEY: (2, 40),
    MAX_OUTPUT_TOKENS_KEY: (200, 8000),
}
TEXT_MAX_LENGTH = 20_000


def agent_prompt_key(agent_id: str) -> str:
    return f"agent_prompt.{agent_id}"


@dataclass(frozen=True)
class SettingSpec:
    key: str
    kind: str  # "text" | "int" | "float"
    default: SettingValue
    description: str

    @property
    def bounds(self) -> tuple[float, float] | None:
        return BOUNDS.get(self.key)


@dataclass(frozen=True)
class SettingState:
    """A spec together with its stored override (if any) for the admin listing."""

    spec: SettingSpec
    value: SettingValue | None
    updated_at: datetime | None
    updated_by: int | None


class SettingError(ValueError):
    """The value does not fit the key's kind or bounds."""


class UnknownSettingError(SettingError):
    """The key is not one of `defaults()`."""


_overrides: dict[str, SettingValue] = {}
# Per-task draft layer: the preview endpoint shadows the cache without touching it.
_draft: ContextVar[Mapping[str, SettingValue] | None] = ContextVar(
    "bot_settings_draft", default=None
)


def _lookup(key: str) -> SettingValue | None:
    draft = _draft.get()
    if draft is not None and key in draft:
        return draft[key]
    return _overrides.get(key)


def get_text(key: str, default: str) -> str:
    value = _lookup(key)
    return str(value) if isinstance(value, str) and value.strip() else default


def get_int(key: str, default: int) -> int:
    value = _lookup(key)
    return int(value) if isinstance(value, int | float) and not isinstance(value, bool) else default


def get_float(key: str, default: float) -> float:
    value = _lookup(key)
    return (
        float(value) if isinstance(value, int | float) and not isinstance(value, bool) else default
    )


@contextmanager
def draft_overrides(mapping: Mapping[str, SettingValue]) -> Iterator[None]:
    """Make the getters prefer `mapping` inside the block, for the current task only."""
    token = _draft.set(dict(mapping))
    try:
        yield
    finally:
        _draft.reset(token)


def defaults() -> list[SettingSpec]:
    """Every editable key with its code default; imported lazily to avoid cycles."""
    from app import agents
    from app.core.config import get_settings

    settings = get_settings()
    specs = [
        SettingSpec(
            RESPONSE_STYLE_KEY,
            "text",
            agents.RESPONSE_STYLE_PROMPT,
            "Shared response-style block appended to every agent system prompt.",
        ),
        SettingSpec(TEMPERATURE_KEY, "float", agents.DEFAULT_TEMPERATURE, "Gemini temperature."),
        SettingSpec(
            HISTORY_TURNS_KEY,
            "int",
            agents.GEMINI_HISTORY_LIMIT,
            "How many recent dialogue messages are sent to Gemini.",
        ),
        SettingSpec(
            MAX_OUTPUT_TOKENS_KEY,
            "int",
            settings.gemini_max_output_tokens,
            "Maximum output tokens per answer.",
        ),
    ]
    for agent_id, agent in agents.AGENTS.items():
        specs.append(
            SettingSpec(
                agent_prompt_key(agent_id),
                "text",
                agent["system"],
                f"System prompt of {agent['names']['en']}.",
            )
        )
    return specs


def spec_for(key: str) -> SettingSpec:
    for spec in defaults():
        if spec.key == key:
            return spec
    raise UnknownSettingError(f"Unknown setting: {key}")


def validate(key: str, value: object) -> SettingValue:
    """Check `value` against the key's kind and bounds; returns the normalized value."""
    spec = spec_for(key)
    if isinstance(value, bool):
        raise SettingError(f"{key}: expected {spec.kind}, got a boolean")
    if spec.kind == "text":
        if not isinstance(value, str) or not value.strip():
            raise SettingError(f"{key}: expected a non-empty text")
        if len(value) > TEXT_MAX_LENGTH:
            raise SettingError(f"{key}: text is longer than {TEXT_MAX_LENGTH} characters")
        return value
    if not isinstance(value, int | float):
        raise SettingError(f"{key}: expected a number")
    if spec.kind == "int":
        if isinstance(value, float):
            if not value.is_integer():
                raise SettingError(f"{key}: expected an integer")
            value = int(value)
        number: SettingValue = int(value)
    else:
        number = float(value)
        if number != number:  # NaN
            raise SettingError(f"{key}: expected a finite number")
    bounds = spec.bounds
    if bounds is not None and not bounds[0] <= number <= bounds[1]:
        raise SettingError(f"{key}: must be between {bounds[0]} and {bounds[1]}")
    return number


async def refresh(session: AsyncSession) -> None:
    """Reload overrides from the database, replacing the cache atomically."""
    global _overrides
    rows = (await session.execute(select(BotSetting))).scalars().all()
    _overrides = {row.key: row.value for row in rows if isinstance(row.value, str | int | float)}


async def refresh_safely() -> None:
    """Startup / periodic refresh: a DB hiccup keeps the previous cache and only warns."""
    from app.db.session import SessionFactory

    try:
        async with SessionFactory() as session:
            await refresh(session)
    except Exception:
        logger.warning("Could not refresh bot settings; keeping the cached values", exc_info=True)


async def list_settings(session: AsyncSession) -> list[SettingState]:
    rows = {row.key: row for row in (await session.execute(select(BotSetting))).scalars()}
    states = []
    for spec in defaults():
        row = rows.get(spec.key)
        states.append(
            SettingState(
                spec=spec,
                value=row.value if row is not None else None,
                updated_at=row.updated_at if row is not None else None,
                updated_by=row.updated_by if row is not None else None,
            )
        )
    return states


async def set_value(session: AsyncSession, key: str, value: SettingValue, admin_id: int) -> None:
    """Validate, upsert the override, log the change and refresh the cache."""
    normalized = validate(key, value)
    row = await session.get(BotSetting, key)
    now = datetime.now(UTC)
    if row is None:
        session.add(BotSetting(key=key, value=normalized, updated_at=now, updated_by=admin_id))
    else:
        row.value = normalized
        row.updated_at = now
        row.updated_by = admin_id
    events.record(session, events.ADMIN_SETTING_CHANGED, admin_id, key=key, action="set")
    await session.commit()
    await refresh(session)


async def delete_value(session: AsyncSession, key: str, admin_id: int) -> None:
    """Drop the override so the code default applies again."""
    spec_for(key)
    row = await session.get(BotSetting, key)
    if row is not None:
        await session.delete(row)
    events.record(session, events.ADMIN_SETTING_CHANGED, admin_id, key=key, action="reset")
    await session.commit()
    await refresh(session)
