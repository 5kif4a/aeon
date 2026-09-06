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


def is_ops_request(chat_id: int, user_id: int | None) -> bool:
    """`/stats` is served in the ops group and privately to listed admins only."""
    settings = get_settings()
    if settings.ops_chat_id and chat_id == settings.ops_chat_id:
        return True
    return user_id is not None and user_id in settings.ops_admin_id_list


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


def _user_line(user: User) -> str:
    parts = [f"<code>{user.id}</code>", html.escape(user.language or "?")]
    if user.country:
        parts.append(html.escape(user.country))
    parts.append(f"plan {billing.effective_plan(user)}")
    return " · ".join(parts)


def _days_since_signup(user: User, now: datetime | None = None) -> int | None:
    if user.created_at is None:
        return None
    current = now or datetime.now(UTC)
    created = user.created_at if user.created_at.tzinfo else user.created_at.replace(tzinfo=UTC)
    return max((current - created).days, 0)


def format_user_created(user: User) -> str:
    return f"🆕 New user\n{_user_line(user)}"


def format_onboarding_completed(user: User) -> str:
    lines = [f"✅ Onboarding completed\n{_user_line(user)}"]
    if user.main_goal:
        lines.append(f"goal: {html.escape(user.main_goal[:200])}")
    if user.activity:
        lines.append(f"activity: {html.escape(user.activity[:120])}")
    return "\n".join(lines)


def format_trial_started(user: User) -> str:
    days = _days_since_signup(user)
    suffix = f" · day {days} since signup" if days is not None else ""
    return f"🎯 Trial started\n{_user_line(user)}{suffix}"


def format_payment_succeeded(
    user: User, *, amount: int, currency: str, renewal: bool, expires_at: datetime | None
) -> str:
    title = "🔁 Subscription renewed" if renewal else "💫 New Pro subscription"
    lines = [f"{title} · <b>{amount} {'★' if currency == 'XTR' else html.escape(currency)}</b>"]
    lines.append(_user_line(user))
    days = _days_since_signup(user)
    if days is not None:
        lines.append(f"day {days} since signup")
    if expires_at is not None:
        lines.append(f"active until {expires_at.date().isoformat()}")
    return "\n".join(lines)


def _pro_until(user: User) -> str:
    return user.pro_expires_at.date().isoformat() if user.pro_expires_at else "—"


def format_subscription_canceled(user: User, *, source: str = "bot") -> str:
    via = " (from Telegram settings)" if source == "telegram" else ""
    return f"📉 Auto-renew canceled{via}\n{_user_line(user)}\nPro active until {_pro_until(user)}"


def format_payment_refunded(
    user: User, *, amount: int, currency: str, source: str, pro_revoked: bool
) -> str:
    unit = "★" if currency == "XTR" else html.escape(currency)
    via = "by Telegram support" if source == "telegram" else "from the admin panel"
    effect = "Pro revoked" if pro_revoked else "entitlement unchanged"
    return f"↩️ Refund {amount} {unit} {via}\n{_user_line(user)}\n{effect}"


def format_paysupport_request(user: User, text: str, payments: list[BillingPayment]) -> str:
    """/paysupport message. Deliberately carries the user's text: it is addressed to us,
    not to an agent, and the operator cannot act on a payment complaint without it."""
    lines = [f"🛟 Payment support request\n{_user_line(user)}"]
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
    return f"🔂 Auto-renew restored\n{_user_line(user)}\nnext charge {_pro_until(user)}"


def format_subscription_payment_failed(user: User) -> str:
    return f"⚠️ Renewal charge failed\n{_user_line(user)}\nPro active until {_pro_until(user)}"


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


def generation_failed(kind: str, user_id: int, error: Exception) -> None:
    alert(
        f"gemini:{kind}",
        f"user <code>{user_id}</code>: {html.escape(type(error).__name__)}: "
        f"{html.escape(str(error)[:300])}",
    )
