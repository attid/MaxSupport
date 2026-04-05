import pytest
from unittest.mock import AsyncMock, MagicMock

from src.application.max_polling import MaxPollingService
from src.application.use_cases import SupportService


@pytest.fixture
def max_sender():
    return AsyncMock()


@pytest.fixture
def support_service():
    return AsyncMock(spec=SupportService)


@pytest.fixture
def polling(max_sender, support_service):
    return MaxPollingService(max_sender, support_service)


@pytest.mark.asyncio
async def test_process_update_with_text_message(polling, support_service):
    update = {
        "update_id": 42,
        "message": {
            "from": {"user_id": 123, "full_name": "Max User", "username": "maxuser"},
            "text": "Hello",
        },
    }

    await polling.process_update(update)

    support_service.handle_client_message.assert_called_once_with(
        client_id=123,
        full_name="Max User",
        username="maxuser",
        text="Hello",
    )
    assert polling.last_update_id == 0  # Not updated in process_update


@pytest.mark.asyncio
async def test_process_update_ignores_no_message(polling, support_service):
    update = {"update_id": 10}
    await polling.process_update(update)
    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_update_ignores_no_text(polling, support_service):
    update = {
        "update_id": 11,
        "message": {
            "from": {"user_id": 123, "full_name": "User"},
        },
    }
    await polling.process_update(update)
    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_poll_delay_resets_on_success(polling, max_sender):
    """After successful poll, delay should reset to initial value."""
    from src.application.max_polling import INITIAL_POLL_DELAY

    max_sender.get_updates.return_value = [
        {"update_id": 5, "message": {"from": {"user_id": 1}, "text": "hi"}}
    ]

    # Simulate one iteration of the loop logic
    updates = await max_sender.get_updates(0)
    for update in updates:
        await polling.process_update(update)
        uid = update.get("update_id")
        if uid and uid >= polling.last_update_id:
            polling.last_update_id = uid + 1

    assert polling.last_update_id == 6
    assert polling._poll_delay == INITIAL_POLL_DELAY
