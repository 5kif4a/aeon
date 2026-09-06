"""Admin authentication for the product-owner panel.

Two ways in, one allowlist (`OPS_ADMIN_IDS`):
- inside Telegram the Mini App keeps sending `Authorization: tma <initData>`;
- in a plain browser the Telegram Login Widget returns a payload signed with
  SHA256(bot_token); we verify it and issue a short-lived HMAC session token that the
  frontend sends as `Authorization: admin <token>`.
"""

import base64
import hashlib
import hmac
import json
import time

from app.core.config import get_settings

# Login Widget payloads are single-use in practice; reject anything older than this.
LOGIN_MAX_AGE_SECONDS = 300
SESSION_TTL_SECONDS = 7 * 24 * 3600
_WIDGET_FIELDS = ("id", "first_name", "last_name", "username", "photo_url", "auth_date")


class AdminAuthError(ValueError):
    pass


def is_admin(user_id: int | None) -> bool:
    return user_id is not None and user_id in get_settings().ops_admin_id_list


def validate_login_widget(payload: dict, now: float | None = None) -> int:
    """Verify a Telegram Login Widget payload and return the Telegram user id."""
    settings = get_settings()
    if not settings.bot_token:
        raise AdminAuthError("BOT_TOKEN is not configured")
    received_hash = str(payload.get("hash") or "")
    if not received_hash:
        raise AdminAuthError("Telegram login hash is missing")

    fields = {
        key: str(payload[key])
        for key in _WIDGET_FIELDS
        if payload.get(key) is not None and payload.get(key) != ""
    }
    try:
        auth_date = int(fields.get("auth_date", "0"))
        user_id = int(fields.get("id", "0"))
    except ValueError as error:
        raise AdminAuthError("Telegram login payload is malformed") from error
    if not user_id:
        raise AdminAuthError("Telegram user is missing")
    current = now if now is not None else time.time()
    if not auth_date or current - auth_date > LOGIN_MAX_AGE_SECONDS:
        raise AdminAuthError("Telegram login is expired")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hashlib.sha256(settings.bot_token.encode()).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise AdminAuthError("Telegram login is invalid")
    return user_id


def _session_key() -> bytes:
    settings = get_settings()
    if settings.admin_session_secret:
        return settings.admin_session_secret.encode()
    # Derived key so the panel works without extra configuration; rotating BOT_TOKEN
    # invalidates sessions, which is the desired behavior anyway.
    return hmac.new(b"AdminSession", settings.bot_token.encode(), hashlib.sha256).digest()


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_session_token(user_id: int, now: float | None = None) -> tuple[str, int]:
    """Return (token, expires_at_unix) for an allowlisted admin."""
    current = int(now if now is not None else time.time())
    expires_at = current + SESSION_TTL_SECONDS
    body = _b64encode(json.dumps({"uid": user_id, "exp": expires_at}).encode())
    signature = hmac.new(_session_key(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}", expires_at


def verify_session_token(token: str, now: float | None = None) -> int:
    """Return the admin user id encoded in a valid, unexpired token."""
    body, _, signature = (token or "").partition(".")
    if not body or not signature:
        raise AdminAuthError("Admin session token is malformed")
    expected = hmac.new(_session_key(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise AdminAuthError("Admin session token is invalid")
    try:
        claims = json.loads(_b64decode(body))
        user_id = int(claims["uid"])
        expires_at = int(claims["exp"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise AdminAuthError("Admin session token is malformed") from error
    current = now if now is not None else time.time()
    if current >= expires_at:
        raise AdminAuthError("Admin session token is expired")
    return user_id
