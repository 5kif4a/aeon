from datetime import UTC, date, datetime

from app.bot import webapp
from app.bot.jobs import (
    _calendar_keyboard,
    _daily_keyboard,
    build_daily_notification,
    build_life_weekly_message,
    reminder_today,
)
from app.db.models import Goal, User
from app.i18n import daily_notification_content, life_weekly_content


def test_reminder_today_uses_configured_timezone_date():
    now = datetime(2026, 1, 1, 23, 30, tzinfo=UTC)

    assert reminder_today(now=now, tz_name="Asia/Almaty").isoformat() == "2026-01-02"


def test_reminder_today_falls_back_to_utc_for_invalid_timezone():
    now = datetime(2026, 1, 1, 23, 30, tzinfo=UTC)

    assert reminder_today(now=now, tz_name="Not/AZone").isoformat() == "2026-01-01"


def test_weekly_agents_rotate_and_return_after_three_weeks():
    first_agent, first_text = life_weekly_content("en", 1200)
    second_agent, _ = life_weekly_content("en", 1201)
    third_agent, _ = life_weekly_content("en", 1202)
    repeated_agent, repeated_text = life_weekly_content("en", 1203)

    assert (first_agent, second_agent, third_agent) == (
        "Marcus Aurelius",
        "Niccolo Machiavelli",
        "Carl Jung",
    )
    assert repeated_agent == first_agent
    assert repeated_text != first_text


def test_build_life_weekly_message_uses_russian_localization():
    user = User(id=1, language="ru", birth_date=date(2000, 1, 1))

    message = build_life_weekly_message(user, date(2000, 1, 15))

    assert "Завершилась 2-я неделя Вашей жизни." in message
    assert "Карл Юнг" in message
    assert "Выберите одну цель на новую неделю." in message


def test_calendar_keyboard_opens_calendar(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view: f"https://aeon.test/?view={view}")

    keyboard = _calendar_keyboard("ru")

    assert keyboard is not None
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "Открыть календарь"
    assert button.web_app is not None
    assert button.web_app.url == "https://aeon.test/?view=calendar"


def test_daily_agents_rotate_and_return_after_three_days():
    first_agent, first_text = daily_notification_content("ru", 1200)
    second_agent, _ = daily_notification_content("ru", 1201)
    third_agent, _ = daily_notification_content("ru", 1202)
    repeated_agent, repeated_text = daily_notification_content("ru", 1203)

    assert (first_agent, second_agent, third_agent) == (
        "Марк Аврелий",
        "Никколо Макиавелли",
        "Карл Юнг",
    )
    assert repeated_agent == first_agent
    assert repeated_text != first_text


def test_daily_notification_includes_active_goal():
    user = User(id=1, language="ru", birth_date=date(2000, 1, 1))
    goal = Goal(user_id=user.id, text="Завершить первую версию")

    message = build_daily_notification(user, goal, date(2000, 1, 15))

    assert "Карл Юнг" in message
    assert "Ваша активная цель: Завершить первую версию" in message
    assert "Выберите один шаг на сегодня." in message


def test_daily_notification_without_goal_uses_english_fallback():
    user = User(id=1, language="unsupported", birth_date=date(2000, 1, 1))

    message = build_daily_notification(user, None, date(2000, 1, 15))

    assert "Carl Jung" in message
    assert "Choose one meaningful action for today." in message


def test_daily_keyboard_opens_calendar_with_goal_label(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view: f"https://aeon.test/?view={view}")

    keyboard = _daily_keyboard("ru", has_goal=True)

    assert keyboard is not None
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "Открыть цель"
    assert button.web_app is not None
    assert button.web_app.url == "https://aeon.test/?view=calendar"
