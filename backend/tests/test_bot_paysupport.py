"""/paysupport conversation and refunded_payment handling, DB-free (services stubbed)."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.ext import CommandHandler, ConversationHandler

from app.bot.handlers import payments
from app.db.models import BillingPayment, User
from app.services import billing

USER_ID = 900_000_778


def _context():
    return SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))


def _update(text: str | None = None):
    return SimpleNamespace(
        effective_user=SimpleNamespace(id=USER_ID),
        effective_message=SimpleNamespace(text=text, refunded_payment=None),
    )


def test_paysupport_handler_waits_for_one_private_message():
    handler = payments.build_paysupport_handler()
    assert isinstance(handler, ConversationHandler)
    assert isinstance(handler.entry_points[0], CommandHandler)
    assert handler.entry_points[0].commands == frozenset({"paysupport"})
    assert payments.PAYSUPPORT_MESSAGE in handler.states
    assert handler.conversation_timeout == payments.PAYSUPPORT_TIMEOUT_SECONDS


async def test_paysupport_message_is_forwarded_to_ops(monkeypatch):
    user = User(id=USER_ID, language="ru", pro_expires_at=datetime(2026, 10, 1, tzinfo=UTC))
    recorded: list = []
    forwarded: list = []

    class FakeResult:
        def __init__(self, items):
            self._items = items

        def __iter__(self):
            return iter(self._items)

    class FakeSession:
        async def scalars(self, query):
            return FakeResult(
                [
                    BillingPayment(
                        user_id=USER_ID,
                        amount=350,
                        currency="XTR",
                        status="paid",
                        telegram_payment_charge_id="c1",
                        created_at=datetime(2026, 9, 1, tzinfo=UTC),
                    )
                ]
            )

        async def commit(self):
            pass

    @asynccontextmanager
    async def session_factory():
        yield FakeSession()

    async def get_or_create_user(session, user_id):
        return user

    monkeypatch.setattr(payments, "SessionFactory", session_factory)
    monkeypatch.setattr(payments.users, "get_or_create_user", get_or_create_user)
    monkeypatch.setattr(
        payments.events,
        "record",
        lambda session, kind, uid, **payload: recorded.append((kind, payload)),
    )
    monkeypatch.setattr(
        payments.ops,
        "paysupport_request",
        lambda u, text, pays: forwarded.append((text, len(pays))),
    )
    context = _context()

    state = await payments.paysupport_message(_update("Paid twice on Sep 1"), context)

    assert state == ConversationHandler.END
    assert recorded == [("paysupport_request", {"text": "Paid twice on Sep 1"})]
    assert forwarded == [("Paid twice on Sep 1", 1)]
    sent = context.bot.send_message.await_args
    assert sent.args[0] == USER_ID
    assert "Спасибо" in sent.args[1]


async def test_refunded_payment_from_telegram_notifies_once(monkeypatch):
    user = User(id=USER_ID, language="en", pro_expires_at=None)
    payment = BillingPayment(user_id=USER_ID, amount=350, currency="XTR", status="refunded")
    results = iter(
        [
            billing.RefundResult(user=user, payment=payment, changed=True, pro_revoked=True),
            billing.RefundResult(user=user, payment=payment, changed=False, pro_revoked=False),
        ]
    )
    ops_calls: list = []

    async def mark_refunded(session, **kwargs):
        assert kwargs["source"] == "telegram"
        return next(results)

    @asynccontextmanager
    async def session_factory():
        yield None

    monkeypatch.setattr(payments, "SessionFactory", session_factory)
    monkeypatch.setattr(payments.billing, "mark_payment_refunded", mark_refunded)
    monkeypatch.setattr(payments.ops, "payment_refunded", lambda u, **kw: ops_calls.append(kw))
    refund = SimpleNamespace(telegram_payment_charge_id="c1", total_amount=350, currency="XTR")
    update = _update()
    update.effective_message.refunded_payment = refund
    context = _context()

    await payments.refunded_payment_callback(update, context)
    await payments.refunded_payment_callback(update, context)

    assert ops_calls == [
        {"amount": 350, "currency": "XTR", "source": "telegram", "pro_revoked": True}
    ]
    assert context.bot.send_message.await_count == 1
    assert "350" in context.bot.send_message.await_args.args[1]
