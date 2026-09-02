"""Agent dialogue inside the bot chat: streaming answers edited into one message."""

import logging
import time

from telegram import Bot

from app.agents import AGENTS, agent_intro, agent_name
from app.bot import messaging, ui
from app.clients.gemini import GeminiError
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.i18n import t
from app.services import agent_chat, billing, conversations, diary, goals, users

logger = logging.getLogger(__name__)


async def set_active_agent(bot: Bot, chat_id: int, agent_id: str, announce: bool = True) -> bool:
    if agent_id not in AGENTS:
        return False
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        await conversations.start_session(session, chat_id, agent_id)
        await users.update_user(session, user, {"active_agent": agent_id})
        language = user.language
    if announce:
        await bot.send_message(chat_id, build_agent_intro(agent_id, language))
    return True


async def clear_active_agent(bot: Bot, chat_id: int, announce: bool = True) -> str:
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        await conversations.close_active_session(session, chat_id)
        await users.update_user(session, user, {"active_agent": None})
        language = user.language
    if announce:
        await bot.send_message(chat_id, t(language, "agent_mode_closed"))
    return language


def build_agent_intro(agent_id: str, language: str) -> str:
    return f"{agent_intro(agent_id, language)}\n\n{t(language, 'agent_intro_suffix')}"


async def process_agent_message(bot: Bot, chat_id: int, text: str) -> bool:
    """Answer a chat message with the active agent. Returns False if no agent is active."""
    settings = get_settings()
    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
        agent_id = user.active_agent if user else None
        if not agent_id:
            return False
        if agent_id not in AGENTS:
            await users.update_user(session, user, {"active_agent": None})
            return False
        language = user.language
        active_goal = await goals.get_active_goal(session, chat_id)
        diary_entries = await diary.list_entries(session, chat_id, limit=3)
        if not settings.gemini_api_key:
            await bot.send_message(chat_id, t(language, "gemini_not_configured"))
            return True
        try:
            grant = await billing.reserve_agent_question(session, chat_id)
        except billing.AccessLimitExceeded as error:
            await bot.send_message(
                chat_id,
                t(language, f"question_limit_{error.plan.lower()}"),
                reply_markup=ui.limit_keyboard(language, error.plan),
            )
            return True
        user.plan = grant.generation_plan

    await bot.send_chat_action(chat_id, "typing")
    history = await agent_chat.get_history(chat_id, agent_id)
    if grant.mode == "prompt":
        history = history[-4:]
    progress = await bot.send_message(
        chat_id, t(language, "agent_thinking", name=agent_name(agent_id, language))
    )
    on_text = _create_stream_editor(bot, chat_id, progress.message_id, language)

    generation_args = dict(
        agent_id=agent_id,
        message=text,
        user=user,
        history=history,
        language=language,
        diary=[entry.text for entry in diary_entries if grant.mode == "rag"]
        or [entry.text for entry in diary_entries[:1]],
        active_goal=active_goal.text if active_goal else "",
    )

    try:
        answer = await agent_chat.generate_answer_stream(on_text=on_text, **generation_args)
    except Exception as error:
        logger.warning("Agent dialogue error: %s", error)
        if _should_try_non_stream_fallback(error):
            try:
                await messaging.send_or_edit(
                    bot, chat_id, progress.message_id, t(language, "stream_fallback")
                )
                answer = await agent_chat.generate_answer(**generation_args)
            except Exception as fallback_error:
                logger.warning("Agent dialogue fallback error: %s", fallback_error)
                await messaging.send_or_edit(
                    bot,
                    chat_id,
                    progress.message_id,
                    _build_error_message(fallback_error, language),
                )
                async with SessionFactory() as session:
                    await billing.release_agent_question(session, chat_id, grant)
                return True
        else:
            await messaging.send_or_edit(
                bot, chat_id, progress.message_id, _build_error_message(error, language)
            )
            async with SessionFactory() as session:
                await billing.release_agent_question(session, chat_id, grant)
            return True

    await agent_chat.append_history(chat_id, agent_id, text, answer)
    await messaging.send_or_edit(
        bot,
        chat_id,
        progress.message_id,
        answer,
        reply_markup=ui.post_answer_keyboard(language),
    )
    return True


async def process_council_message(bot: Bot, chat_id: int, text: str) -> bool:
    settings = get_settings()
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        language = user.language
        if not settings.gemini_api_key:
            await bot.send_message(chat_id, t(language, "gemini_not_configured"))
            return False
        try:
            grant = await billing.reserve_council(session, chat_id)
        except billing.CouncilUnavailable as error:
            await bot.send_message(
                chat_id,
                t(language, f"council_limit_{error.plan.lower()}"),
                reply_markup=ui.limit_keyboard(language, error.plan),
            )
            return False
        user.plan = grant.plan
        active_goal = await goals.get_active_goal(session, chat_id)
        diary_entries = await diary.list_entries(session, chat_id, limit=3)

    progress = await bot.send_message(chat_id, t(language, "council_thinking"))
    try:
        answer = await agent_chat.generate_council_answer(
            text,
            user,
            language,
            diary=[entry.text for entry in diary_entries],
            active_goal=active_goal.text if active_goal else "",
        )
    except Exception as error:
        logger.warning("Council generation error: %s", error)
        async with SessionFactory() as session:
            await billing.release_council(session, chat_id, grant)
        await messaging.send_or_edit(
            bot, chat_id, progress.message_id, _build_error_message(error, language)
        )
        return False

    await agent_chat.store_completed_session(chat_id, "council", text, answer)
    await messaging.send_or_edit(
        bot,
        chat_id,
        progress.message_id,
        answer,
        reply_markup=ui.post_answer_keyboard(language),
    )
    return True


def _create_stream_editor(bot: Bot, chat_id: int, message_id: int, language: str):
    state = {"last_text": "", "last_edit_at": 0.0}
    continue_suffix = f"\n\n{t(language, 'agent_continue')}"

    async def update(text: str) -> None:
        preview = agent_chat.sanitize_answer(text)
        if not preview:
            return
        if len(preview) > messaging.TELEGRAM_MESSAGE_LIMIT:
            preview = preview[: messaging.TELEGRAM_MESSAGE_LIMIT - 24].rstrip() + continue_suffix

        now = time.monotonic()
        is_first_text = not state["last_text"]
        has_meaningful_change = len(preview) - len(state["last_text"]) >= 30
        enough_time_passed = now - state["last_edit_at"] >= 0.25
        if not is_first_text and not (has_meaningful_change and enough_time_passed):
            return

        if await messaging.try_edit(bot, chat_id, message_id, preview):
            state["last_text"] = preview
            state["last_edit_at"] = now

    return update


def _should_try_non_stream_fallback(error: Exception) -> bool:
    if isinstance(error, GeminiError) and error.status in (401, 403, 404, 429):
        return False
    return True


def _build_error_message(error: Exception, language: str) -> str:
    settings = get_settings()
    message = str(error)
    status = error.status if isinstance(error, GeminiError) else None
    if status == 429:
        return t(language, "error_rate_limit")
    if status == 503:
        return t(language, "error_overloaded")
    if status == 404:
        return t(language, "error_model_unavailable", model=settings.gemini_model)
    if status in (401, 403):
        return t(language, "error_key_rejected")
    if "timed out" in message.lower() or "timeout" in message.lower():
        return t(language, "error_network")
    if "empty answer" in message:
        return t(language, "error_empty")
    return t(language, "error_generic")
