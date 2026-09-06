"""DB-free tests for prompt assembly and the multi-turn Gemini request shape."""

from app import agents
from app.db.models import User
from app.services import agent_chat, bot_settings


def _history(*turns: tuple[str, str]) -> list[dict]:
    return [{"role": role, "text": text} for role, text in turns]


def _roles(contents: list[dict]) -> list[str]:
    return [turn["role"] for turn in contents]


def _text(turn: dict) -> str:
    return turn["parts"][0]["text"]


def test_request_contents_alternate_and_end_with_current_user_turn():
    history = _history(
        ("user", "I keep postponing the hard conversation."),
        ("agent", "What do you expect to lose in it?"),
        ("user", "Their respect, I think."),
        ("agent", "Respect rarely survives silence either."),
    )

    body = agent_chat._request_body("jung", "So what do I do?", "en", history)
    contents = body["contents"]

    assert _roles(contents) == ["user", "model", "user", "model", "user"]
    assert _text(contents[0]) == "I keep postponing the hard conversation."
    assert _text(contents[1]) == "What do you expect to lose in it?"
    assert _text(contents[-1]) == "So what do I do?"
    assert body["systemInstruction"]["parts"][0]["text"]
    assert "temperature" in body["generationConfig"]
    assert "maxOutputTokens" in body["generationConfig"]


def test_history_roles_map_agent_to_model_and_drop_unknown_roles():
    history = _history(("user", "Hi"), ("agent", "Hello"), ("system", "ignored"), ("", "ignored"))

    contents = agent_chat._history_contents(history)

    assert _roles(contents) == ["user", "model"]
    assert "ignored" not in "".join(_text(turn) for turn in contents)


def test_history_merges_consecutive_same_role_and_drops_leading_model_turn():
    history = _history(
        ("agent", "Orphaned intro"),
        ("user", "First"),
        ("user", "Second"),
        ("agent", "Reply"),
    )

    contents = agent_chat._history_contents(history)

    assert _roles(contents) == ["user", "model"]
    assert _text(contents[0]) == "First\n\nSecond"


def test_history_drops_trailing_user_turn_so_current_message_stays_last():
    history = _history(("user", "A"), ("agent", "B"), ("user", "dangling"))

    body = agent_chat._request_body("aurelius", "current", "en", history)

    assert _roles(body["contents"]) == ["user", "model", "user"]
    assert _text(body["contents"][-1]) == "current"


def test_history_limit_and_text_cap_are_honoured(monkeypatch):
    long_text = "x" * (agents.GEMINI_HISTORY_TEXT_LIMIT + 50)
    history = []
    for index in range(20):
        history.append({"role": "user", "text": f"u{index}"})
        history.append({"role": "agent", "text": long_text if index == 19 else f"a{index}"})

    contents = agent_chat._history_contents(history)
    assert len(contents) == agents.GEMINI_HISTORY_LIMIT
    assert _text(contents[0]) == f"u{20 - agents.GEMINI_HISTORY_LIMIT // 2}"
    assert len(_text(contents[-1])) == agents.GEMINI_HISTORY_TEXT_LIMIT

    monkeypatch.setitem(bot_settings._overrides, bot_settings.HISTORY_TURNS_KEY, 4)
    assert len(agent_chat._history_contents(history)) == 4


def test_empty_history_yields_single_user_turn():
    body = agent_chat._request_body("machiavelli", "Advice?", "ru", [])

    assert _roles(body["contents"]) == ["user"]
    assert _text(body["contents"][0]).endswith("Advice?")


def test_user_prompt_has_no_serialized_dialogue_and_carries_dialogue_note():
    history = _history(("user", "q1"), ("agent", "a1?"), ("user", "q2"), ("agent", "a2?"))
    user = User(id=1, language="en", plan="Free")

    prompt = agent_chat._build_user_prompt("jung", "q3", user, history, "en")

    assert "recent_dialogue" not in prompt
    assert "a1?" not in prompt
    assert "reply #3" in prompt
    assert "do not end this one with a question" in prompt

    single = agent_chat._build_user_prompt(
        "jung", "q2", user, _history(("user", "q1"), ("agent", "a1?")), "en"
    )
    assert "reply #2" in single
    assert "do not end this one" not in single


def test_trailing_question_count_stops_at_first_non_question_reply():
    history = _history(
        ("agent", "Question one?"),
        ("user", "..."),
        ("agent", "A statement."),
        ("user", "..."),
        ("agent", "Question two?"),
        ("user", "..."),
        ("agent", "*Question three?*"),
    )

    assert agent_chat._trailing_question_count(history) == 2


def test_system_prompt_has_style_block_and_language_directive_without_forced_question():
    prompt = agent_chat._build_system_prompt("jung", "ru")

    assert agents.AGENTS["jung"]["system"] in prompt
    assert agents.RESPONSE_STYLE_PROMPT in prompt
    assert "Always reply in Russian" in prompt
    assert "Вы" in prompt
    assert "single next question or practical step" not in prompt
    assert "usually 5-8 sentences" not in prompt
    assert "at most one question per reply" in prompt.lower()
    assert "mirroring" in prompt.lower()


def test_jung_prompt_has_no_rigid_algorithm():
    system = agents.AGENTS["jung"]["system"]

    assert "strictly one open question" not in system
    assert "Response algorithm" not in system
    assert "step 1" not in system.lower()
    assert "do not make diagnoses" in system
    assert "at most every other reply" in system


def test_aurelius_prompt_allows_direct_stoic_views():
    system = agents.AGENTS["aurelius"]["system"]

    assert "rather than ready-made answers" not in system
    assert "do not hide behind questions" in system.lower()


def test_retry_body_does_not_reintroduce_mandatory_question():
    body = agent_chat._retry_body("jung", "Hello", "en")
    text = body["systemInstruction"]["parts"][0]["text"]

    assert "single next question" not in text
    assert "Always reply in English" in text
    assert body["contents"][-1]["role"] == "user"


def test_history_limits_are_consistent():
    assert agents.GEMINI_HISTORY_LIMIT >= 12
    assert agents.AGENT_HISTORY_LIMIT >= agents.GEMINI_HISTORY_LIMIT
    assert 0 < agents.PROMPT_MODE_HISTORY_LIMIT < agents.GEMINI_HISTORY_LIMIT
    assert agents.GEMINI_HISTORY_TEXT_LIMIT >= 1200
