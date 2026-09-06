"""Postgres-backed tests: product event recording and the stats collector."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.db.models import BillingPayment, DailyUsage, ProductEvent, User
from app.db.session import SessionFactory
from app.services import billing, events, stats, users

USER_ID = 900_000_301
OTHER_USER_ID = 900_000_302


@pytest.fixture(autouse=True)
async def cleanup():
    yield
    async with SessionFactory() as session:
        await session.execute(delete(User).where(User.id.in_([USER_ID, OTHER_USER_ID])))
        await session.execute(
            delete(ProductEvent).where(ProductEvent.type == events.OPS_DIGEST_SENT)
        )
        await session.commit()


async def _events_of(user_id: int) -> list[ProductEvent]:
    async with SessionFactory() as session:
        result = await session.execute(
            select(ProductEvent)
            .where(ProductEvent.user_id == user_id)
            .order_by(ProductEvent.created_at)
        )
        return list(result.scalars())


async def test_user_creation_records_one_event_even_when_called_twice():
    async with SessionFactory() as session:
        await users.get_or_create_user(session, USER_ID, language="ru")
    async with SessionFactory() as session:
        await users.get_or_create_user(session, USER_ID, language="ru")

    recorded = await _events_of(USER_ID)
    assert [event.type for event in recorded] == [events.USER_CREATED]
    assert recorded[0].payload == {"language": "ru"}


async def test_billing_transitions_are_recorded_as_events():
    now = datetime(2026, 9, 7, 10, tzinfo=UTC)
    async with SessionFactory() as session:
        await users.get_or_create_user(session, USER_ID)
        await billing.start_trial(session, USER_ID, now)
        await billing.record_successful_payment(
            session,
            user_id=USER_ID,
            invoice_payload=billing.pro_invoice_payload(USER_ID),
            currency="XTR",
            amount=350,
            telegram_payment_charge_id="charge-ops-1",
            is_recurring=True,
            is_first_recurring=True,
            now=now,
        )
        await billing.mark_subscription_canceled(session, USER_ID)

    recorded = {event.type: event.payload for event in await _events_of(USER_ID)}
    assert set(recorded) == {
        events.USER_CREATED,
        events.TRIAL_STARTED,
        events.PAYMENT_SUCCEEDED,
        events.SUBSCRIPTION_CANCELED,
    }
    assert recorded[events.PAYMENT_SUCCEEDED]["amount"] == 350
    assert recorded[events.PAYMENT_SUCCEEDED]["renewal"] is False
    assert recorded[events.PAYMENT_SUCCEEDED]["expires_at"].startswith("2026-10-07")


async def test_collect_stats_aggregates_window_and_current_state():
    now = datetime(2026, 9, 7, 12, tzinfo=UTC)
    window = stats.Window("test", now - timedelta(hours=12), now)
    async with SessionFactory() as session:
        session.add_all(
            [
                User(
                    id=USER_ID,
                    language="en",
                    created_at=now - timedelta(hours=1),
                    pro_expires_at=now + timedelta(days=2),
                    pro_auto_renew=False,
                ),
                User(
                    id=OTHER_USER_ID,
                    language="ru",
                    created_at=now - timedelta(days=30),
                    trial_expires_at=now + timedelta(days=5),
                ),
            ]
        )
        await session.flush()
        session.add_all(
            [
                DailyUsage(
                    user_id=USER_ID, usage_date=now.date(), prompt_questions=2, rag_questions=3
                ),
                DailyUsage(user_id=OTHER_USER_ID, usage_date=now.date(), council_questions=1),
                BillingPayment(
                    user_id=USER_ID,
                    invoice_payload="p",
                    currency="XTR",
                    amount=350,
                    telegram_payment_charge_id="charge-ops-2",
                    created_at=now - timedelta(hours=2),
                ),
            ]
        )
        # Events default to the wall-clock now(); pin them inside the test window.
        for event_type, kind in (
            (events.TRIAL_STARTED, None),
            (events.QUESTION_LIMIT_HIT, "agent"),
            (events.QUESTION_LIMIT_HIT, "council"),
        ):
            payload = {"kind": kind} if kind else {}
            events.record(session, event_type, OTHER_USER_ID, **payload).created_at = (
                now - timedelta(hours=1)
            )
        await session.commit()

        collected = await stats.collect_stats(session, window, now)

    assert collected.new_users == 1
    assert collected.active_users == 2
    assert (collected.prompt_questions, collected.rag_questions, collected.council_questions) == (
        2,
        3,
        1,
    )
    assert (collected.payments_count, collected.payments_stars) == (1, 350)
    assert collected.trials_started == 1
    assert collected.limit_hits == 2
    assert collected.pro_active >= 1 and collected.trial_active >= 1
    assert collected.pro_expiring_soon >= 1 and collected.pro_not_renewing >= 1


async def test_digest_marker_dedupes_by_period_and_date():
    async with SessionFactory() as session:
        events.record(session, events.OPS_DIGEST_SENT, period="daily", date="2026-09-07")
        await session.commit()

        assert await events.last_event_at(
            session, events.OPS_DIGEST_SENT, period="daily", date="2026-09-07"
        )
        assert (
            await events.last_event_at(
                session, events.OPS_DIGEST_SENT, period="weekly", date="2026-09-07"
            )
            is None
        )
        assert (
            await events.last_event_at(
                session, events.OPS_DIGEST_SENT, period="daily", date="2026-09-08"
            )
            is None
        )
