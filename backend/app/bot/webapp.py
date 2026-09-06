"""Mini App URL and chat menu button helpers."""

from urllib.parse import urlencode

from telegram import Bot, MenuButtonWebApp, WebAppInfo

from app.core.config import get_settings
from app.i18n import t

VIEW_PATHS = {"home": "", "calendar": "calendar", "profile": "profile"}


def build_webapp_url(view: str = "home", **params: str) -> str:
    """Deep link into the Mini App: `/calendar?tab=goal`, `/profile?sheet=pro`, ...

    The frontend router owns these paths (frontend/src/router.tsx); `?view=` links
    from older messages are still understood there.
    """
    settings = get_settings()
    base = settings.mini_app_url.rstrip("/")
    if not base:
        return ""
    url = f"{base}/{VIEW_PATHS.get(view, view)}"
    query = urlencode({key: value for key, value in params.items() if value})
    return f"{url}?{query}" if query else url


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
