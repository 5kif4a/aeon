import pytest

from app.db.models import User
from app.services import agent_chat


def _gemini_response(text: str) -> dict:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "finishReason": "STOP",
            }
        ]
    }


@pytest.mark.asyncio
async def test_discussion_agents_receive_the_previous_turns(monkeypatch):
    prompts: list[tuple[str, str, str]] = []
    summary_bodies: list[dict] = []

    async def fake_generate_answer(agent_id, message, *_args, **kwargs):
        prompts.append((agent_id, message, kwargs.get("retrieval_query", "")))
        return f"{agent_id} position"

    async def fake_generate_content(body, **_kwargs):
        summary_bodies.append(body)
        return _gemini_response("Shared conclusion")

    monkeypatch.setattr(agent_chat, "generate_answer", fake_generate_answer)
    monkeypatch.setattr(agent_chat.gemini, "generate_content", fake_generate_content)

    result = await agent_chat.generate_discussion_round(
        "Should I leave a stable job?",
        User(id=1, language="en", plan="Pro"),
        "en",
    )

    assert [agent_id for agent_id, _prompt, _query in prompts] == [
        "aurelius",
        "machiavelli",
        "jung",
    ]
    assert "aurelius position" not in prompts[0][1]
    assert "aurelius position" in prompts[1][1]
    assert "aurelius position" in prompts[2][1]
    assert "machiavelli position" in prompts[2][1]
    assert {query for _agent_id, _prompt, query in prompts} == {
        "Should I leave a stable job?"
    }
    assert [turn.text for turn in result.turns] == [
        "aurelius position",
        "machiavelli position",
        "jung position",
    ]
    assert result.summary == "Shared conclusion"
    summary_prompt = summary_bodies[0]["contents"][0]["parts"][0]["text"]
    assert "aurelius position" in summary_prompt
    assert "machiavelli position" in summary_prompt
    assert "jung position" in summary_prompt


@pytest.mark.asyncio
async def test_discussion_continuation_includes_the_previous_round(monkeypatch):
    prompts: list[str] = []

    async def fake_generate_answer(_agent_id, message, *_args, **_kwargs):
        prompts.append(message)
        return "next position"

    async def fake_generate_content(_body, **_kwargs):
        return _gemini_response("Updated conclusion")

    monkeypatch.setattr(agent_chat, "generate_answer", fake_generate_answer)
    monkeypatch.setattr(agent_chat.gemini, "generate_content", fake_generate_content)

    await agent_chat.generate_discussion_round(
        "How should I negotiate?",
        User(id=2, language="en", plan="Pro"),
        "en",
        previous_transcript="Marcus Aurelius:\nThe previous position.",
    )

    assert "The previous position." in prompts[0]
