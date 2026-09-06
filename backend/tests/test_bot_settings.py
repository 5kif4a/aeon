"""DB-free tests for the runtime bot settings: cached getters, draft layer, validation."""

import asyncio

import pytest

from app.services import bot_settings


@pytest.fixture(autouse=True)
def empty_cache(monkeypatch):
    monkeypatch.setattr(bot_settings, "_overrides", {})


def test_getters_fall_back_to_defaults_when_cache_is_empty():
    assert bot_settings.get_text(bot_settings.RESPONSE_STYLE_KEY, "default text") == "default text"
    assert bot_settings.get_int(bot_settings.HISTORY_TURNS_KEY, 4) == 4
    assert bot_settings.get_float(bot_settings.TEMPERATURE_KEY, 0.72) == 0.72


def test_getters_read_populated_cache(monkeypatch):
    monkeypatch.setattr(
        bot_settings,
        "_overrides",
        {
            bot_settings.RESPONSE_STYLE_KEY: "Be brief.",
            bot_settings.HISTORY_TURNS_KEY: 8,
            bot_settings.TEMPERATURE_KEY: 1.1,
            bot_settings.MAX_OUTPUT_TOKENS_KEY: 1200.0,
        },
    )
    assert bot_settings.get_text(bot_settings.RESPONSE_STYLE_KEY, "x") == "Be brief."
    assert bot_settings.get_int(bot_settings.HISTORY_TURNS_KEY, 4) == 8
    assert bot_settings.get_float(bot_settings.TEMPERATURE_KEY, 0.72) == 1.1
    # Numbers stored as floats still read as ints for int getters.
    assert bot_settings.get_int(bot_settings.MAX_OUTPUT_TOKENS_KEY, 2500) == 1200


def test_getters_ignore_wrong_kinds_and_blank_text(monkeypatch):
    monkeypatch.setattr(
        bot_settings,
        "_overrides",
        {
            bot_settings.RESPONSE_STYLE_KEY: "   ",
            bot_settings.HISTORY_TURNS_KEY: "8",
            bot_settings.TEMPERATURE_KEY: True,
        },
    )
    assert bot_settings.get_text(bot_settings.RESPONSE_STYLE_KEY, "default") == "default"
    assert bot_settings.get_int(bot_settings.HISTORY_TURNS_KEY, 4) == 4
    assert bot_settings.get_float(bot_settings.TEMPERATURE_KEY, 0.72) == 0.72


def test_draft_overrides_shadow_cache_and_are_scoped(monkeypatch):
    monkeypatch.setattr(
        bot_settings, "_overrides", {bot_settings.TEMPERATURE_KEY: 0.5, "agent_prompt.jung": "db"}
    )
    with bot_settings.draft_overrides({bot_settings.TEMPERATURE_KEY: 1.5}):
        assert bot_settings.get_float(bot_settings.TEMPERATURE_KEY, 0.72) == 1.5
        # Keys missing from the draft still resolve through the cache.
        assert bot_settings.get_text("agent_prompt.jung", "code") == "db"
    assert bot_settings.get_float(bot_settings.TEMPERATURE_KEY, 0.72) == 0.5


async def test_draft_overrides_are_isolated_between_tasks():
    async def read(draft: dict | None) -> int:
        if draft is None:
            await asyncio.sleep(0.01)
            return bot_settings.get_int(bot_settings.HISTORY_TURNS_KEY, 4)
        with bot_settings.draft_overrides(draft):
            await asyncio.sleep(0.01)
            return bot_settings.get_int(bot_settings.HISTORY_TURNS_KEY, 4)

    results = await asyncio.gather(
        read({bot_settings.HISTORY_TURNS_KEY: 10}),
        read({bot_settings.HISTORY_TURNS_KEY: 20}),
        read(None),
    )
    assert results == [10, 20, 4]


def test_defaults_cover_every_agent_and_generation_knob():
    from app.agents import AGENTS

    keys = {spec.key for spec in bot_settings.defaults()}
    assert {
        bot_settings.RESPONSE_STYLE_KEY,
        bot_settings.TEMPERATURE_KEY,
        bot_settings.HISTORY_TURNS_KEY,
        bot_settings.MAX_OUTPUT_TOKENS_KEY,
    } <= keys
    for agent_id in AGENTS:
        assert bot_settings.agent_prompt_key(agent_id) in keys


def test_validate_accepts_values_within_kind_and_bounds():
    assert bot_settings.validate(bot_settings.TEMPERATURE_KEY, 1) == 1.0
    assert bot_settings.validate(bot_settings.TEMPERATURE_KEY, 0.0) == 0.0
    assert bot_settings.validate(bot_settings.HISTORY_TURNS_KEY, 6.0) == 6
    assert bot_settings.validate(bot_settings.MAX_OUTPUT_TOKENS_KEY, 800) == 800
    assert bot_settings.validate("agent_prompt.aurelius", "You are Marcus.") == "You are Marcus."


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (bot_settings.TEMPERATURE_KEY, 2.5),
        (bot_settings.TEMPERATURE_KEY, -0.1),
        (bot_settings.TEMPERATURE_KEY, "0.7"),
        (bot_settings.TEMPERATURE_KEY, True),
        (bot_settings.HISTORY_TURNS_KEY, 1),
        (bot_settings.HISTORY_TURNS_KEY, 41),
        (bot_settings.HISTORY_TURNS_KEY, 4.5),
        (bot_settings.MAX_OUTPUT_TOKENS_KEY, 100),
        (bot_settings.MAX_OUTPUT_TOKENS_KEY, 9000),
        (bot_settings.RESPONSE_STYLE_KEY, ""),
        (bot_settings.RESPONSE_STYLE_KEY, "   "),
        (bot_settings.RESPONSE_STYLE_KEY, 12),
        (bot_settings.RESPONSE_STYLE_KEY, "x" * (bot_settings.TEXT_MAX_LENGTH + 1)),
    ],
)
def test_validate_rejects_bad_kinds_and_bounds(key, value):
    with pytest.raises(bot_settings.SettingError):
        bot_settings.validate(key, value)


def test_validate_rejects_unknown_keys():
    with pytest.raises(bot_settings.UnknownSettingError):
        bot_settings.validate("agent_prompt.socrates", "text")
    with pytest.raises(bot_settings.UnknownSettingError):
        bot_settings.validate("plan", "Pro")
