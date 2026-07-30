from aiogram.client.telegram import TelegramAPIServer

from src.infrastructure.config import DEFAULT_TELEGRAM_API_URL, Settings


def make_settings(telegram_api_url: str) -> Settings:
    return Settings(
        telegram_bot_token="telegram-token",
        max_bot_token="max-token",
        assistants_chat_id=-100,
        telegram_api_url=telegram_api_url,
    )


def test_empty_telegram_api_url_uses_official_server():
    settings = make_settings("")

    assert settings.telegram_api_url == DEFAULT_TELEGRAM_API_URL


def test_whitespace_telegram_api_url_uses_official_server():
    settings = make_settings("   ")

    assert settings.telegram_api_url == DEFAULT_TELEGRAM_API_URL


def test_missing_telegram_api_url_uses_official_server():
    settings = Settings(
        telegram_bot_token="telegram-token",
        max_bot_token="max-token",
        assistants_chat_id=-100,
    )

    assert settings.telegram_api_url == DEFAULT_TELEGRAM_API_URL


def test_custom_telegram_api_url_builds_method_and_file_endpoints():
    settings = make_settings("https://api.mtlminiapps.us")

    api_server = TelegramAPIServer.from_base(settings.telegram_api_url)

    assert api_server.api_url("TOKEN", "getMe") == "https://api.mtlminiapps.us/botTOKEN/getMe"
    assert (
        api_server.file_url("TOKEN", "documents/report.pdf")
        == "https://api.mtlminiapps.us/file/botTOKEN/documents/report.pdf"
    )
