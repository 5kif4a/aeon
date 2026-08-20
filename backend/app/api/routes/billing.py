"""Freemium status and Telegram Stars subscription endpoints."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException
from telegram import LabeledPrice
from telegram.error import TelegramError

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas import BillingStatusOut, CancelSubscriptionOut, CheckoutOut
from app.bot import runtime
from app.core.config import get_settings
from app.i18n import t
from app.services import billing

router = APIRouter(prefix="/billing", tags=["billing"])


async def _status(session: SessionDep, user: CurrentUser) -> BillingStatusOut:
    snapshot = await billing.get_billing_snapshot(session, user)
    return BillingStatusOut.from_snapshot(snapshot)


@router.get("/status", response_model=BillingStatusOut)
async def billing_status(user: CurrentUser, session: SessionDep) -> BillingStatusOut:
    return await _status(session, user)


@router.post("/trial", response_model=BillingStatusOut)
async def activate_trial(user: CurrentUser, session: SessionDep) -> BillingStatusOut:
    try:
        user = await billing.start_trial(session, user.id)
    except billing.TrialUnavailable as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return await _status(session, user)


@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(user: CurrentUser) -> CheckoutOut:
    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Telegram bot is not running")

    settings = get_settings()
    try:
        invoice_link = await application.bot.create_invoice_link(
            title=t(user.language, "payment_pro_title"),
            description=t(user.language, "payment_pro_description"),
            payload=billing.pro_invoice_payload(user.id),
            currency="XTR",
            prices=[
                LabeledPrice(t(user.language, "payment_pro_price"), settings.pro_price_stars)
            ],
            subscription_period=timedelta(days=30),
        )
    except TelegramError as error:
        raise HTTPException(status_code=502, detail="Could not create Telegram invoice") from error
    return CheckoutOut(invoiceLink=invoice_link, priceStars=settings.pro_price_stars)


@router.post("/cancel", response_model=CancelSubscriptionOut)
async def cancel_subscription(
    user: CurrentUser, session: SessionDep
) -> CancelSubscriptionOut:
    if billing.effective_plan(user) != "Pro" or not user.pro_subscription_charge_id:
        raise HTTPException(status_code=409, detail="No active Pro subscription")
    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Telegram bot is not running")
    try:
        await application.bot.edit_user_star_subscription(
            user.id, user.pro_subscription_charge_id, is_canceled=True
        )
    except TelegramError as error:
        raise HTTPException(status_code=502, detail="Could not cancel Telegram subscription") from error
    user = await billing.mark_subscription_canceled(session, user.id)
    return CancelSubscriptionOut(ok=True, activeUntil=user.pro_expires_at)
