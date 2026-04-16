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
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123, "first_name": "Max", "last_name": "User", "username": "maxuser"},
            "body": {"text": "Hello"},
            "recipient": {"chat_id": 456},
        },
    }

    await polling.process_update(update)

    support_service.handle_client_message.assert_called_once_with(
        client_id=123,
        full_name="Max User",
        username="maxuser",
        text="Hello",
        max_chat_id=456,
    )


@pytest.mark.asyncio
async def test_process_update_ignores_non_message_created(polling, support_service):
    update = {"update_type": "bot_started"}
    await polling.process_update(update)
    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_update_ignores_no_message(polling, support_service):
    update = {"update_type": "message_created"}
    await polling.process_update(update)
    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_update_ignores_no_text(polling, support_service):
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123, "first_name": "User"},
            "body": {},
        },
    }
    await polling.process_update(update)
    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_poll_delay_resets_on_success(polling, max_sender):
    """After successful poll, delay should reset to initial value."""
    from src.application.max_polling import INITIAL_POLL_DELAY

    max_sender.get_updates.return_value = (
        [{"update_type": "message_created", "message": {"sender": {"user_id": 1, "first_name": "U"}, "body": {"text": "hi"}}}],
        42,
    )

    updates, new_marker = await max_sender.get_updates(None)
    for update in updates:
        await polling.process_update(update)
    polling._marker = new_marker

    assert polling._marker == 42
    assert polling._poll_delay == INITIAL_POLL_DELAY
