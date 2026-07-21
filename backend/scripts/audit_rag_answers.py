"""Run one production-style RAG answer for every agent and locale."""

import argparse
import asyncio

from app.db.models import User
from app.services.agent_chat import generate_answer

CASES = (
    (
        "AURELIUS RU",
        "aurelius",
        "ru",
        "Коллега публично раскритиковал меня, и я не могу перестать злиться. "
        "Что в этой ситуации зависит от меня?",
    ),
    (
        "AURELIUS EN",
        "aurelius",
        "en",
        "I failed at something important and keep replaying it. "
        "How should I separate the event from my judgment?",
    ),
    (
        "MACHIAVELLI RU",
        "machiavelli",
        "ru",
        "Почему правителю опасно полагаться на чужие войска, "
        "даже если союзник кажется сильным?",
    ),
    (
        "MACHIAVELLI EN",
        "machiavelli",
        "en",
        "My team is divided between leaders and ordinary members. "
        "Can this conflict strengthen the organization rather than destroy it?",
    ),
    (
        "JUNG RU",
        "jung",
        "ru",
        "Меня особенно раздражают люди, которые постоянно хвастаются. "
        "Почему моя реакция может быть такой сильной?",
    ),
    (
        "JUNG EN",
        "jung",
        "en",
        "I repeatedly dream that I arrive too late and miss my journey. "
        "How should I explore this dream without using a dream dictionary?",
    ),
)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[case[0] for case in CASES])
    args = parser.parse_args()
    user = User(id=999999, plan="Pro", name="Test")
    for label, agent_id, language, question in CASES:
        if args.case and label != args.case:
            continue
        print(f"\n===== {label} =====")
        try:
            answer = await generate_answer(agent_id, question, user, [], language)
        except Exception as exc:  # noqa: BLE001 - audit must continue after provider failures
            print(f"ERROR: {type(exc).__name__}: {exc}")
            continue
        print(answer)


if __name__ == "__main__":
    asyncio.run(main())
