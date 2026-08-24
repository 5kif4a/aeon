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
from app.i18n import daily_notification_content, life_weekly_content, notification_agent_id
from app.services.users import notification_is_due


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


def test_weekly_quotes_have_a_24_week_rotation():
    quotes = {life_weekly_content("en", week)[1] for week in range(24)}

    assert len(quotes) == 24


def test_build_life_weekly_message_uses_russian_localization():
    user = User(id=1, language="ru", birth_date=date(2000, 1, 1))

    message = build_life_weekly_message(user, date(2000, 1, 15))

    assert message.startswith("«")
    assert message.index("»") < message.index("— Карл Юнг")
    assert "Завершилась 2-я неделя Вашей жизни." in message
    assert "Карл Юнг" in message
    assert "Выберите одну цель на новую неделю." in message


def test_calendar_keyboard_opens_calendar(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view: f"https://aeon.test/?view={view}")

    keyboard = _calendar_keyboard("ru", "jung")

    assert keyboard is not None
    button = keyboard.inline_keyboard[0][0]
    assert button.text == "Открыть календарь"
    assert button.web_app is not None
    assert button.web_app.url == "https://aeon.test/?view=calendar"
    assert keyboard.inline_keyboard[1][0].callback_data == "agent:jung"


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


def test_daily_quotes_have_a_24_day_rotation():
    quotes = {daily_notification_content("ru", day)[1] for day in range(24)}

    assert len(quotes) == 24


def test_notification_agent_id_matches_content_rotation():
    assert [notification_agent_id(day) for day in range(3)] == [
        "aurelius",
        "machiavelli",
        "jung",
    ]


def test_daily_notification_includes_active_goal():
    user = User(id=1, language="ru", birth_date=date(2000, 1, 1))
    goal = Goal(user_id=user.id, text="Завершить первую версию")

    message = build_daily_notification(user, goal, date(2000, 1, 15))

    assert message.startswith("«")
    assert message.index("»") < message.index("— Карл Юнг")
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

    keyboard = _daily_keyboard("ru", has_goal=True, agent_id="jung")

    assert keyboard is not None
    done_button = keyboard.inline_keyboard[0][0]
    goal_button = keyboard.inline_keyboard[1][0]
    author_button = keyboard.inline_keyboard[2][0]
    settings_button = keyboard.inline_keyboard[3][0]

    assert done_button.callback_data == "daily:done"
    assert goal_button.text == "Открыть цель"
    assert goal_button.web_app is not None
    assert goal_button.web_app.url == "https://aeon.test/?view=calendar"
    assert author_button.text == "Спросить автора"
    assert author_button.callback_data == "agent:jung"
    assert settings_button.callback_data == "settings:open"


def test_notification_is_due_in_the_users_local_timezone():
    user = User(
        id=1,
        reminder_timezone="America/New_York",
        reminder_hour=9,
    )
    now = datetime(2026, 1, 15, 14, 30, tzinfo=UTC)

    assert notification_is_due(user, now)


def test_notification_is_not_due_outside_the_users_local_hour():
    user = User(
        id=1,
        reminder_timezone="Europe/London",
        reminder_hour=9,
    )
    now = datetime(2026, 1, 15, 14, 30, tzinfo=UTC)

    assert not notification_is_due(user, now)
