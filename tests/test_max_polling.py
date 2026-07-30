from unittest.mock import AsyncMock

import pytest

from src.application.use_cases import SupportService
from src.domain.models import AttachmentType
from src.interface.max.polling import MaxPollingService


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
            "sender": {
                "user_id": 123,
                "first_name": "Max",
                "last_name": "User",
                "username": "maxuser",
            },
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
        attachments=[],
    )


@pytest.mark.asyncio
async def test_process_update_with_image_attachment(polling, support_service):
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123, "first_name": "Igor"},
            "body": {
                "text": "",
                "attachments": [
                    {
                        "type": "image",
                        "payload": {"url": "https://example.com/photo.jpg", "token": "img_tok"},
                    }
                ],
            },
            "recipient": {"chat_id": 456},
        },
    }

    await polling.process_update(update)

    call_args = support_service.handle_client_message.call_args
    atts = call_args.kwargs["attachments"]
    assert len(atts) == 1
    assert atts[0].type == AttachmentType.IMAGE
    assert atts[0].url == "https://example.com/photo.jpg"
    assert atts[0].token == "img_tok"
    assert atts[0].filename.endswith(".jpg")


@pytest.mark.asyncio
async def test_process_update_unsupported_attachment_replies(polling, support_service, max_sender):
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123, "first_name": "Igor"},
            "body": {"text": "", "attachments": [{"type": "sticker", "payload": {}}]},
            "recipient": {"chat_id": 456},
        },
    }

    await polling.process_update(update)

    support_service.handle_client_message.assert_not_called()
    max_sender.send_to_client.assert_called_once()
    assert "не поддерживается" in max_sender.send_to_client.call_args.args[1]


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
async def test_process_update_ignores_no_text_no_attachments(polling, support_service):
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
async def test_process_update_rejects_non_integer_sender_id(polling, support_service):
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": "123", "first_name": "User"},
            "body": {"text": "Hello"},
        },
    }

    await polling.process_update(update)

    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_update_ignores_malformed_attachments(polling, support_service):
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123, "first_name": "User"},
            "body": {"attachments": {"type": "image"}},
        },
    }

    await polling.process_update(update)

    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_update_rejects_attachment_without_download_url(polling, support_service):
    update = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 123, "first_name": "User"},
            "body": {
                "attachments": [
                    {
                        "type": "image",
                        "payload": {},
                    }
                ]
            },
        },
    }

    await polling.process_update(update)

    support_service.handle_client_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_updates_continues_after_one_update_fails(polling, support_service):
    updates = [
        {
            "update_type": "message_created",
            "message": {
                "sender": {"user_id": 1, "first_name": "First"},
                "body": {"text": "first"},
            },
        },
        {
            "update_type": "message_created",
            "message": {
                "sender": {"user_id": 2, "first_name": "Second"},
                "body": {"text": "second"},
            },
        },
    ]
    support_service.handle_client_message.side_effect = [RuntimeError("failed"), None]

    await polling.process_updates(updates)

    assert support_service.handle_client_message.await_count == 2


@pytest.mark.asyncio
async def test_poll_delay_resets_on_success(polling, max_sender):
    from src.interface.max.polling import INITIAL_POLL_DELAY

    max_sender.get_updates.return_value = (
        [
            {
                "update_type": "message_created",
                "message": {"sender": {"user_id": 1, "first_name": "U"}, "body": {"text": "hi"}},
            }
        ],
        42,
    )

    updates, new_marker = await max_sender.get_updates(None)
    for update in updates:
        await polling.process_update(update)
    polling._marker = new_marker

    assert polling._marker == 42
    assert polling._poll_delay == INITIAL_POLL_DELAY
