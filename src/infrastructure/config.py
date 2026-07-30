from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_TELEGRAM_API_URL = "https://api.telegram.org"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values are loaded from process environment variables.
    """

    telegram_bot_token: str
    max_bot_token: str
    assistants_chat_id: int
    db_url: str = "sqlite+aiosqlite:///./data.db"
    telegram_api_url: str = DEFAULT_TELEGRAM_API_URL
    log_format: Literal["json", "console"] = "json"

    model_config = SettingsConfigDict(
        extra="ignore",
    )

    @field_validator("telegram_api_url", mode="before")
    @classmethod
    def normalize_telegram_api_url(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or DEFAULT_TELEGRAM_API_URL
        return value
