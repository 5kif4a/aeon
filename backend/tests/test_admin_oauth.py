"""DB-free tests for the Telegram OAuth (OIDC) admin login."""

import base64
import hashlib
import json
from urllib.parse import parse_qs, urlparse

import pytest

from app.core import admin_oauth
from app.core.admin_auth import AdminAuthError
from app.core.config import get_settings

CLIENT_ID = "7521690978"


@pytest.fixture
def configured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "telegram_oauth_client_id", CLIENT_ID)
    monkeypatch.setattr(settings, "telegram_oauth_client_secret", "secret")
    monkeypatch.setattr(
        settings, "admin_oauth_redirect_uri", "https://panel.example/admin/callback"
    )
    admin_oauth._pending.clear()
    yield settings
    admin_oauth._pending.clear()


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_id_token(**claims) -> str:
    payload = {
        "iss": admin_oauth.ISSUER,
        "aud": CLIENT_ID,
        "sub": "1234123412341234123",
        "exp": 1_000_600,
        "id": 42,
        "name": "Ann",
        "preferred_username": "ann",
    } | claims
    return f"{_b64url(b'{}')}.{_b64url(json.dumps(payload).encode())}.signature"


def test_is_configured_needs_every_part(monkeypatch, configured):
    assert admin_oauth.is_configured()
    monkeypatch.setattr(configured, "telegram_oauth_client_secret", "")
    assert not admin_oauth.is_configured()


def test_redirect_uri_falls_back_to_the_mini_app_origin(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_oauth_redirect_uri", "")
    monkeypatch.setattr(settings, "mini_app_url", "https://panel.example/")

    assert settings.admin_oauth_redirect_uri_resolved == "https://panel.example/admin/callback"


def test_begin_login_builds_a_pkce_request(configured):
    url, state = admin_oauth.begin_login(now=1_000_000)
    query = {key: value[0] for key, value in parse_qs(urlparse(url).query).items()}

    assert url.startswith(admin_oauth.AUTHORIZE_URL)
    assert query["client_id"] == CLIENT_ID
    assert query["redirect_uri"] == "https://panel.example/admin/callback"
    assert query["response_type"] == "code"
    assert query["scope"] == admin_oauth.SCOPE
    assert query["code_challenge_method"] == "S256"
    assert query["state"] == state

    verifier = admin_oauth._pending[state].verifier
    assert query["code_challenge"] == _b64url(hashlib.sha256(verifier.encode()).digest())


def test_begin_login_requires_configuration(monkeypatch, configured):
    monkeypatch.setattr(configured, "telegram_oauth_client_id", "")
    with pytest.raises(AdminAuthError):
        admin_oauth.begin_login()


async def test_state_is_single_use_and_expires(configured):
    _, state = admin_oauth.begin_login(now=1_000_000)
    admin_oauth._take_pending(state, 1_000_100)
    with pytest.raises(AdminAuthError):
        admin_oauth._take_pending(state, 1_000_100)

    _, state = admin_oauth.begin_login(now=1_000_000)
    with pytest.raises(AdminAuthError):
        admin_oauth._take_pending(state, 1_000_000 + admin_oauth.STATE_TTL_SECONDS + 1)

    with pytest.raises(AdminAuthError):
        await admin_oauth.complete_login("code", "never-issued", now=1_000_100)


def test_decode_id_token_reads_the_telegram_user_id(configured):
    identity = admin_oauth.decode_id_token(make_id_token(), now=1_000_000)

    assert identity.user_id == 42
    assert identity.name == "Ann"
    assert identity.username == "ann"


def test_decode_id_token_rejects_bad_tokens(configured):
    for token in (
        make_id_token(iss="https://evil.example"),
        make_id_token(aud="999"),
        make_id_token(exp=1_000_000),
        make_id_token(id=None),
        "not-a-jwt",
    ):
        with pytest.raises(AdminAuthError):
            admin_oauth.decode_id_token(token, now=1_000_000)


def test_decode_id_token_accepts_an_audience_list(configured):
    identity = admin_oauth.decode_id_token(make_id_token(aud=["other", CLIENT_ID]), now=1_000_000)

    assert identity.user_id == 42
