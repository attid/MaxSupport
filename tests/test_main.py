import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_cancel_tasks_cancels_and_awaits_background_workers():
    from src.main import cancel_tasks

    started = asyncio.Event()
    finalized = asyncio.Event()

    async def worker() -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            finalized.set()

    task = asyncio.create_task(worker())
    await started.wait()

    await cancel_tasks([task])

    assert task.cancelled()
    assert finalized.is_set()


@pytest.mark.asyncio
async def test_main_disposes_engine_when_repository_initialization_fails(monkeypatch):
    import src.main as main_module

    settings = SimpleNamespace(
        log_format="json",
        db_url="sqlite+aiosqlite:///:memory:",
        telegram_api_url="https://api.telegram.org",
        telegram_bot_token="telegram",
        max_bot_token="max",
        assistants_chat_id=-100,
    )
    engine = MagicMock()
    engine.dispose = AsyncMock()
    repository = MagicMock()
    repository.init_db = AsyncMock(side_effect=RuntimeError("database failed"))

    monkeypatch.setattr(main_module, "load_settings", lambda: settings)
    monkeypatch.setattr(main_module, "configure_logging", lambda log_format: None)
    monkeypatch.setattr(main_module, "create_async_engine", lambda db_url: engine)
    monkeypatch.setattr(main_module, "setup_sqlite_engine", lambda value: None)
    monkeypatch.setattr(main_module, "async_sessionmaker", lambda *args, **kwargs: object())
    monkeypatch.setattr(main_module, "SQLiteRepository", lambda session_factory: repository)

    with pytest.raises(RuntimeError, match="database failed"):
        await main_module.main()

    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_managed_tasks_cancels_workers_when_setup_fails():
    from src.main import managed_tasks

    finalized = asyncio.Event()

    async def worker() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            finalized.set()

    task = None
    with pytest.raises(RuntimeError, match="router failed"):
        async with managed_tasks() as tasks:
            task = asyncio.create_task(worker())
            tasks.append(task)
            await asyncio.sleep(0)
            raise RuntimeError("router failed")

    assert task is not None
    assert task.cancelled()
    assert finalized.is_set()
