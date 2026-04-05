"""Application entry point — DI composition root."""

import asyncio
import os

import structlog
from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.max_polling import MaxPollingService
from src.application.monitoring import AlarmService
from src.application.use_cases import SupportService
from src.infrastructure.config import Settings
from src.infrastructure.database import SQLiteRepository, setup_sqlite_engine
from src.infrastructure.max import MaxSender
from src.infrastructure.telegram.bot_sender import BotSender
from src.interface.telegram.handlers import assistant
from src.interface.telegram.middleware import SupportServiceMiddleware

logger = structlog.get_logger()


async def main() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger("INFO"),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    commit_sha = os.getenv("COMMIT_SHA", "unknown")
    log = logger.bind(commit_sha=commit_sha)
    log.info("starting_application")

    # Settings
    settings = Settings()

    # Ensure DB directory exists
    db_path = settings.db_url.replace("sqlite+aiosqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # Database
    engine = create_async_engine(settings.db_url)
    setup_sqlite_engine(engine)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = SQLiteRepository(session_factory)
    await repo.init_db()

    # Telegram bot
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    # DI — wire up interfaces
    sender = BotSender(bot, settings.assistants_chat_id)
    max_sender = MaxSender(token=settings.max_bot_token)
    support_service = SupportService(repo, sender, max_sender)

    # Log bot info
    bot_info = await bot.get_me()
    log.info("telegram_bot_connected", username=bot_info.username, bot_id=bot_info.id)

    max_info = await max_sender.get_me()
    max_username = max_info.get("username") or max_info.get("name", "Unknown")
    log.info("max_bot_connected", username=max_username)

    # Background services
    alarm_service = AlarmService(repo, sender)
    asyncio.create_task(alarm_service.start_monitoring())

    max_polling = MaxPollingService(max_sender, support_service)
    asyncio.create_task(max_polling.start_polling())

    # Middleware & routers
    dp.update.middleware.register(SupportServiceMiddleware(support_service))
    dp.include_routers(assistant.create_router(support_service))

    log.info("starting_telegram_polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
