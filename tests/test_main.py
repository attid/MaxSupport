import asyncio

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
