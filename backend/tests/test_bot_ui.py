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
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view="home": f"https://aeon.test/{view}")

    keyboard = ui.home_keyboard("en", profile_complete=False)
    callbacks = _callbacks(keyboard)

    assert "agent:picker" in callbacks
    assert "council:start" in callbacks
    assert "profile:setup" in callbacks
    assert "settings:open" in callbacks


def test_completed_profile_does_not_show_setup_again(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view="home": f"https://aeon.test/{view}")

    keyboard = ui.home_keyboard("en", profile_complete=True)

    assert "profile:setup" not in _callbacks(keyboard)


def test_keyboards_do_not_emit_empty_rows_without_mini_app(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view="home": "")

    keyboard = ui.home_keyboard("en", profile_complete=True)

    assert keyboard.inline_keyboard
    assert all(row for row in keyboard.inline_keyboard)


def test_free_limit_leads_to_trial(monkeypatch):
    monkeypatch.setattr(webapp, "build_webapp_url", lambda view="home": f"https://aeon.test/{view}")

    keyboard = ui.limit_keyboard("en", "Free")
    primary = keyboard.inline_keyboard[0][0]

    assert primary.text == "Start 7-day Trial"
    assert primary.web_app.url == "https://aeon.test/profile"


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
    assert "Zone: London" in labels


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
