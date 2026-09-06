"""DB-free tests for ops notifications, /stats access rules, and digest scheduling."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

from app.bot import runtime
from app.core.config import get_settings
from app.db.models import User
from app.services import ops, stats


class FakeBot:
    def __init__(self):
        self.sent: list[dict] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append({"chat_id": chat_id, "text": text, **kwargs})


def _ops_settings(monkeypatch, **overrides):
    settings = get_settings()
    values = {"ops_chat_id": -100123, "ops_thread_sales": 7, "ops_admin_ids": "42, 43"} | overrides
    for key, value in values.items():
        monkeypatch.setattr(settings, key, value)
    return settings


def _user(**fields) -> User:
    defaults = dict(
        id=900_000_777,
        language="ru",
        country="Kazakhstan",
        created_at=datetime.now(UTC) - timedelta(days=3),
    )
    return User(**(defaults | fields))


async def _flush_tasks():
    await asyncio.sleep(0)
    await asyncio.sleep(0)


async def test_notify_is_noop_when_ops_chat_is_not_configured(monkeypatch):
    _ops_settings(monkeypatch, ops_chat_id=0)
    bot = FakeBot()
    monkeypatch.setattr(runtime, "get_application", lambda: SimpleNamespace(bot=bot))

    assert ops.notify("hello") is None
    await _flush_tasks()
    assert bot.sent == []


async def test_notify_sends_to_ops_chat_thread_in_background(monkeypatch):
    _ops_settings(monkeypatch)
    bot = FakeBot()
    monkeypatch.setattr(runtime, "get_application", lambda: SimpleNamespace(bot=bot))

    task = ops.notify("<b>hi</b>", ops.THREAD_SALES)
    assert task is not None
    await task
    assert bot.sent[0]["chat_id"] == -100123
    assert bot.sent[0]["message_thread_id"] == 7
    assert bot.sent[0]["parse_mode"] == "HTML"


async def test_send_swallows_telegram_failures(monkeypatch):
    _ops_settings(monkeypatch)

    class BrokenBot:
        async def send_message(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(runtime, "get_application", lambda: SimpleNamespace(bot=BrokenBot()))
    assert await ops.send("x") is False


async def test_alerts_are_throttled_per_kind(monkeypatch):
    _ops_settings(monkeypatch)
    bot = FakeBot()
    monkeypatch.setattr(runtime, "get_application", lambda: SimpleNamespace(bot=bot))
    ops.reset_alert_throttle()
    now = datetime(2026, 9, 7, 12, tzinfo=UTC)

    first = ops.alert("gemini:agent", "one", now)
    second = ops.alert("gemini:agent", "two", now + timedelta(seconds=30))
    other = ops.alert("gemini:council", "three", now + timedelta(seconds=30))
    later = ops.alert("gemini:agent", "four", now + timedelta(seconds=ops.ALERT_THROTTLE_SECONDS))

    assert first is not None and other is not None and later is not None
    assert second is None
    await asyncio.gather(first, other, later)
    assert [message["text"].splitlines()[-1] for message in bot.sent] == ["one", "three", "four"]
    ops.reset_alert_throttle()


def test_stats_access_is_limited_to_ops_chat_and_admins(monkeypatch):
    _ops_settings(monkeypatch)

    assert ops.is_ops_request(-100123, 1)
    assert ops.is_ops_request(42, 42)
    assert ops.is_ops_request(43, 43)
    assert not ops.is_ops_request(500, 500)
    assert not ops.is_ops_request(500, None)


def test_payment_message_marks_renewals_and_identifies_the_user(monkeypatch):
    monkeypatch.setattr(get_settings(), "mini_app_url", "https://aeon.example")
    user = _user(
        name="Ada <Lovelace>",
        username="ada_l",
        pro_expires_at=datetime(2026, 10, 7, tzinfo=UTC),
    )

    text = ops.format_payment_succeeded(
        user, amount=350, currency="XTR", renewal=False, expires_at=user.pro_expires_at
    )
    renewal = ops.format_payment_succeeded(
        user, amount=350, currency="XTR", renewal=True, expires_at=user.pro_expires_at
    )

    assert "New Pro subscription" in text and "350 ★" in text
    # Name is a profile link (escaped), username and id follow, then the admin card link.
    assert '<a href="tg://user?id=900000777">Ada &lt;Lovelace&gt;</a>' in text
    assert "@ada_l" in text
    assert "900000777" in text and "Kazakhstan" in text and "plan Pro" in text
    assert 'href="https://aeon.example/admin/users/900000777"' in text
    assert "day 3 since signup" in text and "active until 2026-10-07" in text
    assert "Subscription renewed" in renewal


def test_onboarding_message_escapes_user_text():
    user = _user(
        main_goal="Build <b>company</b> & retire",
        birth_date=date(1999, 5, 7),
        activity="founder",
        location="Almaty",
    )

    text = ops.format_onboarding_completed(user)

    assert "&lt;b&gt;company&lt;/b&gt; &amp; retire" in text
    assert "y.o." in text and "Almaty" in text and "activity: founder" in text


def test_new_user_message_without_username_or_admin_url(monkeypatch):
    monkeypatch.setattr(get_settings(), "mini_app_url", "")
    user = _user(name="", username="")

    text = ops.format_user_created(user)

    assert text.startswith("🆕 New user\n")
    assert '<a href="tg://user?id=900000777">no name</a>' in text
    assert "@" not in text and "admin card" not in text


def test_generation_failure_alert_names_agent_mode_and_status():
    from app.clients.gemini import GeminiError

    user = _user(name="Ada", username="ada_l")
    error = GeminiError("Gemini API failed with HTTP 429: quota", status=429)

    text = ops.format_generation_failed(user, error, kind="agent", agent_id="jung", mode="rag")

    assert text.startswith("gemini failed · agent · jung · rag\n")
    assert "@ada_l" in text
    assert "HTTP 429 · GeminiError: Gemini API failed with HTTP 429: quota" in text


def test_digests_due_only_at_the_configured_hour():
    monday_first = datetime(2026, 6, 1, 9, 5)  # Monday and the 1st of the month
    assert stats.digests_due(monday_first, 9) == ["daily", "weekly", "monthly"]
    assert stats.digests_due(monday_first.replace(hour=10), 9) == []
    assert stats.digests_due(datetime(2026, 6, 3, 9), 9) == ["daily"]
    assert stats.digests_due(datetime(2026, 6, 8, 9), 9) == ["daily", "weekly"]


def test_digest_windows_follow_the_ops_timezone():
    today = date(2026, 9, 7)  # a Monday

    daily = stats.digest_window("daily", today, "Asia/Almaty")
    weekly = stats.digest_window("weekly", today, "Asia/Almaty")
    monthly = stats.digest_window("monthly", today, "Asia/Almaty")

    assert daily.label == "2026-09-06"
    assert daily.since == datetime(2026, 9, 5, 19, tzinfo=UTC)
    assert daily.until == datetime(2026, 9, 6, 19, tzinfo=UTC)
    assert weekly.label == "2026-08-31 – 2026-09-06"
    assert weekly.until - weekly.since == timedelta(days=7)
    assert monthly.label == "August 2026"
    assert monthly.since == datetime(2026, 7, 31, 19, tzinfo=UTC)
    assert monthly.until == datetime(2026, 8, 31, 19, tzinfo=UTC)


def test_today_and_last_days_windows_end_now():
    now = datetime(2026, 9, 7, 3, 30, tzinfo=UTC)  # 08:30 in Almaty

    today = stats.today_window(now, "Asia/Almaty")
    week = stats.last_days_window(now, "Asia/Almaty", 7)

    assert today.since == datetime(2026, 9, 6, 19, tzinfo=UTC) and today.until == now
    assert week.since == datetime(2026, 8, 31, 19, tzinfo=UTC) and week.label == "last 7 days"


def test_format_stats_renders_every_section():
    window = stats.Window(
        "today", datetime(2026, 9, 7, tzinfo=UTC), datetime(2026, 9, 7, 12, tzinfo=UTC)
    )
    collected = stats.Stats(
        window=window,
        users_total=120,
        new_users=4,
        active_users=17,
        prompt_questions=30,
        rag_questions=12,
        council_questions=2,
        conversations_started=9,
        conversations_by_agent={"jung": 5, "aurelius": 4},
        payments_count=1,
        payments_stars=350,
        pro_active=6,
        trial_active=3,
    )

    text = stats.format_stats(collected, "Aeon stats")

    assert text.startswith("<b>Aeon stats</b> · today")
    assert "total: 44 (prompt 30, rag 12, council 2)" in text
    assert "conversations: 9 (jung 5, aurelius 4)" in text
    assert "payments: 1 · 350 ★" in text
    assert "Pro: 6 (expiring ≤3d: 0, not renewing: 0) · Trial: 3" in text
