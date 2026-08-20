"""Fast first-run experience and optional birth-date setup for the life calendar."""

import calendar
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot import messaging, ui, webapp
from app.db.models import User
from app.db.session import SessionFactory
from app.i18n import DEFAULT_LANGUAGE, birth_picker_text, month_labels, normalize_language, t
from app.services import users

BIRTH = 1


def _lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", DEFAULT_LANGUAGE)


async def send_home(
    bot, chat_id: int, user: User, *, welcome: bool = False, edit_message_id: int | None = None
) -> None:
    key = "home_welcome" if welcome else "home_returning"
    text = t(user.language, key, name=user.name or t(user.language, "traveler_name"))
    keyboard = ui.home_keyboard(user.language, profile_complete=user.birth_date is not None)
    if edit_message_id and await messaging.try_edit(bot, chat_id, edit_message_id, text, keyboard):
        return
    await bot.send_message(chat_id, text, reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create a lightweight profile from Telegram and show value immediately."""
    context.user_data.clear()
    telegram_user = update.effective_user
    chat_id = update.effective_chat.id
    detected_language = normalize_language(getattr(telegram_user, "language_code", None))
    telegram_name = (getattr(telegram_user, "first_name", "") or "").strip()[:64]

    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
        is_new = user is None
        if user is None:
            user = await users.get_or_create_user(
                session,
                chat_id,
                name=telegram_name or t(detected_language, "traveler_name"),
                language=detected_language,
            )
        elif not user.name and telegram_name:
            user = await users.update_user(session, user, {"name": telegram_name})

    await webapp.set_chat_menu_button(context.bot, chat_id, user.language)
    await send_home(context.bot, chat_id, user, welcome=is_new)
    return ConversationHandler.END


async def start_profile_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    async with SessionFactory() as session:
        user = await users.get_or_create_user(
            session,
            chat_id,
            name=(update.effective_user.first_name or "")[:64],
            language=normalize_language(update.effective_user.language_code),
        )
    context.user_data.clear()
    context.user_data.update(
        {"lang": user.language, "registration_message_id": query.message.message_id}
    )
    await _send_decade_picker(update, context, intro=True)
    return BIRTH


async def cancel_profile_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, update.effective_chat.id)
    context.user_data.clear()
    await send_home(
        context.bot,
        user.id,
        user,
        edit_message_id=query.message.message_id,
    )
    return ConversationHandler.END


async def birth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "birth_back:decades":
        await _send_decade_picker(update, context)
    elif data == "birth_back:months":
        await _send_month_picker(update, context)
    elif data.startswith("birth_back:years:"):
        await _send_year_picker(update, context, int(data.rsplit(":", 1)[1]))
    elif data.startswith("birth_decade:"):
        decade = int(data.split(":", 1)[1])
        context.user_data["birth_decade"] = decade
        await _send_year_picker(update, context, decade)
    elif data.startswith("birth_year:"):
        context.user_data["birth_year"] = int(data.split(":", 1)[1])
        await _send_month_picker(update, context)
    elif data.startswith("birth_month:"):
        context.user_data["birth_month"] = int(data.split(":", 1)[1])
        await _send_day_picker(update, context)
    elif data.startswith("birth_day:"):
        birth = date(
            context.user_data["birth_year"],
            context.user_data["birth_month"],
            int(data.split(":", 1)[1]),
        )
        return await _save_birthdate(update, context, birth)
    return BIRTH


async def receive_typed_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    language = _lang(context)
    try:
        birth = datetime.strptime((update.message.text or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text(t(language, "bad_birthdate"))
        return BIRTH
    if birth > date.today():
        await update.message.reply_text(t(language, "bad_birthdate"))
        return BIRTH
    return await _save_birthdate(update, context, birth)


async def _save_birthdate(
    update: Update, context: ContextTypes.DEFAULT_TYPE, birth: date
) -> int:
    chat_id = update.effective_chat.id
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        today = users.local_datetime(user).date()
        user = await users.update_user(
            session,
            user,
            {
                "birth_date": birth,
                "last_daily_notification_date": today,
                "last_life_weekly_date": today,
            },
        )
    message_id = context.user_data.get("registration_message_id")
    context.user_data.clear()
    await send_home(context.bot, chat_id, user, edit_message_id=message_id)
    await context.bot.send_message(
        chat_id,
        t(user.language, "profile_saved", age=users.calculate_age(birth)),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(t(user.language, "settings_button"), callback_data="settings:open")]]
        ),
    )
    return ConversationHandler.END


async def _send_decade_picker(
    update: Update, context: ContextTypes.DEFAULT_TYPE, intro: bool = False
) -> None:
    language = _lang(context)
    now_year = date.today().year
    min_year = now_year - 100
    decades = list(range((min_year // 10) * 10, now_year + 1, 10))
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for start_year in decades:
        end = min(start_year + 9, now_year)
        row.append(
            InlineKeyboardButton(f"{start_year}-{end}", callback_data=f"birth_decade:{start_year}")
        )
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")])
    text = t(language, "ask_birthdate") if intro else birth_picker_text(language, "period")
    await _edit_registration(update, context, text, InlineKeyboardMarkup(keyboard))


async def _send_year_picker(
    update: Update, context: ContextTypes.DEFAULT_TYPE, decade: int
) -> None:
    language = _lang(context)
    now_year = date.today().year
    min_year = now_year - 100
    years = [y for y in range(decade, min(decade + 10, now_year + 1)) if min_year <= y <= now_year]
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for year in years:
        row.append(InlineKeyboardButton(str(year), callback_data=f"birth_year:{year}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(
        [InlineKeyboardButton(t(language, "birth_back"), callback_data="birth_back:decades")]
    )
    await _edit_registration(
        update, context, birth_picker_text(language, "year"), InlineKeyboardMarkup(keyboard)
    )


async def _send_month_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    language = _lang(context)
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for index, label in enumerate(month_labels(language), start=1):
        row.append(InlineKeyboardButton(label, callback_data=f"birth_month:{index}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    decade = context.user_data.get(
        "birth_decade", context.user_data.get("birth_year", 2000) // 10 * 10
    )
    keyboard.append(
        [
            InlineKeyboardButton(
                t(language, "birth_back_years"), callback_data=f"birth_back:years:{decade}"
            )
        ]
    )
    await _edit_registration(
        update, context, birth_picker_text(language, "month"), InlineKeyboardMarkup(keyboard)
    )


async def _send_day_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    language = _lang(context)
    year = context.user_data["birth_year"]
    month = context.user_data["birth_month"]
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        row.append(InlineKeyboardButton(str(day), callback_data=f"birth_day:{day}"))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(
        [InlineKeyboardButton(t(language, "birth_back_months"), callback_data="birth_back:months")]
    )
    await _edit_registration(
        update, context, birth_picker_text(language, "day"), InlineKeyboardMarkup(keyboard)
    )


async def _edit_registration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chat_id = update.effective_chat.id
    message_id = context.user_data.get("registration_message_id")
    if message_id and await messaging.try_edit(
        context.bot, chat_id, message_id, text, reply_markup
    ):
        return
    message = await context.bot.send_message(chat_id, text, reply_markup=reply_markup)
    context.user_data["registration_message_id"] = message.message_id


def build_onboarding_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(start_profile_setup, pattern=r"^profile:setup$"),
        ],
        states={
            BIRTH: [
                CallbackQueryHandler(cancel_profile_setup, pattern=r"^menu:home$"),
                CallbackQueryHandler(birth_callback, pattern=r"^birth_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_typed_birthdate),
            ]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
