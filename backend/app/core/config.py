from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str = ""
    bot_username: str = ""
    bot_mode: str = "polling"  # polling | webhook
    webhook_secret: str = ""
    webapp_url: str = ""
    # Public HTTPS URL of this backend (Railway domain). Used for the Telegram
    # webhook; falls back to webapp_url when the frontend is served by the backend.
    public_url: str = ""
    # Extra browser origins allowed by CORS (CSV), in addition to webapp_url.
    # Needed when the frontend is hosted separately (e.g. Vercel).
    cors_origins: str = ""

    database_url: str = "postgresql+asyncpg://aeon:aeon@localhost:5432/aeon"
    redis_url: str = ""
    redis_agent_history_ttl: int = 2_592_000

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = 2500

    reminder_hour: int = 9
    reminder_tz: str = "UTC"
    init_data_max_age: int = 172_800

    web_port: int = 5173
    static_dir: str = ""  # path to built frontend (frontend/dist); empty disables static serving

    @property
    def cors_origin_list(self) -> list[str]:
        """Allowed browser origins: webapp_url plus any CORS_ORIGINS entries."""
        origins: list[str] = []
        for value in (self.webapp_url, *self.cors_origins.split(",")):
            origin = value.strip().rstrip("/")
            if origin and origin not in origins:
                origins.append(origin)
        return origins

    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
