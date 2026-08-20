"""Telegram Stars subscription commands and payment update handlers."""

from datetime import timedelta

from telegram import LabeledPrice, Update
from telegram.ext import ContextTypes

from app.bot import ui
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.i18n import t
from app.services import billing, users


async def _user(chat_id: int):
    async with SessionFactory() as session:
        return await users.get_or_create_user(session, chat_id)


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _user(update.effective_user.id)
    settings = get_settings()
    await context.bot.send_invoice(
        chat_id=user.id,
        title=t(user.language, "payment_pro_title"),
        description=t(user.language, "payment_pro_description"),
        payload=billing.pro_invoice_payload(user.id),
        currency="XTR",
        prices=[LabeledPrice(t(user.language, "payment_pro_price"), settings.pro_price_stars)],
        subscription_period=timedelta(days=30),
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query is None:
        return
    settings = get_settings()
    payload_user = billing.payload_user_id(query.invoice_payload)
    valid = (
        payload_user == query.from_user.id
        and query.currency == "XTR"
        and query.total_amount == settings.pro_price_stars
    )
    language = (await _user(query.from_user.id)).language
    await query.answer(
        ok=valid,
        error_message=None if valid else t(language, "payment_invalid"),
    )


async def successful_payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.effective_message
    payment = message.successful_payment if message else None
    if payment is None:
        return
    user_id = update.effective_user.id
    if billing.payload_user_id(payment.invoice_payload) != user_id:
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
    await context.bot.send_message(
        user_id,
        t(user.language, "payment_success"),
        reply_markup=ui.home_keyboard(user.language, profile_complete=user.birth_date is not None),
    )


async def cancel_subscription_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
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
        user = await billing.mark_subscription_canceled(session, user.id)
    await context.bot.send_message(
        user.id,
        t(
            user.language,
            "payment_canceled",
            date=user.pro_expires_at.date().isoformat() if user.pro_expires_at else "—",
        ),
        reply_markup=ui.home_keyboard(user.language, profile_complete=user.birth_date is not None),
    )


async def paysupport_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _user(update.effective_user.id)
    await context.bot.send_message(user.id, t(user.language, "payment_support"))
