from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from app.db.models import BillingPayment, User
from app.db.session import SessionFactory
from app.services import billing

USER_ID = 900_000_101


@pytest.fixture(autouse=True)
async def billing_user():
    async with SessionFactory() as session:
        session.add(User(id=USER_ID, language="en"))
        await session.commit()
    yield
    async with SessionFactory() as session:
        await session.execute(delete(User).where(User.id == USER_ID))
        await session.commit()


async def test_trial_uses_five_rag_then_three_prompt_questions():
    now = datetime(2026, 7, 21, 10, tzinfo=UTC)
    async with SessionFactory() as session:
        await billing.start_trial(session, USER_ID, now)
        grants = [await billing.reserve_agent_question(session, USER_ID, now) for _ in range(8)]
        assert [grant.mode for grant in grants] == ["rag"] * 5 + ["prompt"] * 3
        with pytest.raises(billing.AccessLimitExceeded):
            await billing.reserve_agent_question(session, USER_ID, now)


async def test_failed_question_releases_trial_allowance():
    now = datetime(2026, 7, 21, 10, tzinfo=UTC)
    async with SessionFactory() as session:
        user = await billing.start_trial(session, USER_ID, now)
        grant = await billing.reserve_agent_question(session, USER_ID, now)
        assert user.trial_rag_used == 1
        await billing.release_agent_question(session, USER_ID, grant)
        refreshed = await session.get(User, USER_ID)
        assert refreshed.trial_rag_used == 0
        snapshot = await billing.get_billing_snapshot(session, refreshed, now)
        assert snapshot.rag_used == 0


async def test_trial_council_is_available_once_and_released_on_failure():
    now = datetime(2026, 7, 21, 10, tzinfo=UTC)
    async with SessionFactory() as session:
        await billing.start_trial(session, USER_ID, now)
        grant = await billing.reserve_council(session, USER_ID, now)
        with pytest.raises(billing.CouncilUnavailable):
            await billing.reserve_council(session, USER_ID, now)
        await billing.release_council(session, USER_ID, grant)
        await billing.reserve_council(session, USER_ID, now)


async def test_expired_trial_falls_back_to_free():
    started = datetime(2026, 7, 1, 10, tzinfo=UTC)
    async with SessionFactory() as session:
        user = await billing.start_trial(session, USER_ID, started)
        assert billing.effective_plan(user, started + timedelta(days=6)) == "Trial"
        assert billing.effective_plan(user, started + timedelta(days=8)) == "Free"


async def test_successful_payment_activates_pro_idempotently():
    now = datetime(2026, 7, 21, 10, tzinfo=UTC)
    expires = now + timedelta(days=30)
    payload = billing.pro_invoice_payload(USER_ID)
    async with SessionFactory() as session:
        user = await billing.record_successful_payment(
            session,
            user_id=USER_ID,
            invoice_payload=payload,
            currency="XTR",
            amount=299,
            telegram_payment_charge_id="stars-charge-1",
            subscription_expires_at=expires,
            now=now,
        )
        assert billing.effective_plan(user, now) == "Pro"
        assert user.pro_auto_renew is True

        await billing.record_successful_payment(
            session,
            user_id=USER_ID,
            invoice_payload=payload,
            currency="XTR",
            amount=299,
            telegram_payment_charge_id="stars-charge-1",
            subscription_expires_at=expires,
            now=now,
        )
        payments = list(
            (
                await session.scalars(
                    select(BillingPayment).where(BillingPayment.user_id == USER_ID)
                )
            ).all()
        )
        assert len(payments) == 1


def test_invoice_payload_is_bound_to_telegram_user():
    payload = billing.pro_invoice_payload(USER_ID)
    assert billing.payload_user_id(payload) == USER_ID
    assert billing.payload_user_id("aeon:pro:v1:not-a-number") is None
    assert billing.payload_user_id("another-product") is None


async def test_renewal_keeps_original_subscription_charge_for_cancellation():
    now = datetime(2026, 7, 21, 10, tzinfo=UTC)
    payload = billing.pro_invoice_payload(USER_ID)
    async with SessionFactory() as session:
        await billing.record_successful_payment(
            session,
            user_id=USER_ID,
            invoice_payload=payload,
            currency="XTR",
            amount=299,
            telegram_payment_charge_id="subscription-charge",
            is_first_recurring=True,
            now=now,
        )
        user = await billing.record_successful_payment(
            session,
            user_id=USER_ID,
            invoice_payload=payload,
            currency="XTR",
            amount=299,
            telegram_payment_charge_id="renewal-charge",
            is_first_recurring=False,
            now=now + timedelta(days=30),
        )
        assert user.pro_subscription_charge_id == "subscription-charge"
