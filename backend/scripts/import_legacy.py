"""One-off import of legacy profiles into the new schema.

Reads the old `registrations` table (chat_id + JSONB profile) created by the
previous bot.py and copies profiles, goals, and diary-free fields into the new
`users`/`goals` tables. Existing users are skipped.

Usage: uv run python scripts/import_legacy.py
"""

import asyncio
import json
from datetime import UTC, date, datetime

import sqlalchemy as sa

from app.db.models import Goal, User
from app.db.session import SessionFactory, engine
from app.i18n import normalize_language


def _parse_birth_date(value) -> date | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


async def main() -> None:
    async with engine.connect() as connection:
        exists = await connection.execute(sa.text("SELECT to_regclass('public.registrations')"))
        if exists.scalar() is None:
            print("No legacy `registrations` table found; nothing to import.")
            return
        rows = (
            await connection.execute(sa.text("SELECT chat_id, profile FROM registrations"))
        ).fetchall()

    imported = skipped = 0
    async with SessionFactory() as session:
        for chat_id, profile in rows:
            try:
                chat_id = int(chat_id)
            except (TypeError, ValueError):
                continue
            if isinstance(profile, str):
                profile = json.loads(profile)
            if not isinstance(profile, dict):
                continue

            if await session.get(User, chat_id) is not None:
                skipped += 1
                continue

            user = User(
                id=chat_id,
                language=normalize_language(profile.get("language")),
                name=str(profile.get("name") or "")[:64],
                gender=str(profile.get("gender") or "")[:32],
                birth_date=_parse_birth_date(profile.get("birthDate")),
                country=str(profile.get("country") or "")[:64],
                location=str(profile.get("location") or "")[:128],
                activity=str(profile.get("activity") or "")[:256],
                interests=str(profile.get("interests") or ""),
                main_goal=str(profile.get("mainGoal") or ""),
                current_problem=str(profile.get("currentProblem") or ""),
                plan=str(profile.get("plan") or "Basic")[:32],
                active_agent=profile.get("activeAgent")
                if profile.get("activeAgent") in ("aurelius", "machiavelli", "jung")
                else None,
            )
            session.add(user)

            goal = profile.get("goal")
            if isinstance(goal, dict) and goal.get("text"):
                session.add(
                    Goal(
                        user_id=chat_id,
                        text=str(goal["text"])[:512],
                        status="active" if goal.get("status") == "active" else "closed",
                        closed_at=datetime.now(UTC) if goal.get("status") != "active" else None,
                    )
                )
            imported += 1

        await session.commit()

    print(f"Imported {imported} users, skipped {skipped} already present.")


if __name__ == "__main__":
    asyncio.run(main())
