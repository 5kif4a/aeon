"""Agent picker, dialog menu, /stop and free-form agent chat messages."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from app.agents import AGENTS, agent_button
from app.bot import chat, webapp
from app.db.session import SessionFactory
from app.i18n import t
from app.services import users


async def _user_language(chat_id: int) -> str:
    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
    return user.language if user else "en"


async def agents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_agent_picker(update.effective_chat.id, context)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    language = await _user_language(chat_id)
    await webapp.set_chat_menu_button(context.bot, chat_id)
    keyboard = [
        [InlineKeyboardButton(t(language, "pick_agent_button"), callback_data="agent:picker")]
    ]
    url = webapp.build_webapp_url()
    if url:
        keyboard.append(
            [InlineKeyboardButton(t(language, "open_mini_app"), web_app=WebAppInfo(url=url))]
        )
    await context.bot.send_message(
        chat_id, t(language, "dialog_menu_title"), reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await chat.clear_active_agent(context.bot, update.effective_chat.id)


async def agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    agent_id = query.data.split(":", 1)[1]
    chat_id = update.effective_chat.id
    if agent_id == "picker" or agent_id not in AGENTS:
        await _send_agent_picker(chat_id, context)
        return
    await chat.set_active_agent(context.bot, chat_id, agent_id)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    if not text:
        return
    if await chat.process_agent_message(context.bot, chat_id, text):
        return
    await context.bot.send_message(chat_id, t(await _user_language(chat_id), "unknown"))


async def _send_agent_picker(chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    language = await _user_language(chat_id)
    await webapp.set_chat_menu_button(context.bot, chat_id)
    keyboard = [
        [InlineKeyboardButton(agent_button(agent_id, language), callback_data=f"agent:{agent_id}")]
        for agent_id in AGENTS
    ]
    url = webapp.build_webapp_url()
    if url:
        keyboard.append(
            [InlineKeyboardButton(t(language, "open_mini_app"), web_app=WebAppInfo(url=url))]
        )
    await context.bot.send_message(
        chat_id, t(language, "choose_agent"), reply_markup=InlineKeyboardMarkup(keyboard)
    )


def build_command_handlers() -> list:
    return [
        CommandHandler(["agents", "agent"], agents_command),
        CommandHandler(["app", "menu"], menu_command),
        CommandHandler(["stop", "reset_agent"], stop_command),
        CallbackQueryHandler(agent_callback, pattern=r"^agent:"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message),
    ]
