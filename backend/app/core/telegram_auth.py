"""Validation of Telegram Mini App initData (HMAC-SHA256 per Telegram docs)."""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.core.config import get_settings


class InitDataError(ValueError):
    pass


def validate_init_data(raw_init_data: str) -> dict:
    settings = get_settings()
    if not raw_init_data:
        raise InitDataError("Telegram initData is missing")
    if not settings.telegram_bot_token:
        raise InitDataError("TELEGRAM_BOT_TOKEN is not configured")

    data = dict(parse_qsl(raw_init_data, keep_blank_values=True))
    received_hash = data.pop("hash", "")
    if not received_hash:
        raise InitDataError("Telegram initData hash is missing")

    auth_date = int(data.get("auth_date", "0") or "0")
    if not auth_date or time.time() - auth_date > settings.init_data_max_age:
        raise InitDataError("Telegram initData is expired")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(
        b"WebAppData", settings.telegram_bot_token.encode(), hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise InitDataError("Telegram initData is invalid")

    return data


def extract_telegram_user(init_data: dict) -> dict:
    try:
        user = json.loads(init_data.get("user", "{}"))
    except json.JSONDecodeError as error:
        raise InitDataError("Telegram initData user is malformed") from error
    if not isinstance(user, dict) or not user.get("id"):
        raise InitDataError("Telegram user is missing")
    return user
