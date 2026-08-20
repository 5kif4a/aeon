"""Reusable inline keyboards for the Telegram bot."""

from collections.abc import Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.agents import AGENTS, agent_button
from app.bot import webapp
from app.i18n import t

TIMEZONE_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("utc", "UTC", "UTC"),
    ("london", "Europe/London", "London"),
    ("new_york", "America/New_York", "New York"),
    ("los_angeles", "America/Los_Angeles", "Los Angeles"),
    ("toronto", "America/Toronto", "Toronto"),
    ("berlin", "Europe/Berlin", "Berlin"),
    ("madrid", "Europe/Madrid", "Madrid"),
    ("almaty", "Asia/Almaty", "Almaty"),
)


def _mini_app_button(language: str, key: str, view: str = "home") -> InlineKeyboardButton | None:
    url = webapp.build_webapp_url(view)
    if not url:
        return None
    return InlineKeyboardButton(t(language, key), web_app=WebAppInfo(url=url))


def _markup(rows: Iterable[Iterable[InlineKeyboardButton | None]]) -> InlineKeyboardMarkup:
    cleaned = []
    for row in rows:
        buttons = [button for button in row if button is not None]
        if buttons:
            cleaned.append(buttons)
    return InlineKeyboardMarkup(cleaned)


def home_keyboard(language: str, *, profile_complete: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton | None]] = [
        [
            InlineKeyboardButton(t(language, "pick_agent_button"), callback_data="agent:picker"),
            InlineKeyboardButton(t(language, "council_button"), callback_data="council:start"),
        ],
        [_mini_app_button(language, "open_aeon", "home")],
    ]
    if not profile_complete:
        rows.append(
            [InlineKeyboardButton(t(language, "complete_profile_button"), callback_data="profile:setup")]
        )
    rows.append(
        [InlineKeyboardButton(t(language, "settings_button"), callback_data="settings:open")]
    )
    return _markup(rows)


def agent_picker_keyboard(language: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(agent_button(agent_id, language), callback_data=f"agent:{agent_id}")]
        for agent_id in AGENTS
    ]
    rows.append(
        [InlineKeyboardButton(t(language, "council_button"), callback_data="council:start")]
    )
    rows.append([InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")])
    return InlineKeyboardMarkup(rows)


def post_answer_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t(language, "switch_agent_button"), callback_data="agent:picker"),
                InlineKeyboardButton(t(language, "council_button"), callback_data="council:start"),
            ],
            [InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")],
        ]
    )


def back_home_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")]]
    )


def limit_keyboard(language: str, plan: str) -> InlineKeyboardMarkup:
    primary: InlineKeyboardButton | None
    if plan.lower() == "free":
        primary = _mini_app_button(language, "start_trial_button", "profile")
    elif plan.lower() == "trial":
        primary = InlineKeyboardButton(t(language, "upgrade_pro_button"), callback_data="billing:subscribe")
    else:
        primary = _mini_app_button(language, "open_aeon", "profile")
    return _markup(
        [
            [primary],
            [InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")],
        ]
    )


def settings_keyboard(user) -> InlineKeyboardMarkup:
    language = user.language
    daily_enabled = user.daily_notifications_enabled is not False
    weekly_enabled = user.weekly_notifications_enabled is not False
    reminder_hour = user.reminder_hour if user.reminder_hour is not None else 9
    reminder_timezone = user.reminder_timezone or "UTC"
    daily_key = "notifications_on" if daily_enabled else "notifications_off"
    weekly_key = "notifications_on" if weekly_enabled else "notifications_off"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{t(language, 'daily_setting')}: {t(language, daily_key)}",
                    callback_data="settings:daily",
                )
            ],
            [
                InlineKeyboardButton(
                    f"{t(language, 'weekly_setting')}: {t(language, weekly_key)}",
                    callback_data="settings:weekly",
                )
            ],
            [
                InlineKeyboardButton(
                    t(language, "reminder_time_button", hour=reminder_hour),
                    callback_data="settings:time",
                ),
                InlineKeyboardButton(
                    t(language, "timezone_button", timezone=timezone_label(reminder_timezone)),
                    callback_data="settings:timezone",
                ),
            ],
            [
                InlineKeyboardButton("English", callback_data="settings:language:en"),
                InlineKeyboardButton("Русский", callback_data="settings:language:ru"),
            ],
            [InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")],
        ]
    )


def reminder_time_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"{hour:02d}:00", callback_data=f"settings:hour:{hour}")
                for hour in (8, 10)
            ],
            [
                InlineKeyboardButton(f"{hour:02d}:00", callback_data=f"settings:hour:{hour}")
                for hour in (13, 18)
            ],
            [
                InlineKeyboardButton(f"{hour:02d}:00", callback_data=f"settings:hour:{hour}")
                for hour in (20, 22)
            ],
            [InlineKeyboardButton(t(language, "back_settings"), callback_data="settings:open")],
        ]
    )


def timezone_keyboard(language: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for token, _zone, label in TIMEZONE_OPTIONS:
        row.append(InlineKeyboardButton(label, callback_data=f"settings:tz:{token}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(t(language, "back_settings"), callback_data="settings:open")])
    return InlineKeyboardMarkup(rows)


def timezone_from_token(token: str) -> str | None:
    return next((zone for key, zone, _label in TIMEZONE_OPTIONS if key == token), None)


def timezone_label(zone: str) -> str:
    return next((label for _key, value, label in TIMEZONE_OPTIONS if value == zone), zone)
