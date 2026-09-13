"""Import chat ids from the previous bot generations and pin them into static segments.

The v1 (Nov 2024 - Feb 2025) and v2 (Feb 2025 - Mar 2026) bots ran on the same token as
this one, so their chat ids can still be messaged. This script takes the CSV built from
their dumps (one row per chat: `chat_id, segment, user_msgs, tried_to_pay, first_seen,
last_seen, first_name, username`), creates a `users` row for every id we do not know yet
and pins the ids into one static segment per `segment` value, plus one for everyone who
once reached the payment button. Broadcasts are then queued from the admin panel as usual.

Imported rows are deliberately "empty" users: no `birth_date` (so the reminder jobs skip
them), no `product_events`, and `created_at` set to the day the chat was first seen, so the
signup metrics keep telling the truth about this bot. Ids that already have a `users` row
are current users and are left out of the segments unless `--include-existing` is given.

    uv run python -m scripts.import_legacy_chats ../dumps/legacy_segments.csv
    uv run python -m scripts.import_legacy_chats ../dumps/legacy_segments.csv --dry-run
    uv run python -m scripts.import_legacy_chats ../dumps/legacy_segments.csv --actor <telegram id>

It takes DATABASE_URL from the environment, so it can be pointed at production.
"""

import argparse
import asyncio
import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.db.models import SegmentMember, User, UserSegment
from app.db.session import SessionFactory, engine
from app.i18n import normalize_language
from app.services import segments
from app.services.users import presentable_name

SEGMENT_PREFIX = "legacy"
TRIED_TO_PAY_SEGMENT = "tried_to_pay"
INSERT_CHUNK = 500

# Human-readable descriptions for the segment codes produced by the dump analysis.
SEGMENT_DESCRIPTIONS = {
    "P_paid": "Paid in the v2 bot (Stars subscription or unlimited)",
    "F_power": "30+ messages in the old bots: regulars",
    "E_core": "10-29 messages in the old bots: came back several times",
    "D_engaged": "5-9 messages in the old bots: one or two real dialogues",
    "C_light": "2-4 messages in the old bots: tried it and left",
    "B_one": "Exactly one message in the old bots",
    "A_silent": "Pressed /start in the old bots and never wrote",
    TRIED_TO_PAY_SEGMENT: "Opened a Stars invoice in the v2 bot and never paid",
}


@dataclass(frozen=True)
class LegacyChat:
    chat_id: int
    segment: str
    tried_to_pay: bool
    first_seen: date
    name: str
    username: str


def _parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes"}


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat((value or "").strip()[:10])
    except ValueError:
        return None


def read_chats(path: Path) -> list[LegacyChat]:
    """Parse the CSV; rows without a numeric chat id or a segment are skipped."""
    chats: dict[int, LegacyChat] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            try:
                chat_id = int((row.get("chat_id") or "").strip())
            except ValueError:
                continue
            segment = (row.get("segment") or "").strip()
            if not segment:
                continue
            chats[chat_id] = LegacyChat(
                chat_id=chat_id,
                segment=segment,
                tried_to_pay=_parse_bool(row.get("tried_to_pay")),
                first_seen=_parse_date(row.get("first_seen")) or datetime.now(UTC).date(),
                name=presentable_name(row.get("first_name")),
                username=(row.get("username") or "").strip().lstrip("@")[:64],
            )
    return list(chats.values())


def _segment_name(code: str) -> str:
    return f"{SEGMENT_PREFIX}:{code}"


def _user_values(chat: LegacyChat, language: str, timezone: str, hour: int) -> dict:
    return {
        "id": chat.chat_id,
        "name": chat.name,
        "username": chat.username,
        "language": language,
        "reminder_timezone": timezone,
        "reminder_hour": hour,
        "created_at": datetime.combine(chat.first_seen, datetime.min.time(), tzinfo=UTC),
    }


async def known_ids(chats: list[LegacyChat]) -> set[int]:
    """Ids with a users row that this script did not create: current users of this bot.

    Rows pinned into a `legacy:*` segment came from an earlier run and are treated as
    imports again, so re-running the script refreshes the segments instead of emptying them.
    """
    ids = [chat.chat_id for chat in chats]
    existing: set[int] = set()
    async with SessionFactory() as session:
        for start in range(0, len(ids), INSERT_CHUNK):
            chunk = ids[start : start + INSERT_CHUNK]
            existing.update(await session.scalars(select(User.id).where(User.id.in_(chunk))))
        imported = await session.scalars(
            select(SegmentMember.user_id)
            .join(UserSegment, UserSegment.id == SegmentMember.segment_id)
            .where(UserSegment.name.like(f"{SEGMENT_PREFIX}:%"))
        )
        existing.difference_update(imported)
    return existing


async def import_chats(
    chats: list[LegacyChat],
    existing: set[int],
    *,
    language: str,
    include_existing: bool,
    actor_id: int | None,
) -> None:
    settings = get_settings()
    new_chats = [chat for chat in chats if chat.chat_id not in existing]

    inserted = 0
    async with SessionFactory() as session:
        for start in range(0, len(new_chats), INSERT_CHUNK):
            rows = [
                _user_values(chat, language, settings.reminder_tz, settings.reminder_hour)
                for chat in new_chats[start : start + INSERT_CHUNK]
            ]
            result = await session.execute(insert(User).values(rows).on_conflict_do_nothing())
            inserted += result.rowcount
        await session.commit()

    print(
        f"Users: {inserted} imported, {len(new_chats) - inserted} imported earlier, "
        f"{len(existing)} current users skipped."
    )

    audience = chats if include_existing else new_chats
    members: dict[str, list[int]] = defaultdict(list)
    for chat in audience:
        members[chat.segment].append(chat.chat_id)
        if chat.tried_to_pay:
            members[TRIED_TO_PAY_SEGMENT].append(chat.chat_id)

    for code, user_ids in sorted(members.items()):
        name = _segment_name(code)
        description = SEGMENT_DESCRIPTIONS.get(code, f"Imported from the old bots: {code}")
        async with SessionFactory() as session:
            segment = await session.scalar(select(UserSegment).where(UserSegment.name == name))
            if segment is None:
                row = await segments.create_segment(
                    session,
                    name=name,
                    description=description,
                    kind="static",
                    filters={},
                    user_ids=user_ids,
                    actor_id=actor_id,
                )
                action = "created"
            else:
                row = await segments.update_segment(
                    session,
                    segment.id,
                    name=name,
                    description=description,
                    kind="static",
                    filters={},
                    user_ids=user_ids,
                    actor_id=actor_id,
                )
                action = "updated"
        print(f"Segment {name}: {action}, {row.member_count} members.")


def summarize(chats: list[LegacyChat]) -> None:
    by_segment: dict[str, int] = defaultdict(int)
    tried = 0
    for chat in chats:
        by_segment[chat.segment] += 1
        tried += chat.tried_to_pay
    for code, count in sorted(by_segment.items()):
        print(f"  {_segment_name(code):24s} {count:6d}")
    print(f"  {_segment_name(TRIED_TO_PAY_SEGMENT):24s} {tried:6d}")
    print(f"  {'total':24s} {len(chats):6d}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("csv", type=Path, help="CSV built from the old bot dumps")
    parser.add_argument("--language", default="ru", help="language for the imported users")
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="also pin ids that already have a users row into the segments",
    )
    parser.add_argument(
        "--actor", type=int, default=None, help="telegram id recorded as the segments' author"
    )
    parser.add_argument("--dry-run", action="store_true", help="only print what would happen")
    args = parser.parse_args()

    chats = read_chats(args.csv)
    if not chats:
        print("No usable rows in the CSV; nothing to import.")
        return
    print(f"Read {len(chats)} chats from {args.csv}:")
    summarize(chats)
    try:
        existing = await known_ids(chats)
        print(f"Already present as users: {len(existing)} (skipped unless --include-existing).")
        if args.dry_run:
            return
        await import_chats(
            chats,
            existing,
            language=normalize_language(args.language),
            include_existing=args.include_existing,
            actor_id=args.actor,
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
