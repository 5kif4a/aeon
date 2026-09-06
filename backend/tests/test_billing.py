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
            amount=350,
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
            amount=350,
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
            amount=350,
            telegram_payment_charge_id="subscription-charge",
            is_first_recurring=True,
            now=now,
        )
        user = await billing.record_successful_payment(
            session,
            user_id=USER_ID,
            invoice_payload=payload,
            currency="XTR",
            amount=350,
            telegram_payment_charge_id="renewal-charge",
            is_first_recurring=False,
            now=now + timedelta(days=30),
        )
        assert user.pro_subscription_charge_id == "subscription-charge"


async def test_subscription_state_updates_toggle_auto_renew_once():
    now = datetime(2026, 7, 21, 10, tzinfo=UTC)
    async with SessionFactory() as session:
        await billing.record_successful_payment(
            session,
            user_id=USER_ID,
            invoice_payload=billing.pro_invoice_payload(USER_ID),
            currency="XTR",
            amount=350,
            telegram_payment_charge_id="charge-sub-1",
            is_first_recurring=True,
            now=now,
        )
        user = await billing.mark_subscription_canceled(session, USER_ID, source="telegram")
        assert user.pro_auto_renew is False
        # A second cancel (e.g. bot command after Telegram already told us) is a no-op.
        await billing.mark_subscription_canceled(session, USER_ID)
        user = await billing.mark_subscription_restored(session, USER_ID)
        assert user.pro_auto_renew is True
        user = await billing.mark_subscription_payment_failed(session, USER_ID)
        assert user.pro_auto_renew is False
        assert billing.effective_plan(user, now) == "Pro"


async def test_refund_revokes_pro_only_for_the_current_period():
    now = datetime(2026, 7, 21, 10, tzinfo=UTC)
    async with SessionFactory() as session:
        for index, charge in enumerate(["charge-refund-old", "charge-refund-new"]):
            await billing.record_successful_payment(
                session,
                user_id=USER_ID,
                invoice_payload=billing.pro_invoice_payload(USER_ID),
                currency="XTR",
                amount=350,
                telegram_payment_charge_id=charge,
                subscription_expires_at=now + timedelta(days=30 * (index + 1)),
                now=now,
            )
        # Refunding the superseded charge leaves the entitlement alone.
        old = await billing.mark_payment_refunded(
            session,
            user_id=USER_ID,
            telegram_payment_charge_id="charge-refund-old",
            source="admin",
            refunded_by=1,
            now=now,
        )
        assert old.changed and not old.pro_revoked
        assert old.payment.status == "refunded"
        assert billing.effective_plan(old.user, now) == "Pro"

        # Refunding the charge that bought the current period ends Pro right away.
        new = await billing.mark_payment_refunded(
            session,
            user_id=USER_ID,
            telegram_payment_charge_id="charge-refund-new",
            source="telegram",
            now=now,
        )
        assert new.changed and new.pro_revoked
        assert billing.effective_plan(new.user, now) == "Free"
        assert new.user.pro_auto_renew is False

        # Telegram's refunded_payment arriving after our own refund is a no-op.
        again = await billing.mark_payment_refunded(
            session,
            user_id=USER_ID,
            telegram_payment_charge_id="charge-refund-new",
            source="telegram",
            now=now,
        )
        assert not again.changed

        with pytest.raises(billing.PaymentNotFound):
            await billing.mark_payment_refunded(
                session, user_id=USER_ID, telegram_payment_charge_id="nope", source="admin"
            )
