"""DB-free tests for the admin panel auth: Login Widget signatures and session tokens."""

import hashlib
import hmac
import os

import pytest

from app.core import admin_auth
from app.core.config import get_settings


def sign_widget_payload(payload: dict, bot_token: str | None = None) -> dict:
    token = bot_token or os.environ["BOT_TOKEN"]
    fields = {k: str(v) for k, v in payload.items() if v is not None and k != "hash"}
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hashlib.sha256(token.encode()).digest()
    return payload | {"hash": hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()}


def test_login_widget_payload_roundtrip():
    payload = sign_widget_payload(
        {"id": 42, "first_name": "Ann", "username": "ann", "auth_date": 1_000_000}
    )
    assert admin_auth.validate_login_widget(payload, now=1_000_100) == 42


def test_login_widget_rejects_tampering_and_expiry():
    payload = sign_widget_payload({"id": 42, "first_name": "Ann", "auth_date": 1_000_000})

    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.validate_login_widget(payload | {"id": 43}, now=1_000_100)
    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.validate_login_widget(
            payload, now=1_000_000 + admin_auth.LOGIN_MAX_AGE_SECONDS + 1
        )
    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.validate_login_widget(
            sign_widget_payload(payload, bot_token="other:TOKEN"), now=1_000_100
        )
    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.validate_login_widget({"id": 42, "auth_date": 1_000_000}, now=1_000_100)


def test_session_token_roundtrip_and_expiry():
    token, expires_at = admin_auth.issue_session_token(42, now=1_000_000)

    assert expires_at == 1_000_000 + admin_auth.SESSION_TTL_SECONDS
    assert admin_auth.verify_session_token(token, now=1_000_100) == 42
    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.verify_session_token(token, now=expires_at)


def test_session_token_rejects_forgery(monkeypatch):
    token, _ = admin_auth.issue_session_token(42, now=1_000_000)
    body, _, signature = token.partition(".")

    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.verify_session_token(f"{body}x.{signature}", now=1_000_100)
    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.verify_session_token("garbage", now=1_000_100)

    monkeypatch.setattr(get_settings(), "admin_session_secret", "rotated")
    with pytest.raises(admin_auth.AdminAuthError):
        admin_auth.verify_session_token(token, now=1_000_100)


def test_is_admin_uses_allowlist(monkeypatch):
    monkeypatch.setattr(get_settings(), "ops_admin_ids", "42, 7")

    assert admin_auth.is_admin(42) and admin_auth.is_admin(7)
    assert not admin_auth.is_admin(8) and not admin_auth.is_admin(None)
