from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    assistants_chat_id: int
    db_url: str = "sqlite+aiosqlite:///./data.db"

    # Файл .env подгружается только если он существует.
    # В проде переменные берутся напрямую из окружения.
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )


config = Settings()
