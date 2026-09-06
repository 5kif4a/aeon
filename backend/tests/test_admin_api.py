"""Postgres-backed tests for /api/admin/*: access control, login flow, and read models."""

import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete

from app.core import admin_auth
from app.core.config import get_settings
from app.db.models import BillingPayment, Conversation, ConversationMessage, User
from app.db.session import SessionFactory
from tests.conftest import TEST_USER_ID, build_init_data
from tests.test_admin_auth import sign_widget_payload

ADMIN_ID = 900_000_401
SUBJECT_ID = 900_000_402


@pytest.fixture(autouse=True)
async def admin_fixture(monkeypatch):
    monkeypatch.setattr(get_settings(), "ops_admin_ids", str(ADMIN_ID))
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        subject = User(
            id=SUBJECT_ID,
            language="ru",
            name="Subject",
            country="Kazakhstan",
            pro_expires_at=now + timedelta(days=10),
        )
        session.add(subject)
        await session.flush()
        conversation = Conversation(
            user_id=SUBJECT_ID, agent_id="jung", status="closed", message_count=2
        )
        session.add(conversation)
        await session.flush()
        session.add_all(
            [
                ConversationMessage(
                    conversation_id=conversation.id,
                    position=0,
                    role="user",
                    text="Why do I procrastinate?",
                ),
                ConversationMessage(
                    conversation_id=conversation.id,
                    position=1,
                    role="agent",
                    text="Let us look at the shadow.",
                ),
                BillingPayment(
                    user_id=SUBJECT_ID,
                    invoice_payload="p",
                    currency="XTR",
                    amount=350,
                    telegram_payment_charge_id="charge-admin-1",
                    # Explicit timestamp: the DB clock may run ahead of the app clock.
                    created_at=now - timedelta(hours=1),
                ),
            ]
        )
        await session.commit()
    yield {"conversation_id": str(conversation.id)}
    async with SessionFactory() as session:
        await session.execute(delete(User).where(User.id.in_([ADMIN_ID, SUBJECT_ID])))
        await session.commit()


def admin_tma_headers() -> dict:
    return {"Authorization": f"tma {build_init_data(user_id=ADMIN_ID, name='Admin')}"}


async def test_non_admin_is_forbidden(client, auth_headers):
    # TEST_USER_ID is a regular user; the fixture only allowlists ADMIN_ID.
    assert TEST_USER_ID != ADMIN_ID
    response = await client.get("/api/admin/stats", headers=auth_headers)
    assert response.status_code == 403
    assert (await client.get("/api/admin/stats")).status_code == 401


async def test_profile_exposes_is_admin_flag(client, auth_headers):
    assert (await client.get("/api/me", headers=auth_headers)).json()["isAdmin"] is False
    assert (await client.get("/api/me", headers=admin_tma_headers())).json()["isAdmin"] is True


async def test_login_widget_issues_session_token_for_admins_only(client):
    payload = sign_widget_payload(
        {"id": ADMIN_ID, "first_name": "Admin", "auth_date": int(time.time())}
    )
    response = await client.post("/api/admin/auth/telegram", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["admin"]["id"] == ADMIN_ID
    assert admin_auth.verify_session_token(body["token"]) == ADMIN_ID

    me = await client.get("/api/admin/me", headers={"Authorization": f"admin {body['token']}"})
    assert me.status_code == 200 and me.json()["id"] == ADMIN_ID

    stranger = sign_widget_payload(
        {"id": SUBJECT_ID, "first_name": "Nope", "auth_date": int(time.time())}
    )
    assert (await client.post("/api/admin/auth/telegram", json=stranger)).status_code == 403
    forged = payload | {"hash": "00" * 32}
    assert (await client.post("/api/admin/auth/telegram", json=forged)).status_code == 401


async def test_stats_users_conversations_and_payments(client, admin_fixture):
    headers = admin_tma_headers()

    stats = await client.get("/api/admin/stats", params={"days": 7}, headers=headers)
    assert stats.status_code == 200
    assert stats.json()["totals"]["paymentsStars"] >= 350
    assert len(stats.json()["series"]) == 7
    assert (
        await client.get("/api/admin/stats", params={"days": 5}, headers=headers)
    ).status_code == 422

    users = await client.get(
        "/api/admin/users", params={"q": "Kazakh", "plan": "Pro"}, headers=headers
    )
    assert users.status_code == 200
    ids = [row["id"] for row in users.json()["items"]]
    assert SUBJECT_ID in ids
    subject = next(row for row in users.json()["items"] if row["id"] == SUBJECT_ID)
    assert (
        subject["plan"] == "Pro"
        and subject["paymentsStars"] == 350
        and subject["conversations"] == 1
    )

    detail = await client.get(f"/api/admin/users/{SUBJECT_ID}", headers=headers)
    assert detail.status_code == 200
    assert len(detail.json()["payments"]) == 1 and len(detail.json()["conversations"]) == 1

    conversations = await client.get(
        "/api/admin/conversations", params={"userId": SUBJECT_ID}, headers=headers
    )
    assert conversations.status_code == 200
    row = conversations.json()["items"][0]
    assert row["agentId"] == "jung" and row["preview"].startswith("Why do I")

    thread = await client.get(
        f"/api/admin/conversations/{admin_fixture['conversation_id']}", headers=headers
    )
    assert thread.status_code == 200
    assert [m["role"] for m in thread.json()["messages"]] == ["user", "agent"]

    payments = await client.get("/api/admin/payments", headers=headers)
    assert payments.status_code == 200
    assert any(p["userId"] == SUBJECT_ID for p in payments.json()["items"])

    # The audit trail of the conversation view lands in the admin's events.
    admin_detail = await client.get(f"/api/admin/users/{ADMIN_ID}", headers=headers)
    assert "admin_view_conversation" in {e["type"] for e in admin_detail.json()["events"]}


async def test_grant_pro_extends_expiry(client):
    headers = admin_tma_headers()
    before = datetime.now(UTC) + timedelta(days=10)

    response = await client.post(
        f"/api/admin/users/{SUBJECT_ID}/grant-pro", json={"days": 30}, headers=headers
    )
    assert response.status_code == 200
    expires = datetime.fromisoformat(response.json()["proExpiresAt"])
    assert expires > before + timedelta(days=29)
    assert response.json()["plan"] == "Pro"
    assert (
        await client.post(
            f"/api/admin/users/{SUBJECT_ID}/grant-pro", json={"days": 0}, headers=headers
        )
    ).status_code == 422
    assert (
        await client.post("/api/admin/users/1/grant-pro", json={"days": 1}, headers=headers)
    ).status_code == 404


async def test_refund_payment_calls_telegram_and_revokes_pro(client, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.bot import runtime

    bot = SimpleNamespace(
        refund_star_payment=AsyncMock(return_value=True), send_message=AsyncMock()
    )
    monkeypatch.setattr(runtime, "get_application", lambda: SimpleNamespace(bot=bot))
    headers = admin_tma_headers()

    detail = await client.get(f"/api/admin/users/{SUBJECT_ID}", headers=headers)
    payment = next(p for p in detail.json()["payments"] if p["status"] == "paid")

    response = await client.post(
        f"/api/admin/users/{SUBJECT_ID}/payments/{payment['id']}/refund", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "refunded"
    bot.refund_star_payment.assert_awaited_once_with(SUBJECT_ID, "charge-admin-1")
    bot.send_message.assert_awaited_once()

    # Idempotent: a second call does not hit Telegram again.
    again = await client.post(
        f"/api/admin/users/{SUBJECT_ID}/payments/{payment['id']}/refund", headers=headers
    )
    assert again.status_code == 200 and again.json()["status"] == "refunded"
    assert bot.refund_star_payment.await_count == 1

    after = await client.get(f"/api/admin/users/{SUBJECT_ID}", headers=headers)
    assert "payment_refunded" in {e["type"] for e in after.json()["events"]}
    assert (
        await client.post(
            f"/api/admin/users/{SUBJECT_ID}/payments/{uuid.uuid4()}/refund", headers=headers
        )
    ).status_code == 404
