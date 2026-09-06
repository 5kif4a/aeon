from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""
    bot_username: str = ""
    bot_mode: str = "polling"  # polling | webhook
    webhook_secret: str = ""
    # Public HTTPS URL of the Mini App frontend (Vercel). Also allowed by CORS.
    mini_app_url: str = ""
    # Public HTTPS URL of this backend (Railway domain). Used for the Telegram
    # webhook; falls back to mini_app_url when the frontend is served by the backend.
    webhook_base_url: str = ""
    # Extra browser origins allowed by CORS (CSV), in addition to mini_app_url.
    # Needed when the frontend is hosted separately (e.g. Vercel).
    cors_origins: str = ""

    database_url: str = "postgresql+asyncpg://aeon:aeon@localhost:5432/aeon"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = 2500

    rag_enabled: bool = True
    rag_allow_basic: bool = False
    pro_price_stars: int = 350
    free_daily_questions: int = 3
    trial_days: int = 7
    trial_daily_rag_questions: int = 5
    trial_total_rag_questions: int = 35
    pro_daily_rag_questions: int = 30
    pro_daily_council_questions: int = 3
    rag_data_dir: str = "data/rag"
    rag_top_k: int = 4

    reminder_hour: int = 9
    reminder_tz: str = "UTC"
    init_data_max_age: int = 172_800

    # Product-owner notifications: a Telegram group (negative chat id) that receives
    # sales/user events, alerts and periodic digests. Empty/0 disables everything.
    ops_chat_id: int = 0
    # Optional forum-topic ids inside the ops group; 0 sends to the general chat.
    ops_thread_sales: int = 0
    ops_thread_alerts: int = 0
    ops_thread_digests: int = 0
    # Telegram user ids (CSV) allowed to run /stats in a private chat with the bot.
    ops_admin_ids: str = ""
    # Local hour (in ops_tz, defaults to reminder_tz) at which digests are sent.
    ops_digest_hour: int = 9
    ops_tz: str = ""
    # Signs browser admin sessions (Telegram Login Widget flow). Empty derives a key
    # from BOT_TOKEN.
    admin_session_secret: str = ""
    # Telegram OAuth 2.0 / OIDC credentials from BotFather (Bot Settings -> Web Login).
    # The client id is the bot id; the secret is not BOT_TOKEN.
    telegram_oauth_client_id: str = ""
    telegram_oauth_client_secret: str = ""
    # Must match one of the Web Login allowed URLs in BotFather. Defaults to the
    # panel callback on the Mini App origin.
    admin_oauth_redirect_uri: str = ""

    web_port: int = 5173
    static_dir: str = ""  # path to built frontend (frontend/dist); empty disables static serving

    @property
    def cors_origin_list(self) -> list[str]:
        """Allowed browser origins: mini_app_url plus any CORS_ORIGINS entries."""
        origins: list[str] = []
        for value in (self.mini_app_url, *self.cors_origins.split(",")):
            origin = value.strip().rstrip("/")
            if origin and origin not in origins:
                origins.append(origin)
        return origins

    @property
    def ops_admin_id_list(self) -> list[int]:
        ids: list[int] = []
        for value in self.ops_admin_ids.split(","):
            value = value.strip()
            if value.lstrip("-").isdigit():
                ids.append(int(value))
        return ids

    @property
    def admin_oauth_redirect_uri_resolved(self) -> str:
        if self.admin_oauth_redirect_uri:
            return self.admin_oauth_redirect_uri
        base = self.mini_app_url.rstrip("/")
        return f"{base}/admin/callback" if base else ""

    @property
    def ops_timezone(self) -> str:
        return self.ops_tz or self.reminder_tz or "UTC"

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
