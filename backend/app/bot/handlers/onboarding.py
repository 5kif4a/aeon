"""First-run experience: /start, the language step and the first advisor."""

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, filters

from app.agents import AGENTS, agent_name
from app.bot import chat, messaging, ui, webapp
from app.db.models import User
from app.db.session import SessionFactory
from app.i18n import normalize_language, t
from app.services import users


def _greeting(user: User, key: str) -> str:
    name = users.presentable_name(user.name)
    return t(user.language, f"{key}_named", name=name) if name else t(user.language, key)


async def send_home(bot, chat_id: int, user: User, *, edit_message_id: int | None = None) -> None:
    text = _greeting(user, "home_returning")
    if user.active_agent in AGENTS:
        agent = agent_name(user.active_agent, user.language)
        text = f"{text}\n\n{t(user.language, 'home_active_agent', agent=agent)}"
    keyboard = ui.home_keyboard(user.language)
    if edit_message_id and await messaging.try_edit(bot, chat_id, edit_message_id, text, keyboard):
        return
    await bot.send_message(chat_id, text, reply_markup=keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a lightweight profile from Telegram; new users pick a language and an advisor."""
    context.user_data.clear()
    telegram_user = update.effective_user
    chat_id = update.effective_chat.id
    detected_language = normalize_language(getattr(telegram_user, "language_code", None))
    telegram_name = users.presentable_name(getattr(telegram_user, "first_name", ""))

    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
        is_new = user is None
        if user is None:
            user = await users.get_or_create_user(
                session,
                chat_id,
                name=telegram_name,
                language=detected_language,
                username=getattr(telegram_user, "username", "") or "",
            )
        else:
            changes = {}
            if not users.presentable_name(user.name) and telegram_name:
                changes["name"] = telegram_name
            username = (getattr(telegram_user, "username", "") or "")[:64]
            if user.username != username:
                changes["username"] = username
            if changes:
                user = await users.update_user(session, user, changes)

    await webapp.set_chat_menu_button(context.bot, chat_id, user.language)
    if is_new:
        # The client language is only a guess: the first step lets the user confirm it.
        await context.bot.send_message(
            chat_id,
            t(detected_language, "onboarding_choose_language"),
            reply_markup=ui.language_keyboard("onboarding:lang", detected=detected_language),
        )
    else:
        await send_home(context.bot, chat_id, user)


async def onboarding_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    language = normalize_language(query.data.rsplit(":", 1)[1])
    chat_id = update.effective_chat.id
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        user = await users.update_user(session, user, {"language": language})
    await webapp.set_chat_menu_button(context.bot, chat_id, language)
    await messaging.try_edit(
        context.bot,
        chat_id,
        query.message.message_id,
        _greeting(user, "home_welcome"),
        ui.agent_picker_keyboard(language, prefix="onboarding:agent"),
    )


async def onboarding_agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    agent_id = query.data.rsplit(":", 1)[1]
    chat_id = update.effective_chat.id
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
    if agent_id not in AGENTS:
        await messaging.try_edit(
            context.bot,
            chat_id,
            query.message.message_id,
            _greeting(user, "home_welcome"),
            ui.agent_picker_keyboard(user.language, prefix="onboarding:agent"),
        )
        return
    await chat.set_active_agent(context.bot, chat_id, agent_id, announce=False)
    await messaging.try_edit(
        context.bot,
        chat_id,
        query.message.message_id,
        chat.build_agent_intro(agent_id, user.language),
        ui.onboarding_agent_keyboard(user.language),
    )


def build_onboarding_callbacks() -> list[CallbackQueryHandler]:
    # Each step is addressed by its callback prefix, so no in-memory state survives a restart
    # and none is needed.
    return [
        CallbackQueryHandler(onboarding_language_callback, pattern=r"^onboarding:lang:"),
        CallbackQueryHandler(onboarding_agent_callback, pattern=r"^onboarding:agent:"),
    ]


def build_onboarding_handler() -> CommandHandler:
    return CommandHandler("start", start, filters=filters.ChatType.PRIVATE)
