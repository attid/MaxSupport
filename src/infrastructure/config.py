from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values are loaded from process environment variables.
    """

    telegram_bot_token: str
    max_bot_token: str
    assistants_chat_id: int
    db_url: str = "sqlite+aiosqlite:///./data.db"
    telegram_api_url: str = "https://api.telegram.org"
    log_format: Literal["json", "console"] = "json"

    model_config = SettingsConfigDict(
        extra="ignore",
    )
