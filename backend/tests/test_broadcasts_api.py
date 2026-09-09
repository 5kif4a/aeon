"""Postgres-backed tests for segments and broadcasts: audience, queue, delivery log."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, select
from telegram.error import Forbidden

from app.core.config import get_settings
from app.db.models import Broadcast, BroadcastDelivery, User, UserSegment
from app.db.session import SessionFactory
from tests.conftest import build_init_data, make_admin

ADMIN_ID = 900_000_601
RU_USER = 900_000_602
EN_USER = 900_000_603
OPTED_OUT = 900_000_604
AUDIENCE = [RU_USER, EN_USER, OPTED_OUT]


def admin_headers() -> dict:
    return {"Authorization": f"tma {build_init_data(user_id=ADMIN_ID, name='Admin')}"}


@pytest.fixture(autouse=True)
async def broadcast_fixture(monkeypatch):
    # Keep the queue test fast; the rate only paces the sleeps between sends.
    monkeypatch.setattr(get_settings(), "broadcast_rate_per_second", 1000)
    await make_admin(ADMIN_ID)
    async with SessionFactory() as session:
        session.add_all(
            [
                User(id=RU_USER, language="ru", name="Ru"),
                User(id=EN_USER, language="en", name="En"),
                User(id=OPTED_OUT, language="ru", name="Nope", marketing_enabled=False),
            ]
        )
        await session.commit()
    yield
    async with SessionFactory() as session:
        # Only what this module created: the dev database is shared with hand-made rows.
        await session.execute(delete(Broadcast).where(Broadcast.created_by == ADMIN_ID))
        await session.execute(delete(UserSegment).where(UserSegment.created_by == ADMIN_ID))
        await session.execute(delete(User).where(User.id.in_([ADMIN_ID, *AUDIENCE])))
        await session.commit()


async def _segment(client, kind: str = "dynamic", **overrides) -> dict:
    payload = {
        "name": overrides.pop("name", "Test audience"),
        "description": "",
        "kind": kind,
        "filters": {"userIds": AUDIENCE} if kind == "dynamic" else {},
        "userIds": AUDIENCE if kind == "static" else [],
    } | overrides
    response = await client.post("/api/admin/segments", json=payload, headers=admin_headers())
    assert response.status_code == 200, response.text
    return response.json()


async def _broadcast(client, segment_id: str, category: str = "marketing") -> dict:
    response = await client.post(
        "/api/admin/broadcasts",
        json={
            "title": "September promo",
            "category": category,
            "segmentId": segment_id,
            "content": {
                "ru": {
                    "text": "Скидка на Pro",
                    "buttonText": "Открыть",
                    "buttonUrl": "https://t.me/aeon",
                },
                "en": {"text": "Pro is on sale"},
            },
        },
        headers=admin_headers(),
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_segment_preview_counts_and_splits_by_language(client):
    preview = await client.post(
        "/api/admin/segments/preview",
        json={"kind": "dynamic", "filters": {"userIds": AUDIENCE}},
        headers=admin_headers(),
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["size"] == 3 and body["byLanguage"] == {"ru": 2, "en": 1}
    assert {row["id"] for row in body["sample"]} == set(AUDIENCE)

    # An unknown filter key is rejected instead of quietly widening the audience.
    broken = await client.post(
        "/api/admin/segments/preview",
        json={"kind": "dynamic", "filters": {"planz": ["Pro"]}},
        headers=admin_headers(),
    )
    assert broken.status_code == 422


async def test_static_segment_pins_ids_and_ignores_unknown_ones(client):
    segment = await _segment(client, kind="static", userIds=[*AUDIENCE, 900_000_699])
    assert segment["kind"] == "static" and segment["memberCount"] == 3
    detail = await client.get(f"/api/admin/segments/{segment['id']}", headers=admin_headers())
    assert detail.json()["userIds"] == sorted(AUDIENCE)
    assert detail.json()["size"] == 3

    assert (
        await client.delete(f"/api/admin/segments/{segment['id']}", headers=admin_headers())
    ).status_code == 204


async def test_marketing_audience_skips_opted_out_users(client):
    segment = await _segment(client)
    marketing = await _broadcast(client, segment["id"])
    audience = await client.get(
        f"/api/admin/broadcasts/{marketing['id']}/audience", headers=admin_headers()
    )
    assert audience.json()["size"] == 2

    service = await _broadcast(client, segment["id"], category="service")
    audience = await client.get(
        f"/api/admin/broadcasts/{service['id']}/audience", headers=admin_headers()
    )
    assert audience.json()["size"] == 3


async def test_queue_sends_once_and_records_every_delivery(client, monkeypatch):
    from app.bot import broadcasting

    segment = await _segment(client)
    broadcast = await _broadcast(client, segment["id"])

    scheduled = await client.post(
        f"/api/admin/broadcasts/{broadcast['id']}/schedule", json={}, headers=admin_headers()
    )
    assert scheduled.status_code == 200 and scheduled.json()["status"] == "scheduled"

    sent_to: list[int] = []

    async def send_message(chat_id, text, **kwargs):
        sent_to.append(chat_id)
        if chat_id == EN_USER:
            raise Forbidden("bot was blocked by the user")
        return SimpleNamespace(message_id=1)

    bot = SimpleNamespace(send_message=AsyncMock(side_effect=send_message))
    monkeypatch.setattr(broadcasting.ops, "notify", lambda *a, **k: None)
    await broadcasting.run_queue(SimpleNamespace(bot=bot))

    assert sorted(sent_to) == sorted([RU_USER, EN_USER])  # the opt-out never gets one
    detail = await client.get(f"/api/admin/broadcasts/{broadcast['id']}", headers=admin_headers())
    body = detail.json()
    assert body["status"] == "sent"
    assert (body["sentCount"], body["blockedCount"], body["pendingCount"]) == (1, 1, 0)
    assert body["totalRecipients"] == 2

    deliveries = await client.get(
        f"/api/admin/broadcasts/{broadcast['id']}/deliveries", headers=admin_headers()
    )
    rows = {row["userId"]: row for row in deliveries.json()}
    assert rows[RU_USER]["status"] == "sent" and rows[RU_USER]["sentAt"]
    assert rows[EN_USER]["status"] == "blocked" and "blocked" in rows[EN_USER]["error"]

    # A second tick has nothing left to do: the delivery log is the idempotency key.
    sent_to.clear()
    await broadcasting.run_queue(SimpleNamespace(bot=bot))
    assert sent_to == []

    # And a finished broadcast can no longer be canceled or edited.
    assert (
        await client.post(
            f"/api/admin/broadcasts/{broadcast['id']}/cancel", headers=admin_headers()
        )
    ).status_code == 422


async def test_cancel_keeps_rows_and_a_rescheduled_send_skips_them(client, monkeypatch):
    """Cancel must not delete pending rows: a batch may be in flight, and a re-scheduled
    campaign has to skip everyone who already received it."""
    from app.bot import broadcasting

    segment = await _segment(client)
    broadcast = await _broadcast(client, segment["id"], category="service")
    await client.post(
        f"/api/admin/broadcasts/{broadcast['id']}/schedule", json={}, headers=admin_headers()
    )
    monkeypatch.setattr(broadcasting.ops, "notify", lambda *a, **k: None)
    async with SessionFactory() as session:
        row = await session.get(Broadcast, broadcast["id"])
        await broadcasting.broadcasts.materialize(session, row)
        # Pretend one recipient was already reached before the cancel.
        await broadcasting.broadcasts.mark_deliveries(
            session,
            [
                (
                    (
                        await session.scalars(
                            select(BroadcastDelivery.id).where(
                                BroadcastDelivery.broadcast_id == broadcast["id"],
                                BroadcastDelivery.user_id == RU_USER,
                            )
                        )
                    ).one(),
                    "sent",
                    "",
                )
            ],
        )

    canceled = await client.post(
        f"/api/admin/broadcasts/{broadcast['id']}/cancel", headers=admin_headers()
    )
    assert canceled.status_code == 200 and canceled.json()["status"] == "canceled"
    assert canceled.json()["pendingCount"] == 2 and canceled.json()["sentCount"] == 1

    # Re-schedule and run: only the two who never got it are sent to.
    await client.post(
        f"/api/admin/broadcasts/{broadcast['id']}/schedule", json={}, headers=admin_headers()
    )
    sent_to: list[int] = []

    async def send_message(chat_id, text, **kwargs):
        sent_to.append(chat_id)
        return SimpleNamespace(message_id=1)

    bot = SimpleNamespace(send_message=AsyncMock(side_effect=send_message))
    await broadcasting.run_queue(SimpleNamespace(bot=bot))
    assert sorted(sent_to) == sorted([EN_USER, OPTED_OUT])


async def test_materialize_yields_to_a_concurrent_cancel(client, monkeypatch):
    """Compare-and-set: the admin's cancel is never overwritten back to `sending`."""
    from app.bot import broadcasting

    segment = await _segment(client)
    broadcast = await _broadcast(client, segment["id"])
    await client.post(
        f"/api/admin/broadcasts/{broadcast['id']}/schedule", json={}, headers=admin_headers()
    )
    monkeypatch.setattr(broadcasting.ops, "notify", lambda *a, **k: None)
    async with SessionFactory() as job_session:
        row = await job_session.get(Broadcast, broadcast["id"])  # the job has read `scheduled`
        # ...and the admin cancels in between.
        assert (
            await client.post(
                f"/api/admin/broadcasts/{broadcast['id']}/cancel", headers=admin_headers()
            )
        ).status_code == 200
        assert await broadcasting.broadcasts.materialize(job_session, row) is None
    detail = await client.get(f"/api/admin/broadcasts/{broadcast['id']}", headers=admin_headers())
    assert detail.json()["status"] == "canceled"


async def test_scheduled_broadcast_is_not_editable(client):
    segment = await _segment(client)
    broadcast = await _broadcast(client, segment["id"])
    await client.post(
        f"/api/admin/broadcasts/{broadcast['id']}/schedule", json={}, headers=admin_headers()
    )
    edited = await client.put(
        f"/api/admin/broadcasts/{broadcast['id']}",
        json={
            "title": "changed",
            "category": "service",
            "segmentId": segment["id"],
            "content": {"ru": {"text": "другое"}},
        },
        headers=admin_headers(),
    )
    assert edited.status_code == 422


async def test_empty_dynamic_segment_is_refused(client):
    """`{}` would match every user; it must be refused on save, not read as "everyone"."""
    response = await client.post(
        "/api/admin/segments",
        json={"name": "Everyone", "description": "", "kind": "dynamic", "filters": {}},
        headers=admin_headers(),
    )
    assert response.status_code == 422 and "at least one condition" in response.json()["detail"]


async def test_test_send_goes_to_the_admin_only(client, monkeypatch):
    from app.bot import runtime

    segment = await _segment(client)
    broadcast = await _broadcast(client, segment["id"])
    bot = SimpleNamespace(send_message=AsyncMock())
    monkeypatch.setattr(runtime, "get_application", lambda: SimpleNamespace(bot=bot))

    response = await client.post(
        f"/api/admin/broadcasts/{broadcast['id']}/test",
        json={"language": "en"},
        headers=admin_headers(),
    )
    assert response.status_code == 204, response.text
    chat_id = bot.send_message.await_args.args[0]
    assert chat_id == ADMIN_ID
    assert "Pro is on sale" in bot.send_message.await_args.args[1]


async def test_broadcast_without_text_cannot_be_created_or_queued(client):
    segment = await _segment(client)
    empty = await client.post(
        "/api/admin/broadcasts",
        json={"title": "Empty", "segmentId": segment["id"], "content": {}},
        headers=admin_headers(),
    )
    assert empty.status_code == 422

    orphan = await _broadcast(client, segment["id"])
    await client.delete(f"/api/admin/segments/{segment['id']}", headers=admin_headers())
    queued = await client.post(
        f"/api/admin/broadcasts/{orphan['id']}/schedule", json={}, headers=admin_headers()
    )
    # The segment is gone, so `segment_id` is NULL and no filters are left. That must be
    # refused, not read as "everyone".
    assert queued.status_code == 422 and "at least one filter" in queued.json()["detail"]
