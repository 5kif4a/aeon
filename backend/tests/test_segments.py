"""DB-free tests for the segment filter DSL and the broadcast content rules."""

import pytest
from sqlalchemy.dialects import postgresql

from app.db.models import Broadcast, User
from app.i18n import SUPPORTED_LANGUAGES, t
from app.services import broadcasts, segments


def compiled(audience: segments.Audience) -> str:
    query = audience.select_users()
    return str(query.compile(dialect=postgresql.dialect()))


def test_validate_filters_normalizes_and_drops_empty_values():
    clean = segments.validate_filters(
        {
            "plans": "Pro",
            "languages": ["ru", "en"],
            "countries": [" Kazakhstan ", ""],
            "questionsMin": 0,
            "userIds": ["17", 42],
            "hasPaid": False,
            "genders": [],
            "signedUpWithinDays": None,
        }
    )
    assert clean == {
        "plans": ["Pro"],
        "languages": ["ru", "en"],
        "countries": ["Kazakhstan"],
        "questionsMin": 0,
        "userIds": [17, 42],
        "hasPaid": False,
    }


@pytest.mark.parametrize(
    "filters",
    [
        {"nope": 1},
        {"plans": ["Platinum"]},
        {"languages": ["de"]},
        {"questionsMin": -1},
        {"questionsMin": True},
        {"hasPaid": "yes"},
        {"signedUpWithinDays": "7"},
        {"userIds": ["abc"]},
    ],
)
def test_validate_filters_rejects_bad_definitions(filters):
    """A condition the SQL builder would silently drop must fail loudly instead."""
    with pytest.raises(segments.SegmentError):
        segments.validate_filters(filters)


def test_every_filter_key_builds_a_condition():
    filters = {}
    for spec in segments.FILTER_SPECS:
        if spec.kind == "bool":
            filters[spec.key] = True
        elif spec.kind == "int":
            filters[spec.key] = 7
        elif spec.kind == "enum":
            filters[spec.key] = [spec.options[0]]
        else:
            filters[spec.key] = ["1"] if spec.key == "userIds" else ["Kazakhstan"]
    conditions = segments.build_conditions(filters)
    assert len(conditions) == len(segments.FILTER_SPECS)


def test_marketing_audience_excludes_opted_out_users():
    marketing = compiled(segments.Audience(kind="dynamic", filters={}, respect_opt_out=True))
    service = compiled(segments.Audience(kind="dynamic", filters={}, respect_opt_out=False))
    assert "marketing_enabled IS true" in marketing
    assert "marketing_enabled IS true" not in service


def test_static_audience_needs_a_saved_segment():
    with pytest.raises(segments.SegmentError):
        segments.Audience(kind="static", filters={}).select_users()


def test_validate_content_requires_text_and_a_complete_button():
    clean = broadcasts.validate_content(
        {
            "ru": {"text": " Привет ", "buttonText": "Открыть", "buttonUrl": "https://t.me/x"},
            "en": {"text": "", "buttonText": "", "buttonUrl": ""},
        }
    )
    assert list(clean) == ["ru"] and clean["ru"]["text"] == "Привет"

    for broken in (
        {},
        {"ru": {"text": ""}},
        {"ru": {"text": "hi", "buttonText": "Go"}},
        {"ru": {"text": "hi", "buttonText": "Go", "buttonUrl": "javascript:alert(1)"}},
    ):
        with pytest.raises(broadcasts.BroadcastError):
            broadcasts.validate_content(broken)


def test_render_falls_back_to_the_default_language():
    broadcast = Broadcast(title="t", category="marketing", content={"en": {"text": "English"}})
    assert broadcasts.render(broadcast, "ru").text == "English"
    broadcast.content = {"ru": {"text": "Русский"}, "en": {"text": "English"}}
    assert broadcasts.render(broadcast, "ru").text == "Русский"
    broadcast.content = {}
    with pytest.raises(broadcasts.BroadcastError):
        broadcasts.render(broadcast, "ru")


def test_marketing_messages_carry_an_opt_out_button():
    from app.bot import broadcasting

    message = broadcasts.Message(text="hi", button_text="Open", button_url="https://t.me/x")
    marketing = broadcasting.keyboard("ru", message, broadcasts.MARKETING)
    labels = [button.text for row in marketing.inline_keyboard for button in row]
    assert labels == ["Open", t("ru", "marketing_unsubscribe_button")]

    service = broadcasting.keyboard("ru", broadcasts.Message(text="hi"), broadcasts.SERVICE)
    assert service is None


def test_settings_keyboard_exposes_the_marketing_toggle():
    from app.bot import ui

    user = User(id=1, language="ru", marketing_enabled=False)
    labels = [button.text for row in ui.settings_keyboard(user).inline_keyboard for button in row]
    off = f"{t('ru', 'marketing_setting')}: {t('ru', 'notifications_off')}"
    assert off in labels


def test_marketing_keys_exist_in_every_language():
    for language in SUPPORTED_LANGUAGES:
        for key in ("marketing_setting", "marketing_unsubscribe_button", "marketing_unsubscribed"):
            assert t(language, key) and not t(language, key).startswith("[")
