"""Mini App URL and chat menu button helpers."""

from urllib.parse import urlencode

from telegram import Bot, MenuButtonWebApp, WebAppInfo

from app.core.config import get_settings
from app.i18n import t


def build_webapp_url(view: str = "home") -> str:
    settings = get_settings()
    base = settings.mini_app_url
    if not base:
        return ""
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{urlencode({'view': view})}"


async def set_chat_menu_button(bot: Bot, chat_id: int, language: str = "en") -> None:
    url = build_webapp_url()
    if not url:
        return
    try:
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonWebApp(
                text=t(language, "chat_menu_button"), web_app=WebAppInfo(url=url)
            ),
        )
    except Exception:
        pass
