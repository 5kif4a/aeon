"""Agent dialogue inside the bot chat: streaming answers edited into one message."""

import asyncio
import logging
import time
import uuid
from collections import defaultdict

from telegram import Bot

from app.agents import AGENTS, PROMPT_MODE_HISTORY_LIMIT, agent_intro, agent_name
from app.bot import messaging, ui
from app.clients.gemini import GeminiError
from app.core.config import get_settings
from app.db.session import SessionFactory
from app.i18n import t
from app.services import agent_chat, billing, conversations, diary, events, goals, ops, users

logger = logging.getLogger(__name__)

# One generation at a time per chat: a second message while an answer is still
# streaming would double the Gemini spend and interleave message edits.
_generation_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


async def _reject_if_generating(bot: Bot, chat_id: int) -> bool:
    """Tell the user to wait if a generation is already running for this chat."""
    if not _generation_locks[chat_id].locked():
        return False
    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
    language = user.language if user else "en"
    await bot.send_message(chat_id, t(language, "generation_in_progress"))
    return True


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
    if await _reject_if_generating(bot, chat_id):
        return True
    async with _generation_locks[chat_id]:
        return await _process_agent_message(bot, chat_id, text)


async def _process_agent_message(bot: Bot, chat_id: int, text: str) -> bool:
    settings = get_settings()
    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
        agent_id = user.active_agent if user else None
        if not agent_id:
            return False
        if agent_id not in AGENTS:
            await users.update_user(session, user, {"active_agent": None})
            return False
        await users.mark_reaction(session, user)
        language = user.language
        offer_app = user.last_webapp_open_at is None
        active_goal = await goals.get_active_goal(session, chat_id)
        diary_entries = await diary.list_entries(session, chat_id, limit=3)
        if not settings.gemini_api_key:
            await bot.send_message(chat_id, t(language, "gemini_not_configured"))
            return True
        try:
            grant = await billing.reserve_agent_question(session, chat_id)
        except billing.AccessLimitExceeded as error:
            events.record(
                session, events.QUESTION_LIMIT_HIT, chat_id, kind="agent", plan=error.plan
            )
            await session.commit()
            if error.plan == "Free" and user.first_answer_at is None:
                # The failure mode that killed the previous product: a paywall before any
                # answer. One alert per 10 minutes is enough to notice the same day.
                ops.limit_without_answer(user)
            can_start_trial = billing.trial_available(user, error.plan)
            if error.plan == "Free" and can_start_trial:
                # The limit is the moment the Trial is offered: say plainly that the free
                # questions come back tomorrow and that the Trial opens everything right now.
                text = t(language, "question_limit_free_trial", days=settings.trial_days)
            else:
                text = t(language, f"question_limit_{error.plan.lower()}")
            await bot.send_message(
                chat_id,
                text,
                reply_markup=ui.limit_keyboard(
                    language, error.plan, can_start_trial=can_start_trial
                ),
            )
            return True
        user.plan = grant.generation_plan

    await bot.send_chat_action(chat_id, "typing")
    history = await agent_chat.get_history(chat_id, agent_id)
    if grant.mode == "prompt":
        history = history[-PROMPT_MODE_HISTORY_LIMIT:]
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
                    await _record_generation_failure(session, chat_id, "agent", fallback_error)
                ops.generation_failed(
                    "agent", user, fallback_error, agent_id=agent_id, mode=grant.mode
                )
                return True
        else:
            await messaging.send_or_edit(
                bot, chat_id, progress.message_id, _build_error_message(error, language)
            )
            async with SessionFactory() as session:
                await billing.release_agent_question(session, chat_id, grant)
                await _record_generation_failure(session, chat_id, "agent", error)
            ops.generation_failed("agent", user, error, agent_id=agent_id, mode=grant.mode)
            return True

    await agent_chat.append_history(chat_id, agent_id, text, answer)
    await _mark_first_answer(chat_id, agent_id, grant.mode)
    footer = await _checkin_footer(chat_id, language)
    await messaging.send_or_edit(
        bot,
        chat_id,
        progress.message_id,
        f"{answer}\n\n{footer}" if footer else answer,
        reply_markup=ui.post_answer_keyboard(language, offer_app=offer_app),
        markdown=True,
    )
    return True


async def _mark_first_answer(chat_id: int, agent_id: str, mode: str) -> None:
    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
        if user is not None:
            await users.mark_first_answer(session, user, agent_id=agent_id, mode=mode)


async def _checkin_footer(chat_id: int, language: str) -> str:
    """Writing to an advisor is the day's check-in. The first message of a local day advances
    the streak; from the second day on, one line under the answer says so. It is not the
    advisor speaking, hence the separate line and the marker."""
    async with SessionFactory() as session:
        user = await users.get_user(session, chat_id)
        if user is None:
            return ""
        before = user.last_daily_checkin_date
        streak = await users.record_daily_checkin(session, user)
        if user.last_daily_checkin_date == before:
            return ""
        events.record(session, events.CHECKIN_RECORDED, chat_id, source="message", streak=streak)
        await session.commit()
    return t(language, "streak_footer", streak=streak) if streak >= 2 else ""


async def process_council_message(bot: Bot, chat_id: int, text: str) -> bool:
    """Backward-compatible alias for old Mini App builds and the /council command."""
    return await process_discussion_message(bot, chat_id, text)


async def process_discussion_message(bot: Bot, chat_id: int, text: str) -> bool:
    if await _reject_if_generating(bot, chat_id):
        return False
    async with _generation_locks[chat_id]:
        return await _process_discussion_message(bot, chat_id, text)


async def _process_discussion_message(bot: Bot, chat_id: int, text: str) -> bool:
    settings = get_settings()
    grant: billing.CouncilGrant | None = None
    limit_error: billing.CouncilUnavailable | None = None
    can_start_trial = False
    active_goal = None
    diary_entries = []
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        language = user.language
        if settings.gemini_api_key:
            try:
                grant = await billing.reserve_council(session, chat_id)
            except billing.CouncilUnavailable as error:
                limit_error = error
                can_start_trial = billing.trial_available(user, error.plan)
                events.record(
                    session, events.QUESTION_LIMIT_HIT, chat_id, kind="discussion", plan=error.plan
                )
                await session.commit()
            else:
                user.plan = grant.plan
                active_goal = await goals.get_active_goal(session, chat_id)
                diary_entries = await diary.list_entries(session, chat_id, limit=3)

    if not settings.gemini_api_key:
        await bot.send_message(chat_id, t(language, "gemini_not_configured"))
        return False
    if limit_error is not None:
        await bot.send_message(
            chat_id,
            t(language, f"council_limit_{limit_error.plan.lower()}"),
            reply_markup=ui.limit_keyboard(
                language,
                limit_error.plan,
                can_start_trial=can_start_trial,
            ),
        )
        return False
    assert grant is not None

    progress = await bot.send_message(chat_id, t(language, "discussion_thinking"))
    try:
        result = await agent_chat.generate_discussion_round(
            text,
            user,
            language,
            diary=[entry.text for entry in diary_entries],
            active_goal=active_goal.text if active_goal else "",
        )
    except Exception as error:
        logger.warning("Discussion generation error: %s", error)
        async with SessionFactory() as session:
            await billing.release_council(session, chat_id, grant)
            await _record_generation_failure(session, chat_id, "discussion", error)
        ops.generation_failed("discussion", user, error, mode="council")
        await messaging.send_or_edit(
            bot, chat_id, progress.message_id, _build_error_message(error, language)
        )
        return False

    transcript = agent_chat.discussion_transcript(result.turns, language)
    async with SessionFactory() as session:
        conversation = await conversations.append_completed_session(
            session,
            chat_id,
            "council",
            text,
            transcript,
            summary=result.summary,
        )
        conversation_id = conversation.id
    await _send_discussion_round(
        bot, chat_id, language, result, conversation_id, progress.message_id
    )
    return True


async def continue_discussion(bot: Bot, chat_id: int, conversation_id: str) -> bool:
    if await _reject_if_generating(bot, chat_id):
        return False
    async with _generation_locks[chat_id]:
        return await _continue_discussion(bot, chat_id, conversation_id)


async def _continue_discussion(bot: Bot, chat_id: int, conversation_id: str) -> bool:
    try:
        parsed_id = uuid.UUID(conversation_id)
    except ValueError:
        return False

    settings = get_settings()
    grant: billing.CouncilGrant | None = None
    limit_error: billing.CouncilUnavailable | None = None
    can_start_trial = False
    active_goal = None
    diary_entries = []
    topic = ""
    previous = ""
    conversation_found = False
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        language = user.language
        conversation = await conversations.get_session_for_user(
            session, parsed_id, chat_id, agent_id="council"
        )
        if conversation is not None:
            conversation_found = True
            history = await conversations.list_session_history(session, parsed_id, limit=20)
            topic = next((item["text"] for item in history if item["role"] == "user"), "")
            previous = "\n\n".join(
                item["text"] for item in history if item["role"] == "agent"
            )
            if settings.gemini_api_key:
                try:
                    grant = await billing.reserve_council(session, chat_id)
                except billing.CouncilUnavailable as error:
                    limit_error = error
                    can_start_trial = billing.trial_available(user, error.plan)
                    events.record(
                        session,
                        events.QUESTION_LIMIT_HIT,
                        chat_id,
                        kind="discussion",
                        plan=error.plan,
                    )
                    await session.commit()
                else:
                    user.plan = grant.plan
                    active_goal = await goals.get_active_goal(session, chat_id)
                    diary_entries = await diary.list_entries(session, chat_id, limit=3)

    if not conversation_found:
        await bot.send_message(chat_id, t(language, "discussion_not_found"))
        return False
    if not settings.gemini_api_key:
        await bot.send_message(chat_id, t(language, "gemini_not_configured"))
        return False
    if limit_error is not None:
        await bot.send_message(
            chat_id,
            t(language, f"council_limit_{limit_error.plan.lower()}"),
            reply_markup=ui.limit_keyboard(
                language,
                limit_error.plan,
                can_start_trial=can_start_trial,
            ),
        )
        return False
    assert grant is not None

    progress = await bot.send_message(chat_id, t(language, "discussion_continuing"))
    try:
        result = await agent_chat.generate_discussion_round(
            topic,
            user,
            language,
            previous_transcript=previous,
            diary=[entry.text for entry in diary_entries],
            active_goal=active_goal.text if active_goal else "",
        )
    except Exception as error:
        logger.warning("Discussion continuation error: %s", error)
        async with SessionFactory() as session:
            await billing.release_council(session, chat_id, grant)
            await _record_generation_failure(session, chat_id, "discussion", error)
        ops.generation_failed("discussion", user, error, mode="council")
        await messaging.send_or_edit(
            bot, chat_id, progress.message_id, _build_error_message(error, language)
        )
        return False

    transcript = agent_chat.discussion_transcript(result.turns, language)
    async with SessionFactory() as session:
        conversation = await conversations.append_closed_agent_turn(
            session,
            parsed_id,
            chat_id,
            transcript,
            summary=result.summary,
        )
        if conversation is None:
            await billing.release_council(session, chat_id, grant)
    if conversation is None:
        await messaging.send_or_edit(
            bot, chat_id, progress.message_id, t(language, "discussion_not_found")
        )
        return False
    await _send_discussion_round(bot, chat_id, language, result, parsed_id, progress.message_id)
    return True


async def send_discussion_summary(bot: Bot, chat_id: int, conversation_id: str) -> bool:
    try:
        parsed_id = uuid.UUID(conversation_id)
    except ValueError:
        return False
    async with SessionFactory() as session:
        user = await users.get_or_create_user(session, chat_id)
        conversation = await conversations.get_session_for_user(
            session, parsed_id, chat_id, agent_id="council"
        )
        language = user.language
    if conversation is None or not conversation.summary.strip():
        await bot.send_message(chat_id, t(language, "discussion_not_found"))
        return False
    await messaging.send_chunked(
        bot,
        chat_id,
        f"**{t(language, 'discussion_summary_title')}**\n\n{conversation.summary}",
        reply_markup=ui.discussion_summary_keyboard(language),
        markdown=True,
    )
    return True


async def _send_discussion_round(
    bot: Bot,
    chat_id: int,
    language: str,
    result: agent_chat.DiscussionResult,
    conversation_id: uuid.UUID,
    progress_message_id: int,
) -> None:
    for index, turn in enumerate(result.turns):
        text = f"**{agent_name(turn.agent_id, language)}**\n\n{turn.text}"
        markup = (
            ui.discussion_keyboard(language, str(conversation_id))
            if index == len(result.turns) - 1
            else None
        )
        if index == 0:
            await messaging.send_or_edit(
                bot,
                chat_id,
                progress_message_id,
                text,
                reply_markup=markup,
                markdown=True,
            )
        else:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(0.6)
            await messaging.send_chunked(
                bot, chat_id, text, reply_markup=markup, markdown=True
            )


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

        if await messaging.try_edit(bot, chat_id, message_id, preview, markdown=True):
            state["last_text"] = preview
            state["last_edit_at"] = now

    return update


async def _record_generation_failure(session, chat_id: int, kind: str, error: Exception) -> None:
    events.record(
        session,
        events.GENERATION_FAILED,
        chat_id,
        kind=kind,
        error=f"{type(error).__name__}: {str(error)[:300]}",
    )
    await session.commit()


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
