"""FastAPI application: Mini App API + Telegram bot (webhook or polling) + static frontend."""

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
from app.bot.application import build_application
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/tg/webhook"
_webhook_secret = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _webhook_secret
    settings = get_settings()

    application = None
    if settings.bot_token:
        application = build_application()
        await application.initialize()
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
                allowed_updates=Update.ALL_TYPES,
            )
            await application.start()
            logger.info("Telegram bot started in webhook mode")
        else:
            await application.bot.delete_webhook(drop_pending_updates=False)
            await application.start()
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram bot started in polling mode")
    else:
        logger.warning("BOT_TOKEN is not set; running API without the bot")

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


@app.post(WEBHOOK_PATH, include_in_schema=False)
async def telegram_webhook(request: Request) -> Response:
    application = runtime.get_application()
    if application is None:
        raise HTTPException(status_code=503, detail="Bot is not running")
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != _webhook_secret:
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
