"""Registration flow: language -> name -> staged birth date picker -> country.

The whole flow edits a single Telegram message instead of flooding the chat.
"""

import calendar
from datetime import date, datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.bot import messaging, webapp
from app.db.session import SessionFactory
from app.i18n import (
    CHOOSE_LANGUAGE,
    COUNTRIES,
    DEFAULT_LANGUAGE,
    LANGUAGE_NAMES,
    birth_picker_text,
    country_label,
    month_labels,
    normalize_language,
    t,
)
from app.services import users

LANGUAGE, NAME, BIRTH, COUNTRY = range(4)


def _lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", DEFAULT_LANGUAGE)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"lang:{code}")]
        for code, label in LANGUAGE_NAMES.items()
    ]
    message = await update.effective_chat.send_message(
        CHOOSE_LANGUAGE, reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data["registration_message_id"] = message.message_id
    return LANGUAGE


async def choose_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = normalize_language(query.data.split(":", 1)[1])
    context.user_data["lang"] = lang
    context.user_data["registration_message_id"] = query.message.message_id
    await _edit_registration(update, context, t(lang, "intro"))
    return NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    context.user_data["name"] = text[:48] if text else "Traveler"
    await _send_decade_picker(update, context, intro=True)
    return BIRTH


async def birth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "birth_back:decades":
        await _send_decade_picker(update, context)
        return BIRTH

    if data.startswith("birth_decade:"):
        await _send_year_picker(update, context, int(data.split(":", 1)[1]))
        return BIRTH

    if data.startswith("birth_year:"):
        context.user_data["birth_year"] = int(data.split(":", 1)[1])
        await _send_month_picker(update, context)
        return BIRTH

    if data.startswith("birth_month:"):
        context.user_data["birth_month"] = int(data.split(":", 1)[1])
        await _send_day_picker(update, context)
        return BIRTH

    if data.startswith("birth_day:"):
        day = int(data.split(":", 1)[1])
        birth = date(context.user_data["birth_year"], context.user_data["birth_month"], day)
        context.user_data["birth_date"] = birth
        await _send_country_picker(update, context)
        return COUNTRY

    return BIRTH


async def receive_typed_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = _lang(context)
    text = (update.message.text or "").strip()
    try:
        birth = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        await update.message.reply_text(t(lang, "bad_birthdate"))
        return BIRTH
    if birth > date.today():
        await update.message.reply_text(t(lang, "bad_birthdate"))
        return BIRTH
    context.user_data["birth_date"] = birth
    await _send_country_picker(update, context)
    return COUNTRY


async def choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = _lang(context)
    code = query.data.split(":", 1)[1]
    country = country_label(code, lang)
    birth: date = context.user_data["birth_date"]
    name = context.user_data.get("name", "Traveler")

    chat_id = update.effective_chat.id
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        await users.update_user(
            session,
            user,
            {"language": lang, "name": name, "birth_date": birth, "country": country},
        )

    age = users.calculate_age(birth)
    text = t(lang, "done", name=name, age=age, birthDate=birth.isoformat(), country=country)
    url = webapp.build_webapp_url()
    keyboard = None
    if url:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(t(lang, "open_mini_app"), web_app=WebAppInfo(url=url))]]
        )
    await _edit_registration(update, context, text, keyboard)
    await webapp.set_chat_menu_button(context.bot, chat_id)
    context.user_data.clear()
    return ConversationHandler.END


# --- pickers ------------------------------------------------------------------


async def _send_decade_picker(
    update: Update, context: ContextTypes.DEFAULT_TYPE, intro: bool = False
) -> None:
    lang = _lang(context)
    now_year = date.today().year
    min_year = now_year - 100
    decades = list(range((min_year // 10) * 10, now_year + 1, 10))

    keyboard, row = [], []
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

    text = t(lang, "ask_birthdate") if intro else birth_picker_text(lang, "period")
    await _edit_registration(update, context, text, InlineKeyboardMarkup(keyboard))


async def _send_year_picker(
    update: Update, context: ContextTypes.DEFAULT_TYPE, decade: int
) -> None:
    lang = _lang(context)
    now_year = date.today().year
    min_year = now_year - 100
    years = [y for y in range(decade, min(decade + 10, now_year + 1)) if min_year <= y <= now_year]

    keyboard, row = [], []
    for year in years:
        row.append(InlineKeyboardButton(str(year), callback_data=f"birth_year:{year}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(
        [InlineKeyboardButton(t(lang, "birth_back"), callback_data="birth_back:decades")]
    )
    await _edit_registration(
        update, context, birth_picker_text(lang, "year"), InlineKeyboardMarkup(keyboard)
    )


async def _send_month_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context)
    keyboard, row = [], []
    for index, label in enumerate(month_labels(lang), start=1):
        row.append(InlineKeyboardButton(label, callback_data=f"birth_month:{index}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    await _edit_registration(
        update, context, birth_picker_text(lang, "month"), InlineKeyboardMarkup(keyboard)
    )


async def _send_day_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context)
    year = context.user_data["birth_year"]
    month = context.user_data["birth_month"]
    days_in_month = calendar.monthrange(year, month)[1]

    keyboard, row = [], []
    for day in range(1, days_in_month + 1):
        row.append(InlineKeyboardButton(str(day), callback_data=f"birth_day:{day}"))
        if len(row) == 7:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    await _edit_registration(
        update, context, birth_picker_text(lang, "day"), InlineKeyboardMarkup(keyboard)
    )


async def _send_country_picker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = _lang(context)
    name = context.user_data.get("name", "Traveler")
    keyboard = [
        [InlineKeyboardButton(country_label(code, lang), callback_data=f"country:{code}")]
        for code, _ in COUNTRIES
    ]
    await _edit_registration(
        update, context, t(lang, "ask_country", name=name), InlineKeyboardMarkup(keyboard)
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
        entry_points=[CommandHandler("start", start)],
        states={
            LANGUAGE: [CallbackQueryHandler(choose_language, pattern=r"^lang:")],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            BIRTH: [
                CallbackQueryHandler(birth_callback, pattern=r"^birth_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_typed_birthdate),
            ],
            COUNTRY: [CallbackQueryHandler(choose_country, pattern=r"^country:")],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
