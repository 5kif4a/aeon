import pytest

from app.agents import AGENTS
from app.bot import ui, webapp
from app.db.models import User
from app.i18n import t
from app.services import users


def _callbacks(keyboard) -> list[str]:
    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    ]


def test_agent_picker_offers_only_the_three_advisors():
    keyboard = ui.agent_picker_keyboard("ru")

    assert _callbacks(keyboard) == [f"agent:{agent_id}" for agent_id in AGENTS]
    assert len(keyboard.inline_keyboard) == 3


def test_agent_picker_prefix_addresses_the_onboarding_step():
    keyboard = ui.agent_picker_keyboard("en", prefix="onboarding:agent")

    assert _callbacks(keyboard) == [f"onboarding:agent:{agent_id}" for agent_id in AGENTS]


def test_agent_intro_keyboard_only_opens_the_mini_app(monkeypatch):
    monkeypatch.setattr(
        webapp, "build_webapp_url", lambda view="home", **params: f"https://aeon.test/{view}"
    )

    keyboard = ui.agent_intro_keyboard("ru")

    assert _callbacks(keyboard) == []
    web_buttons = [b for row in keyboard.inline_keyboard for b in row if b.web_app]
    assert len(web_buttons) == 1
    assert web_buttons[0].text == t("ru", "open_aeon")


def test_agent_intro_keyboard_is_absent_without_a_mini_app(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view="home", **params: "")

    assert ui.agent_intro_keyboard("ru") is None


def test_post_answer_keyboard_only_switches_advisor():
    assert _callbacks(ui.post_answer_keyboard("en")) == ["agent:picker"]


def test_language_keyboard_puts_the_detected_language_first():
    keyboard = ui.language_keyboard("lang", detected="ru")

    assert _callbacks(keyboard) == ["lang:ru", "lang:en"]
    assert keyboard.inline_keyboard[0][0].text == "✓ Русский"
    assert keyboard.inline_keyboard[1][0].text == "English"


def test_home_keyboard_opens_the_mini_app_and_switches_advisor(monkeypatch):
    monkeypatch.setattr(
        webapp, "build_webapp_url", lambda view="home", **params: f"https://aeon.test/{view}"
    )

    keyboard = ui.home_keyboard("en")
    web_buttons = [b for row in keyboard.inline_keyboard for b in row if b.web_app]

    assert len(web_buttons) == 1
    assert web_buttons[0].web_app.url == "https://aeon.test/home"
    assert _callbacks(keyboard) == ["agent:picker"]


def test_home_keyboard_does_not_emit_empty_rows_without_mini_app(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view="home", **params: "")

    keyboard = ui.home_keyboard("en")

    assert keyboard.inline_keyboard
    assert all(row for row in keyboard.inline_keyboard)
    assert _callbacks(keyboard) == ["agent:picker"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Alikhan", "Alikhan"),
        ("  Ali  ", "Ali"),
        ("", ""),
        ("   ", ""),
        ("—", ""),
        ("…", ""),
        (None, ""),
    ],
)
def test_presentable_name_drops_placeholders(raw, expected):
    assert users.presentable_name(raw) == expected


def test_greeting_keys_exist_in_both_languages():
    for key in (
        "home_welcome",
        "home_welcome_named",
        "home_returning",
        "home_returning_named",
        "home_active_agent",
        "choose_language",
        "language_saved",
        "onboarding_welcome",
    ):
        assert t("en", key) != key
        assert t("ru", key) != key
    assert "{name}" in t("ru", "home_welcome_named")
    assert "{name}" not in t("ru", "home_welcome")


def test_free_limit_offers_the_trial_first():
    keyboard = ui.limit_keyboard("en", "Free", can_start_trial=True)
    primary = keyboard.inline_keyboard[0][0]

    assert primary.text == "Try it free"
    assert primary.callback_data == "billing:trial"


def test_free_limit_after_trial_leads_to_the_invoice():
    keyboard = ui.limit_keyboard("en", "Free", can_start_trial=False)
    primary = keyboard.inline_keyboard[0][0]

    assert primary.text == "Open Primus"
    assert primary.callback_data == "billing:subscribe"


def test_trial_limit_leads_directly_to_the_invoice():
    keyboard = ui.limit_keyboard("ru", "Trial", can_start_trial=True)

    assert keyboard.inline_keyboard[0][0].callback_data == "billing:subscribe"


def test_settings_keyboard_contains_independent_notification_toggles():
    user = User(
        id=1,
        language="en",
        daily_notifications_enabled=True,
        weekly_notifications_enabled=False,
        reminder_timezone="Europe/London",
        reminder_hour=10,
    )

    keyboard = ui.settings_keyboard(user)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert "Morning: On" in labels
    assert "Morning 10:00" in labels
    assert "Evening question: On" in labels
    assert "Evening 21:00" in labels
    assert "Weekly: Off" in labels
    # The offset moves with DST, so only its shape is asserted.
    assert any(label.startswith("Zone: London (UTC") for label in labels)


def test_reminder_time_keyboard_offers_every_hour_and_marks_the_current_one():
    keyboard = ui.reminder_time_keyboard("en", 10)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    hours = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data.startswith("settings:hour:")
    ]

    assert len(hours) == 24
    assert hours[0] == "settings:hour:0" and hours[-1] == "settings:hour:23"
    assert "• 10:00" in labels
    assert "09:00" in labels


def test_timezone_keyboard_marks_the_current_zone():
    keyboard = ui.timezone_keyboard("en", "Asia/Almaty")
    labels = [button.text for row in keyboard.inline_keyboard for button in row]

    assert "• Almaty" in labels
    assert "Almaty" not in labels


def test_utc_offset_label_formats_whole_and_half_hours():
    assert ui.utc_offset_label("UTC") == "UTC+0"
    assert ui.utc_offset_label("Asia/Almaty") == "UTC+5"
    assert ui.utc_offset_label("Asia/Kolkata") == "UTC+5:30"
    assert ui.utc_offset_label("Not/AZone") == ""


def test_user_facing_errors_do_not_expose_provider_configuration():
    for language in ("en", "ru"):
        combined = " ".join(
            t(language, key, model="internal")
            for key in (
                "gemini_not_configured",
                "error_model_unavailable",
                "error_key_rejected",
            )
        )
        assert "Gemini" not in combined
        assert "GEMINI_" not in combined


def test_build_webapp_url_produces_router_paths(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "mini_app_url", "https://aeon.test/")
    assert webapp.build_webapp_url() == "https://aeon.test/"
    assert webapp.build_webapp_url("calendar", tab="goal") == "https://aeon.test/calendar?tab=goal"
    assert webapp.build_webapp_url("profile", sheet="pro") == "https://aeon.test/profile?sheet=pro"
    monkeypatch.setattr(get_settings(), "mini_app_url", "")
    assert webapp.build_webapp_url("calendar") == ""


def _private_update(**message_fields):
    from datetime import UTC, datetime

    from telegram import Chat, Message, Update

    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=42, type=Chat.PRIVATE),
        **message_fields,
    )
    return Update(update_id=1, message=message)


def test_unsupported_message_filter_catches_voice_but_not_text_or_status_updates():
    from telegram import Voice

    from app.bot.handlers.commands import UNSUPPORTED_MESSAGE_FILTER

    voice = _private_update(voice=Voice(file_id="v", file_unique_id="vu", duration=3))
    text = _private_update(text="Как жить?")
    command = _private_update(text="/start", entities=[])
    status = _private_update(pinned_message=None, new_chat_title="Renamed")

    assert UNSUPPORTED_MESSAGE_FILTER.check_update(voice)
    assert not UNSUPPORTED_MESSAGE_FILTER.check_update(text)
    assert not UNSUPPORTED_MESSAGE_FILTER.check_update(command)
    assert not UNSUPPORTED_MESSAGE_FILTER.check_update(status)


def test_unsupported_message_text_exists_in_both_languages():
    assert "текст" in t("ru", "unsupported_message")
    assert "text" in t("en", "unsupported_message")
