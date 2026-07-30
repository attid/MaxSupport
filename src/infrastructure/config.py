from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Environment variables take precedence. Optional .env file can be used
    for local development (not used in production).
    """

    telegram_bot_token: str
    max_bot_token: str
    assistants_chat_id: int
    db_url: str = "sqlite+aiosqlite:///./data.db"
    telegram_api_url: str = "https://api.telegram.org"
    log_format: Literal["json", "console"] = "json"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        env_file_encoding="utf-8",
    )
