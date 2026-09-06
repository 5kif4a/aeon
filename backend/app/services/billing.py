"""Subscription entitlements, usage limits, and Telegram Stars payment records."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import BillingPayment, DailyUsage, User
from app.services import events

PRO_PAYLOAD_PREFIX = "aeon:pro:v1:"

BillingReminder = Literal["trial_ending", "trial_ended", "pro_expired"]
# "Trial ends tomorrow" goes out once the trial has less than this left.
TRIAL_ENDING_WINDOW = timedelta(hours=24)
# Telegram charges the renewal around the expiry moment; wait before calling Pro expired.
PRO_EXPIRED_GRACE = timedelta(hours=1)
# Never resurface an expiry older than this (protects existing users on first deploy).
REMINDER_MAX_AGE = timedelta(days=3)


class BillingError(RuntimeError):
    pass


class AccessLimitExceeded(BillingError):
    def __init__(self, plan: str):
        super().__init__(f"Daily {plan} question limit reached")
        self.plan = plan


class CouncilUnavailable(BillingError):
    def __init__(self, plan: str):
        super().__init__(f"Council is unavailable for {plan}")
        self.plan = plan


class TrialUnavailable(BillingError):
    pass


@dataclass(frozen=True)
class AccessGrant:
    mode: Literal["prompt", "rag"]
    plan: Literal["Free", "Trial", "Pro"]
    usage_date: date

    @property
    def generation_plan(self) -> str:
        return self.plan if self.mode == "rag" else "Free"


@dataclass(frozen=True)
class CouncilGrant:
    plan: Literal["Trial", "Pro"]
    usage_date: date


@dataclass(frozen=True)
class BillingSnapshot:
    plan: str
    daily_mode: str
    daily_used: int
    daily_limit: int
    daily_remaining: int
    prompt_used: int
    prompt_limit: int
    rag_used: int
    rag_limit: int
    trial_total_used: int
    trial_total_limit: int
    council_used: int
    council_limit: int
    council_remaining: int
    can_start_trial: bool
    trial_started_at: datetime | None
    trial_expires_at: datetime | None
    pro_expires_at: datetime | None
    pro_auto_renew: bool
    pro_price_stars: int


def utc_now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def effective_plan(user: User, now: datetime | None = None) -> Literal["Free", "Trial", "Pro"]:
    current = now or utc_now()
    pro_expires_at = _aware(user.pro_expires_at)
    trial_expires_at = _aware(user.trial_expires_at)
    if pro_expires_at and pro_expires_at > current:
        return "Pro"
    if trial_expires_at and trial_expires_at > current:
        return "Trial"
    return "Free"


def pro_invoice_payload(user_id: int) -> str:
    return f"{PRO_PAYLOAD_PREFIX}{user_id}"


def payload_user_id(payload: str) -> int | None:
    if not payload.startswith(PRO_PAYLOAD_PREFIX):
        return None
    try:
        return int(payload.removeprefix(PRO_PAYLOAD_PREFIX))
    except ValueError:
        return None


async def _locked_user(session: AsyncSession, user_id: int) -> User:
    user = await session.scalar(select(User).where(User.id == user_id).with_for_update())
    if user is None:
        raise BillingError("User not found")
    return user


async def _daily_usage(
    session: AsyncSession, user_id: int, usage_date: date, *, lock: bool = False
) -> DailyUsage:
    statement = select(DailyUsage).where(
        DailyUsage.user_id == user_id, DailyUsage.usage_date == usage_date
    )
    if lock:
        statement = statement.with_for_update()
    usage = await session.scalar(statement)
    if usage is None:
        usage = DailyUsage(user_id=user_id, usage_date=usage_date)
        session.add(usage)
        await session.flush()
    return usage


async def start_trial(session: AsyncSession, user_id: int, now: datetime | None = None) -> User:
    current = now or utc_now()
    user = await _locked_user(session, user_id)
    if effective_plan(user, current) == "Pro":
        raise TrialUnavailable("Pro is already active")
    if user.pro_expires_at is not None:
        raise TrialUnavailable("Trial is unavailable after a Pro subscription")
    if user.trial_started_at is not None:
        raise TrialUnavailable("Trial has already been used")

    settings = get_settings()
    user.plan = "Trial"
    user.trial_started_at = current
    user.trial_expires_at = current + timedelta(days=settings.trial_days)
    user.trial_rag_used = 0
    user.trial_council_used = False
    events.record(session, events.TRIAL_STARTED, user.id, expires_at=user.trial_expires_at)
    await session.commit()
    await session.refresh(user)
    return user


async def reserve_agent_question(
    session: AsyncSession, user_id: int, now: datetime | None = None
) -> AccessGrant:
    current = now or utc_now()
    today = current.date()
    settings = get_settings()
    user = await _locked_user(session, user_id)
    plan = effective_plan(user, current)
    user.plan = plan
    usage = await _daily_usage(session, user_id, today, lock=True)

    if plan == "Pro":
        if usage.rag_questions >= settings.pro_daily_rag_questions:
            raise AccessLimitExceeded(plan)
        usage.rag_questions += 1
        grant = AccessGrant("rag", "Pro", today)
    elif plan == "Trial":
        has_daily_rag = usage.rag_questions < settings.trial_daily_rag_questions
        has_total_rag = user.trial_rag_used < settings.trial_total_rag_questions
        if has_daily_rag and has_total_rag:
            usage.rag_questions += 1
            user.trial_rag_used += 1
            grant = AccessGrant("rag", "Trial", today)
        elif usage.prompt_questions < settings.free_daily_questions:
            usage.prompt_questions += 1
            grant = AccessGrant("prompt", "Trial", today)
        else:
            raise AccessLimitExceeded(plan)
    else:
        if usage.prompt_questions >= settings.free_daily_questions:
            raise AccessLimitExceeded(plan)
        usage.prompt_questions += 1
        grant = AccessGrant("prompt", "Free", today)

    await session.commit()
    return grant


async def release_agent_question(session: AsyncSession, user_id: int, grant: AccessGrant) -> None:
    user = await _locked_user(session, user_id)
    usage = await _daily_usage(session, user_id, grant.usage_date, lock=True)
    if grant.mode == "rag":
        usage.rag_questions = max(usage.rag_questions - 1, 0)
        if grant.plan == "Trial":
            user.trial_rag_used = max(user.trial_rag_used - 1, 0)
    else:
        usage.prompt_questions = max(usage.prompt_questions - 1, 0)
    await session.commit()


async def reserve_council(
    session: AsyncSession, user_id: int, now: datetime | None = None
) -> CouncilGrant:
    current = now or utc_now()
    today = current.date()
    settings = get_settings()
    user = await _locked_user(session, user_id)
    plan = effective_plan(user, current)
    user.plan = plan

    if plan == "Trial":
        if user.trial_council_used:
            raise CouncilUnavailable(plan)
        user.trial_council_used = True
        grant = CouncilGrant("Trial", today)
    elif plan == "Pro":
        usage = await _daily_usage(session, user_id, today, lock=True)
        if usage.council_questions >= settings.pro_daily_council_questions:
            raise CouncilUnavailable(plan)
        usage.council_questions += 1
        grant = CouncilGrant("Pro", today)
    else:
        raise CouncilUnavailable(plan)

    await session.commit()
    return grant


async def release_council(session: AsyncSession, user_id: int, grant: CouncilGrant) -> None:
    user = await _locked_user(session, user_id)
    if grant.plan == "Trial":
        user.trial_council_used = False
    else:
        usage = await _daily_usage(session, user_id, grant.usage_date, lock=True)
        usage.council_questions = max(usage.council_questions - 1, 0)
    await session.commit()


async def get_billing_snapshot(
    session: AsyncSession, user: User, now: datetime | None = None
) -> BillingSnapshot:
    current = now or utc_now()
    settings = get_settings()
    plan = effective_plan(user, current)
    usage = await _daily_usage(session, user.id, current.date())

    if plan == "Pro":
        daily_mode = "rag"
        daily_used = usage.rag_questions
        daily_limit = settings.pro_daily_rag_questions
        prompt_limit = 0
        rag_limit = daily_limit
        council_used = usage.council_questions
        council_limit = settings.pro_daily_council_questions
    elif plan == "Trial":
        has_rag = user.trial_rag_used < settings.trial_total_rag_questions
        daily_mode = (
            "rag"
            if has_rag and usage.rag_questions < settings.trial_daily_rag_questions
            else "prompt"
        )
        daily_used = usage.rag_questions if daily_mode == "rag" else usage.prompt_questions
        daily_limit = (
            settings.trial_daily_rag_questions
            if daily_mode == "rag"
            else settings.free_daily_questions
        )
        prompt_limit = settings.free_daily_questions
        rag_limit = settings.trial_daily_rag_questions
        council_used = int(user.trial_council_used)
        council_limit = 1
    else:
        daily_mode = "prompt"
        daily_used = usage.prompt_questions
        daily_limit = settings.free_daily_questions
        prompt_limit = daily_limit
        rag_limit = 0
        council_used = 0
        council_limit = 0

    return BillingSnapshot(
        plan=plan,
        daily_mode=daily_mode,
        daily_used=daily_used,
        daily_limit=daily_limit,
        daily_remaining=max(daily_limit - daily_used, 0),
        prompt_used=usage.prompt_questions,
        prompt_limit=prompt_limit,
        rag_used=usage.rag_questions,
        rag_limit=rag_limit,
        trial_total_used=user.trial_rag_used,
        trial_total_limit=settings.trial_total_rag_questions,
        council_used=council_used,
        council_limit=council_limit,
        council_remaining=max(council_limit - council_used, 0),
        can_start_trial=(
            user.trial_started_at is None and user.pro_expires_at is None and plan != "Pro"
        ),
        trial_started_at=_aware(user.trial_started_at),
        trial_expires_at=_aware(user.trial_expires_at),
        pro_expires_at=_aware(user.pro_expires_at),
        pro_auto_renew=user.pro_auto_renew and plan == "Pro",
        pro_price_stars=settings.pro_price_stars,
    )


async def record_successful_payment(
    session: AsyncSession,
    *,
    user_id: int,
    invoice_payload: str,
    currency: str,
    amount: int,
    telegram_payment_charge_id: str,
    provider_payment_charge_id: str = "",
    subscription_expires_at: datetime | None = None,
    is_recurring: bool = True,
    is_first_recurring: bool = False,
    now: datetime | None = None,
) -> User:
    current = now or utc_now()
    user = await _locked_user(session, user_id)
    payment = await session.scalar(
        select(BillingPayment).where(
            BillingPayment.telegram_payment_charge_id == telegram_payment_charge_id
        )
    )
    expires_at = subscription_expires_at or current + timedelta(days=30)
    if payment is None:
        payment = BillingPayment(
            user_id=user_id,
            invoice_payload=invoice_payload,
            currency=currency,
            amount=amount,
            telegram_payment_charge_id=telegram_payment_charge_id,
            provider_payment_charge_id=provider_payment_charge_id,
            subscription_expires_at=expires_at,
            is_recurring=is_recurring,
        )
        session.add(payment)
    else:
        payment.subscription_expires_at = expires_at
        payment.status = "paid"

    user.plan = "Pro"
    user.pro_expires_at = expires_at
    if is_first_recurring or not user.pro_subscription_charge_id:
        user.pro_subscription_charge_id = telegram_payment_charge_id
    user.pro_auto_renew = is_recurring
    events.record(
        session,
        events.PAYMENT_SUCCEEDED,
        user.id,
        amount=amount,
        currency=currency,
        renewal=is_recurring and not is_first_recurring,
        expires_at=expires_at,
    )
    await session.commit()
    await session.refresh(user)
    return user


async def mark_subscription_canceled(
    session: AsyncSession, user_id: int, *, source: str = "bot"
) -> User:
    """Auto-renew is off; Pro stays until ``pro_expires_at``.

    ``source`` is ``bot`` for /cancel_subscription and the Mini App, ``telegram`` when the
    user canceled from Telegram's own subscription settings (Bot API ``subscription`` update).
    Idempotent: a repeated cancel does not produce a second event.
    """
    user = await _locked_user(session, user_id)
    if not user.pro_auto_renew:
        return user
    user.pro_auto_renew = False
    events.record(
        session,
        events.SUBSCRIPTION_CANCELED,
        user.id,
        expires_at=user.pro_expires_at,
        source=source,
    )
    await session.commit()
    await session.refresh(user)
    return user


async def mark_subscription_restored(session: AsyncSession, user_id: int) -> User:
    """The user re-enabled a canceled subscription in Telegram; renewals will resume."""
    user = await _locked_user(session, user_id)
    if user.pro_auto_renew:
        return user
    user.pro_auto_renew = True
    events.record(session, events.SUBSCRIPTION_RESTORED, user.id, expires_at=user.pro_expires_at)
    await session.commit()
    await session.refresh(user)
    return user


async def mark_subscription_payment_failed(session: AsyncSession, user_id: int) -> User:
    """Telegram could not charge the renewal (usually not enough Stars).

    Pro keeps working until ``pro_expires_at``; auto-renew is switched off so the UI stops
    promising a renewal. A later successful charge turns it back on via
    ``record_successful_payment``, and the ``pro_expired`` reminder covers the no-charge case.
    """
    user = await _locked_user(session, user_id)
    user.pro_auto_renew = False
    events.record(
        session, events.SUBSCRIPTION_PAYMENT_FAILED, user.id, expires_at=user.pro_expires_at
    )
    await session.commit()
    await session.refresh(user)
    return user


class PaymentNotFound(Exception):
    """No payment with that charge id belongs to the user."""


async def get_payment(session: AsyncSession, user_id: int, payment_id) -> BillingPayment | None:
    return await session.scalar(
        select(BillingPayment).where(
            BillingPayment.id == payment_id, BillingPayment.user_id == user_id
        )
    )


@dataclass(frozen=True, slots=True)
class RefundResult:
    user: User
    payment: BillingPayment
    changed: bool  # False when the payment had already been marked refunded
    pro_revoked: bool


async def mark_payment_refunded(
    session: AsyncSession,
    *,
    user_id: int,
    telegram_payment_charge_id: str,
    source: str,
    refunded_by: int | None = None,
    now: datetime | None = None,
) -> RefundResult:
    """Record a Stars refund and take Pro away for the period that payment bought.

    ``source`` is ``admin`` (we called ``refundStarPayment``) or ``telegram`` (Telegram's
    support refunded it and the bot received ``refunded_payment``). Idempotent: a payment
    already marked refunded is returned unchanged, so both paths can fire for one refund.
    Pro is revoked only when the refunded charge covers the user's current Pro period; an
    older, already superseded payment leaves the entitlement alone.
    """
    current = now or utc_now()
    user = await _locked_user(session, user_id)
    payment = await session.scalar(
        select(BillingPayment).where(
            BillingPayment.telegram_payment_charge_id == telegram_payment_charge_id,
            BillingPayment.user_id == user_id,
        )
    )
    if payment is None:
        raise PaymentNotFound(telegram_payment_charge_id)
    if payment.status == "refunded":
        return RefundResult(user=user, payment=payment, changed=False, pro_revoked=False)

    payment.status = "refunded"
    pro_expires_at = _aware(user.pro_expires_at)
    paid_until = _aware(payment.subscription_expires_at)
    revoked = (
        pro_expires_at is not None
        and pro_expires_at > current
        and (paid_until is None or paid_until >= pro_expires_at)
    )
    if revoked:
        user.pro_expires_at = current
        user.pro_auto_renew = False
        user.plan = effective_plan(user, current)
    events.record(
        session,
        events.PAYMENT_REFUNDED,
        user.id,
        amount=payment.amount,
        currency=payment.currency,
        source=source,
        refunded_by=refunded_by,
        pro_revoked=revoked,
    )
    await session.commit()
    await session.refresh(user)
    await session.refresh(payment)
    return RefundResult(user=user, payment=payment, changed=True, pro_revoked=revoked)


def pending_billing_reminder(user: User, now: datetime | None = None) -> BillingReminder | None:
    """Which Stars upsell reminder the user is owed right now, if any.

    Pure function over the user row so the job stays testable without a database.
    Each reminder is sent once per expiry; the ``*_reminded_at`` columns are the dedupe.
    """
    current = now or utc_now()
    plan = effective_plan(user, current)
    trial_expires_at = _aware(user.trial_expires_at)
    pro_expires_at = _aware(user.pro_expires_at)

    if plan == "Pro":
        return None

    if (
        pro_expires_at is not None
        and current - REMINDER_MAX_AGE <= pro_expires_at <= current - PRO_EXPIRED_GRACE
    ):
        reminded_at = _aware(user.pro_expired_reminded_at)
        if reminded_at is None or reminded_at < pro_expires_at:
            return "pro_expired"
        return None

    if trial_expires_at is None or pro_expires_at is not None:
        return None

    if plan == "Trial":
        if (
            trial_expires_at - current <= TRIAL_ENDING_WINDOW
            and user.trial_ending_reminded_at is None
        ):
            return "trial_ending"
        return None

    if current - REMINDER_MAX_AGE <= trial_expires_at and user.trial_ended_reminded_at is None:
        return "trial_ended"
    return None


async def billing_reminder_candidates(
    session: AsyncSession, now: datetime | None = None
) -> list[User]:
    """Users whose trial or Pro is ending or has recently ended; the job filters further."""
    current = now or utc_now()
    cutoff = current - REMINDER_MAX_AGE
    result = await session.execute(
        select(User).where(
            or_(
                User.trial_expires_at >= cutoff,
                User.pro_expires_at >= cutoff,
            )
        )
    )
    return list(result.scalars().all())


async def mark_billing_reminder_sent(
    session: AsyncSession, user: User, reminder: BillingReminder, now: datetime | None = None
) -> None:
    current = now or utc_now()
    if reminder == "trial_ending":
        user.trial_ending_reminded_at = current
    elif reminder == "trial_ended":
        user.trial_ended_reminded_at = current
    else:
        user.pro_expired_reminded_at = current
    await session.commit()
