"""Reusable inline keyboards for the Telegram bot."""

from collections.abc import Iterable
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.agents import AGENTS, agent_button
from app.bot import webapp
from app.i18n import SUPPORTED_LANGUAGES, t

# (callback token, IANA zone, city label). Mirrored in frontend/src/lib/options.ts so the
# bot and the Mini App offer the same zones; the Mini App additionally accepts whatever
# zone the device reports. Tokens are part of callback data - never rename one in place.
TIMEZONE_OPTIONS: tuple[tuple[str, str, str], ...] = (
    ("utc", "UTC", "UTC"),
    ("lisbon", "Europe/Lisbon", "Lisbon"),
    ("london", "Europe/London", "London"),
    ("berlin", "Europe/Berlin", "Berlin"),
    ("madrid", "Europe/Madrid", "Madrid"),
    ("warsaw", "Europe/Warsaw", "Warsaw"),
    ("kyiv", "Europe/Kyiv", "Kyiv"),
    ("istanbul", "Europe/Istanbul", "Istanbul"),
    ("moscow", "Europe/Moscow", "Moscow"),
    ("tbilisi", "Asia/Tbilisi", "Tbilisi"),
    ("yerevan", "Asia/Yerevan", "Yerevan"),
    ("dubai", "Asia/Dubai", "Dubai"),
    ("tashkent", "Asia/Tashkent", "Tashkent"),
    ("almaty", "Asia/Almaty", "Almaty"),
    ("bangkok", "Asia/Bangkok", "Bangkok"),
    ("singapore", "Asia/Singapore", "Singapore"),
    ("tokyo", "Asia/Tokyo", "Tokyo"),
    ("sydney", "Australia/Sydney", "Sydney"),
    ("sao_paulo", "America/Sao_Paulo", "Sao Paulo"),
    ("new_york", "America/New_York", "New York"),
    ("toronto", "America/Toronto", "Toronto"),
    ("chicago", "America/Chicago", "Chicago"),
    ("denver", "America/Denver", "Denver"),
    ("los_angeles", "America/Los_Angeles", "Los Angeles"),
)

# Delivery hours offered in the bot; the Mini App offers the same range.
REMINDER_HOURS: tuple[int, ...] = tuple(range(24))
HOURS_PER_ROW = 4
TIMEZONES_PER_ROW = 3


def _mini_app_button(
    language: str, key: str, view: str = "home", **params: str
) -> InlineKeyboardButton | None:
    url = webapp.build_webapp_url(view, **params)
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


LANGUAGE_LABELS = {"en": "English", "ru": "Русский"}


def language_keyboard(prefix: str, *, detected: str) -> InlineKeyboardMarkup:
    # The detected (or current) language goes first so the likely answer is one tap away.
    ordered = [detected, *(code for code in SUPPORTED_LANGUAGES if code != detected)]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"{'✓ ' if code == detected else ''}{LANGUAGE_LABELS[code]}",
                    callback_data=f"{prefix}:{code}",
                )
            ]
            for code in ordered
        ]
    )


def agent_picker_keyboard(language: str, *, prefix: str = "agent") -> InlineKeyboardMarkup:
    # The bot offers only the three advisors; the council lives in the Mini App.
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    agent_button(agent_id, language), callback_data=f"{prefix}:{agent_id}"
                )
            ]
            for agent_id in AGENTS
        ]
    )


def home_keyboard(language: str) -> InlineKeyboardMarkup:
    return _markup(
        [
            [_mini_app_button(language, "open_aeon", "home")],
            [
                InlineKeyboardButton(
                    t(language, "switch_agent_button"), callback_data="agent:picker"
                )
            ],
        ]
    )


def agent_intro_keyboard(language: str) -> InlineKeyboardMarkup | None:
    """The advisor has just greeted the user: the only offer is the Mini App.

    Returns None rather than an empty markup so an unset MINI_APP_URL leaves the message
    bare instead of sending a keyboard with no buttons.
    """
    button = _mini_app_button(language, "open_aeon", "home")
    return InlineKeyboardMarkup([[button]]) if button else None


def post_answer_keyboard(language: str, *, offer_app: bool = False) -> InlineKeyboardMarkup:
    """Under an advisor's answer: switch advisor, and, until the Mini App has been opened
    once, the app itself. The bot is where people start; the app is where the goals, the
    diary and the device time zone live, so the first answers keep pointing at it."""
    return _markup(
        [
            [
                InlineKeyboardButton(
                    t(language, "switch_agent_button"), callback_data="agent:picker"
                )
            ],
            [_mini_app_button(language, "open_aeon", "home")] if offer_app else [],
        ]
    )


def back_home_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")]]
    )


def limit_keyboard(
    language: str, plan: str, *, can_start_trial: bool = False
) -> InlineKeyboardMarkup:
    # A Free user who never had a Trial gets it in one tap; everyone else on Free/Trial gets
    # the Stars invoice directly.
    if plan.lower() == "free" and can_start_trial:
        primary = InlineKeyboardButton(
            t(language, "trial_start_button"), callback_data="billing:trial"
        )
    elif plan.lower() in ("free", "trial"):
        primary = InlineKeyboardButton(
            t(language, "upgrade_pro_button"), callback_data="billing:subscribe"
        )
    else:
        primary = _mini_app_button(language, "open_aeon", "profile", sheet="pro")
    return _markup(
        [
            [primary],
            [InlineKeyboardButton(t(language, "back_home"), callback_data="menu:home")],
        ]
    )


def settings_keyboard(user) -> InlineKeyboardMarkup:
    language = user.language
    daily_enabled = user.daily_notifications_enabled is not False
    evening_enabled = user.evening_enabled is not False
    weekly_enabled = user.weekly_notifications_enabled is not False
    reminder_hour = user.reminder_hour if user.reminder_hour is not None else 9
    evening_hour = user.evening_hour if user.evening_hour is not None else 21
    reminder_timezone = user.reminder_timezone or "UTC"
    marketing_enabled = user.marketing_enabled is not False
    daily_key = "notifications_on" if daily_enabled else "notifications_off"
    evening_key = "notifications_on" if evening_enabled else "notifications_off"
    weekly_key = "notifications_on" if weekly_enabled else "notifications_off"
    marketing_key = "notifications_on" if marketing_enabled else "notifications_off"
    # Same settings, larger screen: the Mini App writes the very same columns.
    app_button = _mini_app_button(language, "settings_open_app", "profile", sheet="notifications")
    return InlineKeyboardMarkup(
        [
            *([[app_button]] if app_button else []),
            [
                InlineKeyboardButton(
                    f"{t(language, 'daily_setting')}: {t(language, daily_key)}",
                    callback_data="settings:daily",
                ),
                InlineKeyboardButton(
                    t(language, "reminder_time_button", hour=reminder_hour),
                    callback_data="settings:time",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{t(language, 'evening_setting')}: {t(language, evening_key)}",
                    callback_data="settings:evening",
                ),
                InlineKeyboardButton(
                    t(language, "evening_time_button", hour=evening_hour),
                    callback_data="settings:evening_time",
                ),
            ],
            [
                InlineKeyboardButton(
                    f"{t(language, 'weekly_setting')}: {t(language, weekly_key)}",
                    callback_data="settings:weekly",
                )
            ],
            [
                InlineKeyboardButton(
                    f"{t(language, 'marketing_setting')}: {t(language, marketing_key)}",
                    callback_data="settings:marketing",
                )
            ],
            [
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


def _chunk(buttons: list[InlineKeyboardButton], per_row: int) -> list[list[InlineKeyboardButton]]:
    return [buttons[start : start + per_row] for start in range(0, len(buttons), per_row)]


def reminder_time_keyboard(
    language: str, selected_hour: int | None = None, *, slot: str = "hour"
) -> InlineKeyboardMarkup:
    """Every hour of the day; the current one is marked so the choice is visible.

    `slot` is the callback token: "hour" for the morning message, "evening_hour" for the
    evening question.
    """
    buttons = [
        InlineKeyboardButton(
            f"• {hour:02d}:00" if hour == selected_hour else f"{hour:02d}:00",
            callback_data=f"settings:{slot}:{hour}",
        )
        for hour in REMINDER_HOURS
    ]
    rows = _chunk(buttons, HOURS_PER_ROW)
    rows.append([InlineKeyboardButton(t(language, "back_settings"), callback_data="settings:open")])
    return InlineKeyboardMarkup(rows)


def timezone_keyboard(language: str, selected_zone: str | None = None) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            f"• {label}" if zone == selected_zone else label,
            callback_data=f"settings:tz:{token}",
        )
        for token, zone, label in TIMEZONE_OPTIONS
    ]
    rows = _chunk(buttons, TIMEZONES_PER_ROW)
    rows.append([InlineKeyboardButton(t(language, "back_settings"), callback_data="settings:open")])
    return InlineKeyboardMarkup(rows)


def timezone_from_token(token: str) -> str | None:
    return next((zone for key, zone, _label in TIMEZONE_OPTIONS if key == token), None)


def timezone_label(zone: str) -> str:
    """City plus its current UTC offset; falls back to the raw zone for device-set ones.

    `Etc/GMT-4` is the language fallback zone and means UTC+4 (the IANA sign is inverted);
    showing its name would read as the opposite offset, so it is shown as the offset alone.
    """
    offset = utc_offset_label(zone)
    if zone.startswith("Etc/"):
        return offset or zone
    label = next((value for _key, known, value in TIMEZONE_OPTIONS if known == zone), zone)
    return f"{label} ({offset})" if offset else label


def utc_offset_label(zone: str) -> str:
    """`UTC+5`, `UTC-3:30`, or an empty string when the zone is unknown."""
    try:
        offset = datetime.now(ZoneInfo(zone)).utcoffset()
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return ""
    if offset is None:
        return ""
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"UTC{sign}{hours}" + (f":{minutes:02d}" if minutes else "")
