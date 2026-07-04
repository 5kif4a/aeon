"""Scheduled bot jobs: daily goal reminders."""

import logging
from datetime import date

from telegram.ext import ContextTypes

from app.db.session import SessionFactory
from app.i18n import t
from app.services import goals

logger = logging.getLogger(__name__)


async def remind_due_goals(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = date.today()
    async with SessionFactory() as session:
        due_goals = await goals.goals_due_for_reminder(session, today)
        for goal in due_goals:
            lang = goal.user.language if goal.user else "en"
            try:
                await context.bot.send_message(goal.user_id, t(lang, "reminder", goal=goal.text))
            except Exception as error:
                logger.warning("Goal reminder failed for %s: %s", goal.user_id, error)
                continue
            await goals.mark_reminded(session, goal, today)
