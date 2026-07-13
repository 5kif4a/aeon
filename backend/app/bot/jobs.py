"""Scheduled bot jobs: daily agent notifications and weekly life reviews."""

import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

from app.bot import webapp
from app.core.config import get_settings
from app.db.models import Goal, User
from app.db.session import SessionFactory
from app.i18n import daily_notification_content, life_weekly_content, t
from app.services import users

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
    url = webapp.build_webapp_url("calendar")
    if not url:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(language, "life_weekly_button"), web_app=WebAppInfo(url=url))]]
    )


async def send_life_weekly_reviews(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = reminder_today()
    async with SessionFactory() as session:
        due_users = await users.users_due_for_life_weekly(session, today)
        for user in due_users:
            try:
                await context.bot.send_message(
                    user.id,
                    build_life_weekly_message(user, today),
                    reply_markup=_calendar_keyboard(user.language),
                )
            except Exception as error:
                logger.warning("Life weekly notification failed for %s: %s", user.id, error)
                continue
            await users.mark_life_weekly_sent(session, user, today)


def build_daily_notification(user: User, goal: Goal | None, today: date) -> str:
    sequence = max((today - user.birth_date).days, 0) if user.birth_date else 0
    agent, text = daily_notification_content(user.language, sequence)
    if goal is not None:
        return t(
            user.language,
            "daily_with_goal",
            agent=agent,
            goal=goal.text,
            text=text,
        )
    return t(
        user.language,
        "daily_without_goal",
        agent=agent,
        text=text,
    )


def _daily_keyboard(language: str, has_goal: bool) -> InlineKeyboardMarkup | None:
    url = webapp.build_webapp_url("calendar")
    if not url:
        return None
    key = "daily_goal_button" if has_goal else "daily_calendar_button"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(language, key), web_app=WebAppInfo(url=url))]]
    )


async def send_daily_notifications(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = reminder_today()
    async with SessionFactory() as session:
        due_users = await users.users_due_for_daily_notification(session, today)
        for user, goal in due_users:
            try:
                await context.bot.send_message(
                    user.id,
                    build_daily_notification(user, goal, today),
                    reply_markup=_daily_keyboard(user.language, goal is not None),
                )
            except Exception as error:
                logger.warning("Daily notification failed for %s: %s", user.id, error)
                continue
            await users.mark_daily_notification_sent(session, user, goal, today)
