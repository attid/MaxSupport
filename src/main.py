"""Application entry point — DI composition root."""

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.monitoring import AlarmService
from src.application.use_cases import SupportService
from src.infrastructure.config import Settings
from src.infrastructure.database import SQLiteRepository, setup_sqlite_engine
from src.infrastructure.logging import configure_logging
from src.infrastructure.max import MaxSender
from src.infrastructure.telegram.bot_sender import BotSender
from src.interface.max.polling import MaxPollingService
from src.interface.telegram.handlers import assistant
from src.interface.telegram.middleware import SupportServiceMiddleware

logger = structlog.get_logger()


def load_settings() -> Settings:
    # BaseSettings obtains required values from the process environment.
    return Settings()  # pyright: ignore[reportCallIssue]


async def cancel_tasks(tasks: list[asyncio.Task[None]]) -> None:
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


@asynccontextmanager
async def managed_tasks() -> AsyncIterator[list[asyncio.Task[None]]]:
    tasks: list[asyncio.Task[None]] = []
    try:
        yield tasks
    finally:
        await cancel_tasks(tasks)


async def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_format)

    commit_sha = os.getenv("COMMIT_SHA", "unknown")
    log = logger.bind(commit_sha=commit_sha)
    log.info("starting_application")

    # Ensure DB directory exists
    db_path = settings.db_url.replace("sqlite+aiosqlite:///", "")
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncExitStack() as resources:
        engine = create_async_engine(settings.db_url)
        setup_sqlite_engine(engine)
        resources.push_async_callback(engine.dispose)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        repo = SQLiteRepository(session_factory)
        await repo.init_db()

        api_server = TelegramAPIServer.from_base(settings.telegram_api_url)
        session = AiohttpSession(api=api_server)
        resources.push_async_callback(session.close)
        bot = Bot(token=settings.telegram_bot_token, session=session)
        dp = Dispatcher()

        sender = BotSender(bot, settings.assistants_chat_id)
        max_sender = MaxSender(token=settings.max_bot_token)
        resources.push_async_callback(max_sender.close)
        support_service = SupportService(repo, sender, max_sender)

        async with managed_tasks() as background_tasks:
            bot_info = await bot.get_me()
            log.info("telegram_bot_connected", username=bot_info.username, bot_id=bot_info.id)

            max_info = await max_sender.get_me()
            max_username = max_info.get("username") or max_info.get("name", "Unknown")
            log.info("max_bot_connected", username=max_username)

            alarm_service = AlarmService(repo, sender)
            background_tasks.append(asyncio.create_task(alarm_service.start_monitoring()))

            max_polling = MaxPollingService(max_sender, support_service)
            background_tasks.append(asyncio.create_task(max_polling.start_polling()))

            dp.update.middleware.register(SupportServiceMiddleware(support_service))
            dp.include_routers(assistant.create_router(support_service))

            log.info("starting_telegram_polling")
            await dp.start_polling(bot, close_bot_session=False)
            log.info("stopping_application")


if __name__ == "__main__":
    asyncio.run(main())
