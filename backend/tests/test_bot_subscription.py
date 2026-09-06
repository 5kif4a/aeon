"""Bot API `subscription` updates (Stars auto-renew canceled / restored / charge failed).

DB-free: the service layer is stubbed so the handler's parsing and dispatch are what is tested.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram import Update

from app.bot.application import ALLOWED_UPDATES
from app.bot.handlers import payments
from app.db.models import User
from app.services import billing

USER_ID = 900_000_777
EXPIRES = datetime(2026, 10, 6, 12, tzinfo=UTC)


def _update(state: str, *, user_id: int = USER_ID, payload: str | None = None) -> Update:
    data = {
        "update_id": 1,
        "subscription": {
            "user": {"id": user_id, "is_bot": False, "first_name": "A"},
            "invoice_payload": payload or billing.pro_invoice_payload(USER_ID),
            "state": state,
        },
    }
    return Update.de_json(data, None)


def test_subscription_update_type_is_requested_explicitly():
    # PTB's ALL_TYPES predates Bot API 10.2; without this Telegram never sends the update.
    assert "subscription" in ALLOWED_UPDATES


def test_parse_subscription_update_reads_raw_api_kwargs():
    parsed = payments.parse_subscription_update(_update("canceled"))
    assert parsed == payments.SubscriptionUpdate(
        user_id=USER_ID,
        invoice_payload=billing.pro_invoice_payload(USER_ID),
        state="canceled",
    )


def test_handler_matches_only_subscription_updates():
    handler = payments.SubscriptionUpdateHandler(payments.subscription_update_callback)
    assert handler.check_update(_update("failed"))
    plain = Update.de_json(
        {
            "update_id": 2,
            "message": {"message_id": 1, "date": 0, "chat": {"id": 1, "type": "private"}},
        },
        None,
    )
    assert not handler.check_update(plain)


def _stub_services(monkeypatch):
    user = User(id=USER_ID, language="en", pro_expires_at=EXPIRES, pro_auto_renew=True)
    calls: dict[str, list] = {"canceled": [], "restored": [], "failed": [], "ops": []}

    async def canceled(session, user_id, *, source="bot"):
        calls["canceled"].append((user_id, source))
        user.pro_auto_renew = False
        return user

    async def restored(session, user_id):
        calls["restored"].append(user_id)
        user.pro_auto_renew = True
        return user

    async def failed(session, user_id):
        calls["failed"].append(user_id)
        user.pro_auto_renew = False
        return user

    @asynccontextmanager
    async def session_factory():
        yield None

    monkeypatch.setattr(payments.billing, "mark_subscription_canceled", canceled)
    monkeypatch.setattr(payments.billing, "mark_subscription_restored", restored)
    monkeypatch.setattr(payments.billing, "mark_subscription_payment_failed", failed)
    monkeypatch.setattr(payments, "SessionFactory", session_factory)
    for name in ("subscription_canceled", "subscription_restored", "subscription_payment_failed"):
        monkeypatch.setattr(
            payments.ops, name, lambda user, _name=name, **kw: calls["ops"].append((_name, kw))
        )
    return user, calls


async def test_canceled_from_telegram_settings_turns_auto_renew_off(monkeypatch):
    user, calls = _stub_services(monkeypatch)
    bot = SimpleNamespace(send_message=AsyncMock())

    await payments.subscription_update_callback(_update("canceled"), SimpleNamespace(bot=bot))

    assert calls["canceled"] == [(USER_ID, "telegram")]
    assert calls["ops"] == [("subscription_canceled", {"source": "telegram"})]
    assert user.pro_auto_renew is False
    sent = bot.send_message.await_args
    assert sent.args[0] == USER_ID
    assert "2026-10-06" in sent.args[1]


async def test_restored_and_failed_states_dispatch(monkeypatch):
    user, calls = _stub_services(monkeypatch)
    bot = SimpleNamespace(send_message=AsyncMock())

    await payments.subscription_update_callback(_update("active"), SimpleNamespace(bot=bot))
    assert calls["restored"] == [USER_ID]
    assert user.pro_auto_renew is True

    await payments.subscription_update_callback(_update("failed"), SimpleNamespace(bot=bot))
    assert calls["failed"] == [USER_ID]
    assert user.pro_auto_renew is False
    assert [name for name, _ in calls["ops"]] == [
        "subscription_restored",
        "subscription_payment_failed",
    ]
    assert bot.send_message.await_count == 2


async def test_payload_bound_to_another_user_is_ignored(monkeypatch):
    _, calls = _stub_services(monkeypatch)
    bot = SimpleNamespace(send_message=AsyncMock())
    foreign = _update("canceled", payload=billing.pro_invoice_payload(USER_ID + 1))

    await payments.subscription_update_callback(foreign, SimpleNamespace(bot=bot))

    assert calls == {"canceled": [], "restored": [], "failed": [], "ops": []}
    bot.send_message.assert_not_awaited()


async def test_unknown_state_is_ignored(monkeypatch):
    _, calls = _stub_services(monkeypatch)
    bot = SimpleNamespace(send_message=AsyncMock())

    await payments.subscription_update_callback(_update("paused"), SimpleNamespace(bot=bot))

    assert calls == {"canceled": [], "restored": [], "failed": [], "ops": []}
    bot.send_message.assert_not_awaited()
