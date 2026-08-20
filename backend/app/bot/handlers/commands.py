"""Bot navigation, advisor dialogue, Council, and notification settings."""

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from app.agents import AGENTS
from app.bot import chat, messaging, ui, webapp
from app.bot.handlers.onboarding import send_home
from app.bot.handlers.payments import (
    cancel_subscription_command,
    paysupport_command,
    precheckout_callback,
    subscribe_command,
    successful_payment_callback,
)
from app.db.session import SessionFactory
from app.i18n import normalize_language, t
from app.services import users


async def _user_for_update(update: Update):
    telegram_user = update.effective_user
    async with SessionFactory() as session:
        return await users.get_or_create_user(
            session,
            update.effective_chat.id,
            name=(telegram_user.first_name or "")[:64],
            language=normalize_language(telegram_user.language_code),
        )


async def _user_language(chat_id: int) -> str:
    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
    return user.language if user else "en"


async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_agent_picker(update.effective_chat.id, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _user_for_update(update)
    await webapp.set_chat_menu_button(context.bot, user.id, user.language)
    await send_home(context.bot, user.id, user)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = await _user_for_update(update)
    await context.bot.send_message(
        user.id,
        _settings_text(user),
        reply_markup=ui.settings_keyboard(user),
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    language = await chat.clear_active_agent(context.bot, chat_id, announce=False)
    user = await _user_for_update(update)
    await context.bot.send_message(
        chat_id,
        t(language, "agent_mode_closed"),
        reply_markup=ui.home_keyboard(language, profile_complete=user.birth_date is not None),
    )


async def council_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = " ".join(context.args).strip()
    if question:
        await chat.process_council_message(context.bot, update.effective_chat.id, question)
        return
    context.user_data["awaiting_council"] = True
    language = await _user_language(update.effective_chat.id)
    await context.bot.send_message(update.effective_chat.id, t(language, "council_prompt"))


async def agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    agent_id = query.data.split(":", 1)[1]
    chat_id = update.effective_chat.id
    if agent_id == "picker" or agent_id not in AGENTS:
        await _send_agent_picker(chat_id, context)
        return

    pending_question = context.user_data.pop("pending_question", "")
    context.user_data.pop("awaiting_council", None)
    await chat.set_active_agent(context.bot, chat_id, agent_id, announce=False)
    language = await _user_language(chat_id)
    await messaging.try_edit(
        context.bot,
        chat_id,
        query.message.message_id,
        chat.build_agent_intro(agent_id, language),
        ui.post_answer_keyboard(language),
    )
    if pending_question:
        await chat.process_agent_message(context.bot, chat_id, pending_question)


async def navigation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = await _user_for_update(update)

    if data == "menu:home":
        context.user_data.clear()
        await send_home(context.bot, user.id, user)
        return
    if data == "council:start":
        pending_question = context.user_data.pop("pending_question", "")
        if pending_question:
            context.user_data.pop("awaiting_council", None)
            await chat.process_council_message(context.bot, user.id, pending_question)
            return
        context.user_data["awaiting_council"] = True
        await context.bot.send_message(
            user.id,
            t(user.language, "council_prompt"),
            reply_markup=ui.back_home_keyboard(user.language),
        )
        return
    if data == "billing:subscribe":
        await subscribe_command(update, context)
        return
    if data == "daily:done":
        async with SessionFactory() as session:
            db_user = await users.get_or_create_user(session, user.id)
            streak = await users.record_daily_checkin(session, db_user)
        await context.bot.send_message(
            user.id,
            t(user.language, "daily_checkin_saved", streak=streak),
            reply_markup=ui.post_answer_keyboard(user.language),
        )
        return
    if data.startswith("settings:"):
        await _handle_settings_callback(update, context, user)


async def _handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    query = update.callback_query
    data = query.data
    if data == "settings:open":
        await context.bot.send_message(
            user.id,
            _settings_text(user),
            reply_markup=ui.settings_keyboard(user),
        )
        return
    if data == "settings:time":
        await messaging.try_edit(
            context.bot,
            user.id,
            query.message.message_id,
            t(user.language, "choose_reminder_time"),
            ui.reminder_time_keyboard(user.language),
        )
        return
    if data == "settings:timezone":
        await messaging.try_edit(
            context.bot,
            user.id,
            query.message.message_id,
            t(user.language, "choose_timezone"),
            ui.timezone_keyboard(user.language),
        )
        return

    fields: dict = {}
    if data == "settings:daily":
        fields["daily_notifications_enabled"] = user.daily_notifications_enabled is False
    elif data == "settings:weekly":
        fields["weekly_notifications_enabled"] = user.weekly_notifications_enabled is False
    elif data.startswith("settings:hour:"):
        fields["reminder_hour"] = min(max(int(data.rsplit(":", 1)[1]), 0), 23)
    elif data.startswith("settings:tz:"):
        timezone = ui.timezone_from_token(data.rsplit(":", 1)[1])
        if timezone:
            fields["reminder_timezone"] = timezone
    elif data.startswith("settings:language:"):
        fields["language"] = normalize_language(data.rsplit(":", 1)[1])

    if fields:
        async with SessionFactory() as session:
            db_user = await users.get_or_create_user(session, user.id)
            user = await users.update_user(session, db_user, fields)
        if "language" in fields:
            await webapp.set_chat_menu_button(context.bot, user.id, user.language)

    await messaging.try_edit(
        context.bot,
        user.id,
        query.message.message_id,
        _settings_text(user),
        ui.settings_keyboard(user),
    )


def _settings_text(user) -> str:
    reminder_hour = user.reminder_hour if user.reminder_hour is not None else 9
    reminder_timezone = user.reminder_timezone or "UTC"
    return t(
        user.language,
        "settings_title",
        hour=reminder_hour,
        timezone=ui.timezone_label(reminder_timezone),
    )


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    if not text:
        return
    if context.user_data.pop("awaiting_council", False):
        await chat.process_council_message(context.bot, chat_id, text)
        return
    if await chat.process_agent_message(context.bot, chat_id, text):
        return

    context.user_data["pending_question"] = text
    language = await _user_language(chat_id)
    await context.bot.send_message(
        chat_id,
        t(language, "choose_agent_for_question"),
        reply_markup=ui.agent_picker_keyboard(language),
    )


async def _send_agent_picker(
    chat_id: int, context: ContextTypes.DEFAULT_TYPE, message_id: int | None = None
) -> None:
    language = await _user_language(chat_id)
    await webapp.set_chat_menu_button(context.bot, chat_id, language)
    text = t(language, "choose_agent")
    keyboard = ui.agent_picker_keyboard(language)
    if message_id and await messaging.try_edit(context.bot, chat_id, message_id, text, keyboard):
        return
    await context.bot.send_message(chat_id, text, reply_markup=keyboard)


def build_command_handlers() -> list:
    from telegram.ext import PreCheckoutQueryHandler

    return [
        CommandHandler(["agents", "agent"], agents_command),
        CommandHandler(["app", "menu"], menu_command),
        CommandHandler("settings", settings_command),
        CommandHandler(["stop", "reset_agent"], stop_command),
        CommandHandler("council", council_command),
        CommandHandler("subscribe", subscribe_command),
        CommandHandler("cancel_subscription", cancel_subscription_command),
        CommandHandler("paysupport", paysupport_command),
        PreCheckoutQueryHandler(precheckout_callback),
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback),
        CallbackQueryHandler(agent_callback, pattern=r"^agent:"),
        CallbackQueryHandler(
            navigation_callback,
            pattern=r"^(menu:home|council:start|billing:subscribe|daily:done|settings:)",
        ),
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message),
    ]
