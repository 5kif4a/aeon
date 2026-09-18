"""Scheduled bot jobs: local-time morning and evening messages, weekly life reviews.

Two slots a day at most: a thought in the morning (`reminder_hour`) and a question in the
evening (`evening_hour`), each in the user's own zone. Nothing daily goes to a user whose zone
is only the platform default; the auto-decay in `users` mutes slots nobody reacts to.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.error import Forbidden
from telegram.ext import ContextTypes

from app.agents import AGENTS, agent_name
from app.bot import webapp
from app.core.config import get_settings
from app.db.models import Goal, User
from app.db.session import SessionFactory
from app.i18n import life_weekly_content, notification_agent_id, t
from app.notification_texts import evening_question, morning_content
from app.services import billing, conversations, events, followups, ops, users

# Billing reminders are sent only inside the user's local daytime window.
BILLING_REMINDER_HOURS = range(9, 22)

logger = logging.getLogger(__name__)


def reminder_today(now: datetime | None = None, tz_name: str | None = None) -> date:
    configured_tz = tz_name or get_settings().reminder_tz
    try:
        timezone = ZoneInfo(configured_tz)
    except ZoneInfoNotFoundError:
        logger.warning("Invalid REMINDER_TZ %r; falling back to UTC", configured_tz)
        timezone = ZoneInfo("UTC")

    current = now or datetime.now(timezone)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone)
    return current.astimezone(timezone).date()


def life_weeks_lived(birth_date: date, today: date) -> int:
    if birth_date > today:
        return 0
    return max((today - birth_date).days // 7, 0)


def build_life_weekly_message(user: User, today: date) -> str:
    weeks_lived = life_weeks_lived(user.birth_date, today) if user.birth_date else 0
    agent, text = life_weekly_content(user.language, weeks_lived)
    return t(
        user.language,
        "life_weekly",
        weeksLived=weeks_lived,
        agent=agent,
        text=text,
    )


def _calendar_keyboard(language: str) -> InlineKeyboardMarkup | None:
    """One action under the weekly review: open the life calendar in the Mini App."""
    url = webapp.build_webapp_url("calendar", tab="life")
    if not url:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(language, "life_weekly_button"), web_app=WebAppInfo(url=url))]]
    )


async def _send_failed(session, user: User, error: Exception, *, job: str) -> None:
    """A Forbidden means the user blocked the bot: remember it instead of retrying daily."""
    if isinstance(error, Forbidden):
        await users.mark_blocked(session, user, source=job)
        return
    logger.warning("%s notification failed for %s: %s", job, user.id, error)


async def send_life_weekly_reviews(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        candidates = await users.life_weekly_notification_candidates(session)
        for user in candidates:
            if not users.notification_is_due(user, now):
                continue
            today = users.local_datetime(user, now).date()
            if user.last_life_weekly_date and user.last_life_weekly_date > today - timedelta(
                days=7
            ):
                continue
            try:
                await context.bot.send_message(
                    user.id,
                    build_life_weekly_message(user, today),
                    reply_markup=_calendar_keyboard(user.language),
                )
            except Exception as error:
                await _send_failed(session, user, error, job="weekly")
                continue
            await users.mark_life_weekly_sent(session, user, today)


def build_daily_notification(user: User, goal: Goal | None, today: date) -> str:
    """Morning message: a signed advisor line or an unsigned aphorism, then the goal."""
    text, author = morning_content(user.language, users.notification_sequence(user, today))
    if author:
        quote = t(user.language, "morning_signed_quote", text=text, agent=author)
    else:
        quote = t(user.language, "morning_plain_quote", text=text)
    if goal is not None:
        return t(user.language, "morning_with_goal", quote=quote, goal=goal.text)
    return t(user.language, "morning_without_goal", quote=quote)


def _daily_keyboard(language: str, has_goal: bool) -> InlineKeyboardMarkup:
    """Mark the day done, open the calendar (goal tab when there is one), or mute mornings.

    The mute sits on the message itself: nobody walks to /settings to quiet a bot, they block
    it. One tap here keeps the evening question alive.
    """
    url = webapp.build_webapp_url("calendar", tab="goal" if has_goal else "life")
    rows = [[InlineKeyboardButton(t(language, "daily_done_button"), callback_data="daily:done")]]
    if url:
        rows.append(
            [InlineKeyboardButton(t(language, "life_weekly_button"), web_app=WebAppInfo(url=url))]
        )
    rows.append(
        [
            InlineKeyboardButton(
                t(language, "morning_mute_button"), callback_data="notify:morning_off"
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


async def send_daily_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(UTC)
    sent = blocked = 0
    async with SessionFactory() as session:
        candidates = await users.daily_notification_candidates(session)
        for user, goal in candidates:
            if not users.notification_is_due(user, now):
                continue
            today = users.local_datetime(user, now).date()
            if user.last_daily_notification_date == today or user.last_life_weekly_date == today:
                continue
            try:
                await context.bot.send_message(
                    user.id,
                    build_daily_notification(user, goal, today),
                    reply_markup=_daily_keyboard(user.language, goal is not None),
                )
            except Exception as error:
                blocked += isinstance(error, Forbidden)
                await _send_failed(session, user, error, job="morning")
                continue
            sent += 1
            events.record(session, events.NOTIFICATION_SENT, user.id, kind="morning")
            await users.mark_daily_notification_sent(session, user, goal, today)
    ops.blocked_wave("morning", sent=sent, blocked=blocked)


def evening_agent_id(user: User, today: date) -> str:
    """The advisor who asks tonight: the current one, or the rotation when there is none."""
    if user.active_agent in AGENTS:
        return user.active_agent
    return notification_agent_id(users.notification_sequence(user, today))


def build_evening_message(user: User, agent_id: str, question: str) -> str:
    """The question (or follow-up recap) signed by the advisor who asks it."""
    return t(
        user.language,
        "evening_question",
        question=question,
        agent=agent_name(agent_id, user.language),
    )


def build_evening_question(user: User, today: date, agent_id: str) -> str:
    question = evening_question(user.language, users.notification_sequence(user, today))
    return build_evening_message(user, agent_id, question)


async def _send_evening(context, session, user: User, today: date, now: datetime) -> bool:
    """One evening message: a pending follow-up if there is one, else the rotation question.

    Whatever is sent is stored as the advisor's turn in the conversation the reply will land
    in, so the answer (often a single word) reaches the advisor with its question attached.
    """
    followup = await followups.pending_for_user(session, user.id)
    if followup is not None:
        agent_id = followup.agent_id
        question = followup.summary
    else:
        agent_id = evening_agent_id(user, today)
        question = evening_question(user.language, users.notification_sequence(user, today))

    try:
        await context.bot.send_message(user.id, build_evening_message(user, agent_id, question))
    except Exception as error:
        await _send_failed(session, user, error, job="evening")
        return False

    if followup is not None:
        await conversations.reopen_session(session, followup)
        conversation = followup
        await followups.mark_sent(session, conversation, now)
    else:
        conversation = await conversations.start_session(session, user.id, agent_id)
    user.active_agent = agent_id
    # Stored unsigned: in the history it is simply the advisor's own turn.
    await conversations.append_agent_message(session, conversation, question)
    events.record(
        session,
        events.NOTIFICATION_SENT,
        user.id,
        kind="followup" if followup is not None else "evening",
        agent_id=agent_id,
    )
    await users.mark_evening_notification_sent(session, user, today)
    return True


async def send_evening_questions(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        candidates = await users.evening_notification_candidates(session)
        for user in candidates:
            if not users.evening_notification_is_due(user, now):
                continue
            today = users.local_datetime(user, now).date()
            if user.last_evening_notification_date == today:
                continue
            await _send_evening(context, session, user, today, now)


async def generate_conversation_followups(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recaps for dialogues that went quiet; the evening job delivers them."""
    try:
        await followups.generate_pending()
    except Exception as error:
        logger.warning("Follow-up generation failed: %s", error)


def build_billing_reminder(user: User, reminder: billing.BillingReminder) -> str:
    return t(
        user.language,
        f"billing_{reminder}",
        price=get_settings().pro_price_stars,
    )


def _billing_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    t(language, "upgrade_pro_button"), callback_data="billing:subscribe"
                )
            ],
            [InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")],
        ]
    )


def billing_reminder_is_due(user: User, now: datetime) -> bool:
    return users.local_datetime(user, now).hour in BILLING_REMINDER_HOURS


async def send_billing_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stars upsell: trial ends tomorrow, trial ended, Pro expired without renewal."""
    now = datetime.now(UTC)
    async with SessionFactory() as session:
        candidates = await billing.billing_reminder_candidates(session, now)
        for user in candidates:
            reminder = billing.pending_billing_reminder(user, now)
            if reminder is None or not billing_reminder_is_due(user, now):
                continue
            try:
                await context.bot.send_message(
                    user.id,
                    build_billing_reminder(user, reminder),
                    reply_markup=_billing_keyboard(user.language),
                )
            except Exception as error:
                await _send_failed(session, user, error, job=f"billing:{reminder}")
                continue
            await billing.mark_billing_reminder_sent(session, user, reminder, now)
