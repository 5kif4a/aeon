"""Telegram Stars subscription commands and payment update handlers."""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.ext import (
    BaseHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot import ui
from app.db.models import BillingPayment
from app.db.session import SessionFactory
from app.i18n import t
from app.services import billing, events, ops, users

logger = logging.getLogger(__name__)


async def _user(chat_id: int):
    async with SessionFactory() as session:
        return await users.get_or_create_user(session, chat_id)


def invoice_texts(language: str, period: billing.BillingPeriod) -> dict[str, str]:
    """Title, description and price label of a Pro invoice, shared by the bot and the API."""
    if period == "year":
        return {
            "title": t(language, "payment_pro_title"),
            "description": t(language, "payment_pro_year_description"),
            "label": t(language, "payment_pro_year_price"),
        }
    return {
        "title": t(language, "payment_pro_title"),
        "description": t(language, "payment_pro_description"),
        "label": t(language, "payment_pro_price"),
    }


def _invoice_keyboard(language: str, period: billing.BillingPeriod) -> InlineKeyboardMarkup:
    # Telegram requires the first button of an invoice to be the Pay button. Under the monthly
    # invoice the year is offered as a second button, so it costs no extra message.
    price = billing.pro_price_stars(period)
    rows = [[InlineKeyboardButton(t(language, "payment_pay_button", price=price), pay=True)]]
    if period == "month":
        rows.append(
            [
                InlineKeyboardButton(
                    t(
                        language,
                        "payment_year_button",
                        price=billing.pro_price_stars("year"),
                        discount=billing.pro_year_discount_percent(),
                    ),
                    callback_data="billing:subscribe_year",
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


async def send_pro_invoice(bot, user, period: billing.BillingPeriod, *, source: str) -> None:
    texts = invoice_texts(user.language, period)
    await bot.send_invoice(
        chat_id=user.id,
        title=texts["title"],
        description=texts["description"],
        payload=billing.pro_invoice_payload(user.id, period),
        currency="XTR",
        prices=[LabeledPrice(texts["label"], billing.pro_price_stars(period))],
        # The year is a one-off purchase: Telegram subscriptions only come in 30-day periods.
        subscription_period=timedelta(days=30) if period == "month" else None,
        reply_markup=_invoice_keyboard(user.language, period),
    )
    await record_invoice_opened(user.id, period, source)


async def record_invoice_opened(user_id: int, period: billing.BillingPeriod, source: str) -> None:
    """The step between the limit and the payment; without it the funnel has a hole."""
    async with SessionFactory() as session:
        events.record(
            session,
            events.INVOICE_OPENED,
            user_id,
            period=period,
            price=billing.pro_price_stars(period),
            source=source,
        )
        await session.commit()


async def subscribe_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE, *, source: str | None = None
) -> None:
    user = await _user(update.effective_user.id)
    if source is None:
        source = "button" if update.callback_query is not None else "command"
    await send_pro_invoice(context.bot, user, "month", source=source)


async def subscribe_year_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _user(update.effective_user.id)
    await send_pro_invoice(context.bot, user, "year", source="year_button")


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query is None:
        return
    payload_user = billing.payload_user_id(query.invoice_payload)
    period = billing.payload_period(query.invoice_payload)
    valid = (
        payload_user == query.from_user.id
        and period is not None
        and query.currency == "XTR"
        and query.total_amount == billing.pro_price_stars(period)
    )
    language = (await _user(query.from_user.id)).language
    await query.answer(
        ok=valid,
        error_message=None if valid else t(language, "payment_invalid"),
    )


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    payment = message.successful_payment if message else None
    if payment is None:
        return
    user_id = update.effective_user.id
    if billing.payload_user_id(payment.invoice_payload) != user_id:
        logger.error(
            "Successful payment ignored: payload does not match payer "
            "(user_id=%s payload=%r charge_id=%s)",
            user_id,
            payment.invoice_payload,
            payment.telegram_payment_charge_id,
        )
        return

    async with SessionFactory() as session:
        user = await billing.record_successful_payment(
            session,
            user_id=user_id,
            invoice_payload=payment.invoice_payload,
            currency=payment.currency,
            amount=payment.total_amount,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
            provider_payment_charge_id=payment.provider_payment_charge_id,
            subscription_expires_at=payment.subscription_expiration_date,
            is_recurring=bool(payment.is_recurring),
            is_first_recurring=bool(payment.is_first_recurring),
        )
    period = billing.payload_period(payment.invoice_payload) or "month"
    ops.payment_succeeded(
        user,
        amount=payment.total_amount,
        currency=payment.currency,
        renewal=bool(payment.is_recurring) and not bool(payment.is_first_recurring),
        expires_at=user.pro_expires_at,
        period=period,
    )
    if period == "year":
        text = t(
            user.language,
            "payment_success_year",
            date=user.pro_expires_at.date().isoformat() if user.pro_expires_at else "—",
        )
    else:
        text = t(user.language, "payment_success")
    await context.bot.send_message(user_id, text, reply_markup=ui.home_keyboard(user.language))


async def cancel_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _user(update.effective_user.id)
    if billing.effective_plan(user) != "Pro" or not user.pro_subscription_charge_id:
        await context.bot.send_message(
            user.id,
            t(user.language, "payment_no_subscription"),
            reply_markup=ui.limit_keyboard(user.language, billing.effective_plan(user)),
        )
        return
    await context.bot.edit_user_star_subscription(
        user.id, user.pro_subscription_charge_id, is_canceled=True
    )
    async with SessionFactory() as session:
        user = await billing.mark_subscription_canceled(session, user.id, source="bot")
    ops.subscription_canceled(user, source="bot")
    await context.bot.send_message(
        user.id,
        t(
            user.language,
            "payment_canceled",
            date=user.pro_expires_at.date().isoformat() if user.pro_expires_at else "—",
        ),
        reply_markup=ui.home_keyboard(user.language),
    )


# --- /paysupport -------------------------------------------------------------------------------
#
# Telegram requires every bot that accepts payments to answer /paysupport. Ours explains the
# policy and then waits for one message, which is forwarded to the ops group together with the
# user's recent charges so the operator can act (refund from the admin panel, grant Pro, reply).

PAYSUPPORT_MESSAGE = 1
PAYSUPPORT_TIMEOUT_SECONDS = 15 * 60


async def paysupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await _user(update.effective_user.id)
    await context.bot.send_message(user.id, t(user.language, "payment_support"))
    return PAYSUPPORT_MESSAGE


async def paysupport_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.effective_message.text or "").strip()
    if not text:
        return PAYSUPPORT_MESSAGE
    user_id = update.effective_user.id
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, user_id)
        payments = list(
            await session.scalars(
                select(BillingPayment)
                .where(BillingPayment.user_id == user_id)
                .order_by(BillingPayment.created_at.desc())
                .limit(3)
            )
        )
        events.record(session, events.PAYSUPPORT_REQUEST, user_id, text=text[:1000])
        await session.commit()
    ops.paysupport_request(user, text, payments)
    await context.bot.send_message(
        user.id,
        t(user.language, "payment_support_received"),
        reply_markup=ui.home_keyboard(user.language),
    )
    return ConversationHandler.END


async def paysupport_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = await _user(update.effective_user.id)
    await context.bot.send_message(
        user.id,
        t(user.language, "payment_support_canceled"),
        reply_markup=ui.home_keyboard(user.language),
    )
    return ConversationHandler.END


async def paysupport_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END


def build_paysupport_handler() -> ConversationHandler:
    private = filters.ChatType.PRIVATE
    return ConversationHandler(
        entry_points=[CommandHandler("paysupport", paysupport_command, filters=private)],
        states={
            PAYSUPPORT_MESSAGE: [
                MessageHandler(private & filters.TEXT & ~filters.COMMAND, paysupport_message),
            ],
            ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, paysupport_timeout)],
        },
        fallbacks=[CommandHandler("cancel", paysupport_cancel, filters=private)],
        conversation_timeout=PAYSUPPORT_TIMEOUT_SECONDS,
        allow_reentry=True,
    )


# --- refunds -------------------------------------------------------------------------------------


async def refunded_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Telegram refunded a Stars payment (its support, or our own refundStarPayment call)."""
    message = update.effective_message
    refund = message.refunded_payment if message else None
    if refund is None:
        return
    user_id = update.effective_user.id
    async with SessionFactory() as session:
        try:
            result = await billing.mark_payment_refunded(
                session,
                user_id=user_id,
                telegram_payment_charge_id=refund.telegram_payment_charge_id,
                source="telegram",
            )
        except billing.PaymentNotFound:
            logger.error(
                "Refund for an unknown charge (user_id=%s charge_id=%s)",
                user_id,
                refund.telegram_payment_charge_id,
            )
            return
    if not result.changed:  # already handled by the admin-panel refund
        return
    user = result.user
    ops.payment_refunded(
        user,
        amount=refund.total_amount,
        currency=refund.currency,
        source="telegram",
        pro_revoked=result.pro_revoked,
    )
    await context.bot.send_message(
        user.id,
        t(user.language, "payment_refunded", amount=refund.total_amount),
        reply_markup=ui.home_keyboard(user.language),
    )


# --- Bot API 10.2 `subscription` updates ---------------------------------------------------
#
# Telegram tells the bot when the user cancels a Stars subscription from Telegram's own
# settings ("canceled"), re-enables it ("active"), or a renewal charge fails ("failed").
# python-telegram-bot 22.x predates this update type: `Update.de_json` keeps the unknown
# field in `update.api_kwargs`, and the type must be requested explicitly in `allowed_updates`
# (see `app.bot.application.ALLOWED_UPDATES`). Once PTB grows `Update.subscription`, the
# parser below picks it up without changes here.

SUBSCRIPTION_UPDATE_KEY = "subscription"
SUBSCRIPTION_STATES = ("canceled", "active", "failed")


@dataclass(frozen=True, slots=True)
class SubscriptionUpdate:
    user_id: int
    invoice_payload: str
    state: str


def parse_subscription_update(update: Update) -> SubscriptionUpdate | None:
    raw: Any = update.api_kwargs.get(SUBSCRIPTION_UPDATE_KEY)
    if raw is None:
        raw = getattr(update, SUBSCRIPTION_UPDATE_KEY, None)
    if raw is None:
        return None
    if isinstance(raw, dict):
        user = raw.get("user") or {}
        user_id = user.get("id")
        payload = raw.get("invoice_payload")
        state = raw.get("state")
    else:  # a future PTB object
        user_id = getattr(getattr(raw, "user", None), "id", None)
        payload = getattr(raw, "invoice_payload", None)
        state = getattr(raw, "state", None)
    if not isinstance(user_id, int) or not isinstance(payload, str) or not isinstance(state, str):
        return None
    return SubscriptionUpdate(user_id=user_id, invoice_payload=payload, state=state)


class SubscriptionUpdateHandler(BaseHandler[Update, ContextTypes.DEFAULT_TYPE, None]):
    """Matches only updates that carry a `subscription` object."""

    def check_update(self, update: object) -> bool:
        return isinstance(update, Update) and parse_subscription_update(update) is not None


async def subscription_update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    event = parse_subscription_update(update)
    if event is None:
        return
    if billing.payload_user_id(event.invoice_payload) != event.user_id:
        logger.error(
            "Subscription update ignored: payload does not match user (user_id=%s payload=%r)",
            event.user_id,
            event.invoice_payload,
        )
        return
    if event.state not in SUBSCRIPTION_STATES:
        logger.warning("Unknown subscription state %r for user %s", event.state, event.user_id)
        return

    async with SessionFactory() as session:
        if event.state == "canceled":
            user = await billing.mark_subscription_canceled(
                session, event.user_id, source="telegram"
            )
        elif event.state == "active":
            user = await billing.mark_subscription_restored(session, event.user_id)
        else:
            user = await billing.mark_subscription_payment_failed(session, event.user_id)

    date = user.pro_expires_at.date().isoformat() if user.pro_expires_at else "—"
    if event.state == "canceled":
        ops.subscription_canceled(user, source="telegram")
        text = t(user.language, "payment_canceled", date=date)
        keyboard = ui.home_keyboard(user.language)
    elif event.state == "active":
        ops.subscription_restored(user)
        text = t(user.language, "payment_restored", date=date)
        keyboard = ui.home_keyboard(user.language)
    else:
        ops.subscription_payment_failed(user)
        text = t(user.language, "payment_renewal_failed", date=date)
        keyboard = ui.limit_keyboard(user.language, billing.effective_plan(user))
    try:
        await context.bot.send_message(user.id, text, reply_markup=keyboard)
    except Exception as error:  # the user may have blocked the bot; the state is already saved
        logger.warning("Subscription notice failed for %s: %s", user.id, error)
