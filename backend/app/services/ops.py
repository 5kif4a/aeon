"""Product-owner notifications: pushes to the ops Telegram group.

Sends are fire-and-forget so a slow or failing Telegram call never delays a user-facing
handler or holds a DB session open. Texts are internal (English, HTML), keyed by user id and
country/language only: no names and no message content leave the database.
"""

import asyncio
import html
import logging
from datetime import UTC, datetime

from app.bot import runtime
from app.core.config import get_settings
from app.db.models import BillingPayment, User
from app.services import billing

logger = logging.getLogger(__name__)

THREAD_SALES = "sales"
THREAD_ALERTS = "alerts"
THREAD_DIGESTS = "digests"

# Alerts of the same kind are collapsed into one message per window.
ALERT_THROTTLE_SECONDS = 600
_last_alert_at: dict[str, datetime] = {}
_pending: set[asyncio.Task] = set()


def enabled() -> bool:
    return bool(get_settings().ops_chat_id)


def is_ops_chat(chat_id: int) -> bool:
    """True for the product-owner group, where `/stats` is open to everyone present."""
    settings = get_settings()
    return bool(settings.ops_chat_id) and chat_id == settings.ops_chat_id


def _thread_id(thread: str) -> int | None:
    settings = get_settings()
    value = {
        THREAD_SALES: settings.ops_thread_sales,
        THREAD_ALERTS: settings.ops_thread_alerts,
        THREAD_DIGESTS: settings.ops_thread_digests,
    }.get(thread, 0)
    return value or None


async def send(text: str, thread: str = THREAD_SALES) -> bool:
    """Deliver one message to the ops group now; returns False when disabled or failed."""
    settings = get_settings()
    application = runtime.get_application()
    if not settings.ops_chat_id or application is None:
        return False
    try:
        await application.bot.send_message(
            settings.ops_chat_id,
            text,
            parse_mode="HTML",
            message_thread_id=_thread_id(thread),
            disable_web_page_preview=True,
        )
        return True
    except Exception as error:
        logger.warning("Ops notification failed: %s", error)
        return False


def notify(text: str, thread: str = THREAD_SALES) -> asyncio.Task | None:
    """Schedule a send in the background; callers never wait on Telegram."""
    if not enabled() or runtime.get_application() is None:
        return None
    task = asyncio.get_running_loop().create_task(send(text, thread))
    _pending.add(task)
    task.add_done_callback(_pending.discard)
    return task


def alert(kind: str, text: str, now: datetime | None = None) -> asyncio.Task | None:
    """Throttled alert: at most one message per `kind` per ALERT_THROTTLE_SECONDS."""
    current = now or datetime.now(UTC)
    last = _last_alert_at.get(kind)
    if last is not None and (current - last).total_seconds() < ALERT_THROTTLE_SECONDS:
        return None
    _last_alert_at[kind] = current
    return notify(f"🔥 <b>{html.escape(kind)}</b>\n{text}", THREAD_ALERTS)


def reset_alert_throttle() -> None:
    _last_alert_at.clear()


# --- event announcements -------------------------------------------------------------


def _display_name(user: User) -> str:
    return html.escape((user.name or "").strip() or "no name")


def _admin_url(user: User) -> str:
    base = get_settings().mini_app_url.rstrip("/")
    return f"{base}/admin/users/{user.id}" if base else ""


def _user_line(user: User) -> str:
    """Who this is, in one line: name as a Telegram profile link, @username, id, language,
    country, plan. The name link opens the profile from the group; the id is what the
    admin panel and logs use."""
    parts = [f'<a href="tg://user?id={user.id}">{_display_name(user)}</a>']
    if user.username:
        parts.append(f"@{html.escape(user.username)}")
    parts.append(f"<code>{user.id}</code>")
    parts.append(html.escape(user.language or "?"))
    if user.country:
        parts.append(html.escape(user.country))
    parts.append(f"plan {billing.effective_plan(user)}")
    return " · ".join(parts)


def _admin_line(user: User) -> str:
    url = _admin_url(user)
    return f'<a href="{html.escape(url)}">admin card</a>' if url else ""


def _age(user: User, now: datetime | None = None) -> int | None:
    if user.birth_date is None:
        return None
    today = (now or datetime.now(UTC)).date()
    years = today.year - user.birth_date.year
    if (today.month, today.day) < (user.birth_date.month, user.birth_date.day):
        years -= 1
    return years


def _days_since_signup(user: User, now: datetime | None = None) -> int | None:
    if user.created_at is None:
        return None
    current = now or datetime.now(UTC)
    created = user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=UTC)
    return max((current - created).days, 0)


def _compose(title: str, user: User, *details: str) -> str:
    lines = [title, _user_line(user), *[d for d in details if d]]
    admin = _admin_line(user)
    if admin:
        lines.append(admin)
    return "\n".join(lines)


def format_user_created(user: User) -> str:
    return _compose("🆕 New user", user)


def format_onboarding_completed(user: User) -> str:
    facts = []
    age = _age(user)
    if age is not None:
        facts.append(f"{age} y.o.")
    if user.gender:
        facts.append(html.escape(user.gender))
    if user.location:
        facts.append(html.escape(user.location[:64]))
    details = [
        " · ".join(facts),
        f"activity: {html.escape(user.activity[:120])}" if user.activity else "",
        f"interests: {html.escape(user.interests[:120])}" if user.interests else "",
        f"goal: {html.escape(user.main_goal[:200])}" if user.main_goal else "",
        f"problem: {html.escape(user.current_problem[:200])}" if user.current_problem else "",
    ]
    return _compose("✅ Onboarding completed", user, *details)


def format_trial_started(user: User) -> str:
    days = _days_since_signup(user)
    until = user.trial_expires_at.date().isoformat() if user.trial_expires_at else "—"
    return _compose(
        "🎯 Trial started",
        user,
        f"day {days} since signup" if days is not None else "",
        f"trial until {until}",
    )


def format_payment_succeeded(
    user: User, *, amount: int, currency: str, renewal: bool, expires_at: datetime | None
) -> str:
    title = "🔁 Subscription renewed" if renewal else "💫 New Pro subscription"
    days = _days_since_signup(user)
    return _compose(
        f"{title} · <b>{amount} {'★' if currency == 'XTR' else html.escape(currency)}</b>",
        user,
        f"day {days} since signup" if days is not None else "",
        f"active until {expires_at.date().isoformat()}" if expires_at is not None else "",
    )


def _pro_until(user: User) -> str:
    return user.pro_expires_at.date().isoformat() if user.pro_expires_at else "—"


def format_subscription_canceled(user: User, *, source: str = "bot") -> str:
    via = " (from Telegram settings)" if source == "telegram" else ""
    return _compose(f"📉 Auto-renew canceled{via}", user, f"Pro active until {_pro_until(user)}")


def format_payment_refunded(
    user: User, *, amount: int, currency: str, source: str, pro_revoked: bool
) -> str:
    unit = "★" if currency == "XTR" else html.escape(currency)
    via = "by Telegram support" if source == "telegram" else "from the admin panel"
    effect = "Pro revoked" if pro_revoked else "entitlement unchanged"
    return _compose(f"↩️ Refund {amount} {unit} {via}", user, effect)


def format_paysupport_request(user: User, text: str, payments: list[BillingPayment]) -> str:
    """/paysupport message. Deliberately carries the user's text: it is addressed to us,
    not to an agent, and the operator cannot act on a payment complaint without it."""
    lines = [f"🛟 Payment support request\n{_user_line(user)}"]
    if _admin_line(user):
        lines.append(_admin_line(user))
    if user.pro_expires_at:
        lines.append(f"pro until {user.pro_expires_at.date().isoformat()}")
    for payment in payments[:3]:
        unit = "★" if payment.currency == "XTR" else html.escape(payment.currency)
        lines.append(
            f"• {payment.created_at.date().isoformat()} {payment.amount} {unit} "
            f"{html.escape(payment.status)} <code>{html.escape(payment.telegram_payment_charge_id)}</code>"
        )
    if not payments:
        lines.append("no payments on record")
    lines.append(f"<blockquote>{html.escape(text[:1000])}</blockquote>")
    return "\n".join(lines)


def format_subscription_restored(user: User) -> str:
    return _compose("🔂 Auto-renew restored", user, f"next charge {_pro_until(user)}")


def format_subscription_payment_failed(user: User) -> str:
    return _compose("⚠️ Renewal charge failed", user, f"Pro active until {_pro_until(user)}")


def user_created(user: User) -> None:
    notify(format_user_created(user))


def onboarding_completed(user: User) -> None:
    notify(format_onboarding_completed(user))


def trial_started(user: User) -> None:
    notify(format_trial_started(user))


def payment_succeeded(
    user: User, *, amount: int, currency: str, renewal: bool, expires_at: datetime | None
) -> None:
    notify(
        format_payment_succeeded(
            user, amount=amount, currency=currency, renewal=renewal, expires_at=expires_at
        )
    )


def subscription_canceled(user: User, *, source: str = "bot") -> None:
    notify(format_subscription_canceled(user, source=source))


def payment_refunded(
    user: User, *, amount: int, currency: str, source: str, pro_revoked: bool
) -> None:
    notify(
        format_payment_refunded(
            user, amount=amount, currency=currency, source=source, pro_revoked=pro_revoked
        )
    )


def paysupport_request(user: User, text: str, payments: list[BillingPayment]) -> None:
    notify(format_paysupport_request(user, text, payments), THREAD_ALERTS)


def subscription_restored(user: User) -> None:
    notify(format_subscription_restored(user))


def subscription_payment_failed(user: User) -> None:
    notify(format_subscription_payment_failed(user))


def format_generation_failed(
    user: User, error: Exception, *, kind: str, agent_id: str = "", mode: str = ""
) -> str:
    """Enough to triage without opening logs: who, which agent and mode, HTTP status."""
    where = " · ".join(p for p in (kind, agent_id, mode) if p)
    status = getattr(error, "status", None)
    status_text = f"HTTP {status} · " if status else ""
    return _compose(
        f"gemini failed · {html.escape(where)}",
        user,
        f"{status_text}{html.escape(type(error).__name__)}: {html.escape(str(error)[:300])}",
    )


def generation_failed(
    kind: str, user: User, error: Exception, *, agent_id: str = "", mode: str = ""
) -> None:
    alert(
        f"gemini:{kind}",
        format_generation_failed(user, error, kind=kind, agent_id=agent_id, mode=mode),
    )


def _broadcast_line(broadcast) -> str:
    audience = broadcast.segment_id and "segment" or "filter"
    return (
        f"“{html.escape(broadcast.title)}” · {broadcast.category} · {audience}"
        f"\n<code>{broadcast.id}</code>"
    )


def broadcast_started(broadcast, recipients: int) -> None:
    notify(
        f"📣 <b>Broadcast started</b>\n{_broadcast_line(broadcast)}\nrecipients: {recipients}",
        THREAD_SALES,
    )


def broadcast_finished(broadcast) -> None:
    notify(
        f"✅ <b>Broadcast sent</b>\n{_broadcast_line(broadcast)}"
        f"\nsent: {broadcast.sent_count} · blocked: {broadcast.blocked_count}"
        f" · failed: {broadcast.failed_count}",
        THREAD_SALES,
    )


def broadcast_failed(broadcast, reason: str) -> None:
    alert(
        "broadcast_failed",
        f"{_broadcast_line(broadcast)}\n{html.escape(reason)}",
    )
