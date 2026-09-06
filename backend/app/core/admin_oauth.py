"""Telegram OAuth 2.0 / OpenID Connect sign-in for the product-owner panel.

Telegram archived the iframe Login Widget in favour of an OIDC provider at
`oauth.telegram.org` (discovery: `/.well-known/openid-configuration`). BotFather
issues the credentials under Bot Settings -> Web Login: the client id is the bot
id, the client secret is separate from `BOT_TOKEN`, and the redirect URI has to
be allowlisted there as well.

The panel runs on the Mini App origin, not on this backend, so the browser only
carries `code` + `state` back here and the confidential exchange happens
server-side. What comes out is the Telegram user id, which
`admin_auth.is_admin` then checks against `OPS_ADMIN_IDS` exactly like the
widget flow did.
"""

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass

import httpx

from app.core.admin_auth import AdminAuthError
from app.core.config import get_settings

ISSUER = "https://oauth.telegram.org"
AUTHORIZE_URL = f"{ISSUER}/auth"
TOKEN_URL = f"{ISSUER}/token"
# The panel needs an identity and a display name, nothing else; `phone` stays unrequested.
SCOPE = "openid profile"
# How long a started login may stay unfinished. Telegram codes are short-lived anyway.
STATE_TTL_SECONDS = 600
TOKEN_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class OAuthIdentity:
    user_id: int
    name: str
    username: str


@dataclass(frozen=True)
class _Pending:
    verifier: str
    redirect_uri: str
    expires_at: float


# In-process, like the JobQueue: the backend runs as a single instance. A redeploy
# in the middle of a login simply asks the admin to press the button again.
_pending: dict[str, _Pending] = {}


def is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.telegram_oauth_client_id
        and settings.telegram_oauth_client_secret
        and settings.admin_oauth_redirect_uri_resolved
    )


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _prune(now: float) -> None:
    for state, pending in list(_pending.items()):
        if pending.expires_at <= now:
            del _pending[state]


def begin_login(now: float | None = None) -> tuple[str, str]:
    """Return (authorize_url, state) for a fresh PKCE login."""
    if not is_configured():
        raise AdminAuthError("Telegram OAuth is not configured")
    settings = get_settings()
    current = now if now is not None else time.time()
    _prune(current)

    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    redirect_uri = settings.admin_oauth_redirect_uri_resolved
    _pending[state] = _Pending(
        verifier=verifier, redirect_uri=redirect_uri, expires_at=current + STATE_TTL_SECONDS
    )

    query = httpx.QueryParams(
        {
            "client_id": settings.telegram_oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPE,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"{AUTHORIZE_URL}?{query}", state


def _take_pending(state: str, now: float) -> _Pending:
    _prune(now)
    pending = _pending.pop(state, None)
    if pending is None:
        raise AdminAuthError("Login request is unknown or expired")
    return pending


def decode_id_token(id_token: str, now: float | None = None) -> OAuthIdentity:
    """Read the identity out of an id_token received straight from the token endpoint.

    The signature is not re-checked: the token arrives over TLS from Telegram's
    token endpoint in response to a client-authenticated request, which OIDC Core
    3.1.3.7 accepts in place of verifying it against the JWKS. Everything that is
    not covered by the transport - issuer, audience, expiry - is checked here.
    """
    current = now if now is not None else time.time()
    parts = (id_token or "").split(".")
    if len(parts) != 3:
        raise AdminAuthError("Telegram returned a malformed id_token")
    try:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))
    except (ValueError, json.JSONDecodeError) as error:
        raise AdminAuthError("Telegram returned a malformed id_token") from error

    if payload.get("iss") != ISSUER:
        raise AdminAuthError("id_token was issued by someone else")
    audience = payload.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if str(get_settings().telegram_oauth_client_id) not in {str(item) for item in audiences}:
        raise AdminAuthError("id_token was issued for another client")
    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError) as error:
        raise AdminAuthError("id_token has no usable expiry") from error
    if expires_at <= current:
        raise AdminAuthError("id_token is expired")

    # `sub` is an opaque pairwise identifier; the numeric Telegram user id - the one
    # the bot and `OPS_ADMIN_IDS` speak - is the separate `id` claim.
    try:
        user_id = int(payload["id"])
    except (KeyError, TypeError, ValueError) as error:
        raise AdminAuthError("id_token carries no Telegram user id") from error

    username = str(payload.get("preferred_username") or "")
    name = str(payload.get("name") or payload.get("given_name") or username or "")
    return OAuthIdentity(user_id=user_id, name=name[:64], username=username)


async def complete_login(code: str, state: str, now: float | None = None) -> OAuthIdentity:
    """Exchange an authorization code for an identity, consuming the pending state."""
    if not is_configured():
        raise AdminAuthError("Telegram OAuth is not configured")
    if not code:
        raise AdminAuthError("Authorization code is missing")
    settings = get_settings()
    current = now if now is not None else time.time()
    pending = _take_pending(state, current)

    try:
        async with httpx.AsyncClient(timeout=TOKEN_TIMEOUT_SECONDS) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": pending.redirect_uri,
                    "client_id": settings.telegram_oauth_client_id,
                    "code_verifier": pending.verifier,
                },
                auth=(settings.telegram_oauth_client_id, settings.telegram_oauth_client_secret),
                headers={"Accept": "application/json"},
            )
    except httpx.HTTPError as error:
        raise AdminAuthError("Telegram did not answer the token request") from error

    if response.status_code != 200:
        raise AdminAuthError(f"Telegram rejected the login ({response.status_code})")
    try:
        id_token = str(response.json()["id_token"])
    except (ValueError, KeyError, TypeError) as error:
        raise AdminAuthError("Telegram returned no id_token") from error
    return decode_id_token(id_token, now=current)
