"""FastAPI application: Mini App API + Telegram bot (webhook or polling) + static frontend."""

import hmac
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from telegram import Update

from app.api.routes import api_router
from app.bot import runtime
from app.bot.application import ALLOWED_UPDATES, build_application, configure_commands
from app.core.config import get_settings
from app.services import bot_settings, ops

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/tg/webhook"
_webhook_secret = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _webhook_secret
    settings = get_settings()

    # Prompts and generation knobs live in the DB; a failure here only keeps code defaults.
    await bot_settings.refresh_safely()

    application = None
    if settings.bot_token:
        application = build_application()
        await application.initialize()
        await configure_commands(application)
        runtime.set_application(application)

        if settings.bot_mode == "webhook":
            webhook_base_url = settings.webhook_base_url or settings.mini_app_url
            if not webhook_base_url:
                raise RuntimeError(
                    "BOT_MODE=webhook requires WEBHOOK_BASE_URL (or MINI_APP_URL) to be set"
                )
            _webhook_secret = settings.webhook_secret or secrets.token_urlsafe(32)
            await application.bot.set_webhook(
                url=f"{webhook_base_url.rstrip('/')}{WEBHOOK_PATH}",
                secret_token=_webhook_secret,
                allowed_updates=ALLOWED_UPDATES,
            )
            await application.start()
            logger.info("Telegram bot started in webhook mode")
        else:
            await application.bot.delete_webhook(drop_pending_updates=False)
            await application.start()
            await application.updater.start_polling(allowed_updates=ALLOWED_UPDATES)
            logger.info("Telegram bot started in polling mode")
    else:
        logger.warning("BOT_TOKEN is not set; running API without the bot")

    # One message per process start: the limits this environment actually runs with.
    ops.settings_drift(settings.funnel_overrides())

    if settings.bot_mode == "webhook" and not settings.admin_session_secret:
        logger.warning(
            "ADMIN_SESSION_SECRET is not set; admin sessions are signed with a key derived "
            "from BOT_TOKEN"
        )

    yield

    if application is not None:
        if settings.bot_mode != "webhook" and application.updater:
            await application.updater.stop()
        await application.stop()
        await application.shutdown()
        runtime.set_application(None)


app = FastAPI(title="aeon", lifespan=lifespan)

_cors_origins = get_settings().cors_origin_list
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router)


def _webhook_authorized(header: str | None) -> bool:
    """True only when a secret is configured and the header matches it.

    In polling mode no secret exists, so the endpoint must refuse everything: an empty
    header would otherwise equal the empty secret and let anyone queue forged updates
    (a fake `successful_payment` would grant Pro).
    """
    if not _webhook_secret or header is None:
        return False
    return hmac.compare_digest(header, _webhook_secret)


@app.post(WEBHOOK_PATH, include_in_schema=False)
async def telegram_webhook(request: Request) -> Response:
    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Bot is not running")
    if not _webhook_authorized(request.headers.get("X-Telegram-Bot-Api-Secret-Token")):
        raise HTTPException(status_code=403, detail="Invalid secret token")
    update = Update.de_json(await request.json(), application.bot)
    await application.update_queue.put(update)
    return Response(status_code=204)


@app.get("/api/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}


_static_dir = get_settings().static_dir
if _static_dir and Path(_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="frontend")
