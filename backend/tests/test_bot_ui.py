from app.bot import ui, webapp
from app.db.models import User
from app.i18n import t


def _callbacks(keyboard) -> list[str]:
    return [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data
    ]


def test_home_keyboard_exposes_primary_bot_actions(monkeypatch):
    monkeypatch.setattr(
        webapp, "build_webapp_url", lambda view="home", **params: f"https://aeon.test/{view}"
    )

    keyboard = ui.home_keyboard("en", profile_complete=False)
    callbacks = _callbacks(keyboard)

    assert "agent:picker" in callbacks
    assert "council:start" in callbacks
    assert "profile:setup" in callbacks
    assert "settings:open" in callbacks


def test_completed_profile_does_not_show_setup_again(monkeypatch):
    monkeypatch.setattr(
        webapp, "build_webapp_url", lambda view="home", **params: f"https://aeon.test/{view}"
    )

    keyboard = ui.home_keyboard("en", profile_complete=True)

    assert "profile:setup" not in _callbacks(keyboard)


def test_keyboards_do_not_emit_empty_rows_without_mini_app(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view="home", **params: "")

    keyboard = ui.home_keyboard("en", profile_complete=True)

    assert keyboard.inline_keyboard
    assert all(row for row in keyboard.inline_keyboard)


def test_free_limit_leads_directly_to_pro_invoice():
    keyboard = ui.limit_keyboard("en", "Free")
    primary = keyboard.inline_keyboard[0][0]

    assert primary.text == "Continue with Pro"
    assert primary.callback_data == "billing:subscribe"


def test_trial_limit_leads_directly_to_pro_invoice():
    keyboard = ui.limit_keyboard("ru", "Trial")

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

    assert "Daily: On" in labels
    assert "Weekly: Off" in labels
    assert "Time 10:00" in labels
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
