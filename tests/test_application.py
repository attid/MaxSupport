from unittest.mock import ANY, AsyncMock

import pytest

from src.application.interfaces import BotSenderInterface, MaxSenderInterface, RepositoryInterface
from src.application.use_cases import SupportService
from src.domain.models import Ticket, TicketStatus, User


@pytest.fixture
def repo():
    return AsyncMock(spec=RepositoryInterface)


@pytest.fixture
def sender():
    mock = AsyncMock(spec=BotSenderInterface)
    mock.assistants_chat_id = -100123456
    return mock


@pytest.fixture
def max_sender():
    return AsyncMock(spec=MaxSenderInterface)


@pytest.fixture
def service(repo, sender, max_sender):
    return SupportService(repo, sender, max_sender)


@pytest.mark.asyncio
async def test_handle_client_message_new_user_and_ticket(service, repo, sender):
    # Setup
    client_id = 123
    repo.get_user.return_value = None
    repo.get_active_ticket_by_client.return_value = None
    sender.create_forum_topic.return_value = 999
    sender.send_to_topic.return_value = 1000

    # Act
    await service.handle_client_message(
        client_id=client_id, full_name="Test Client", username="testclient", text="Help me"
    )

    # Assert
    repo.save_user.assert_called_once()
    repo.save_ticket.assert_called_once()
    sender.create_forum_topic.assert_called_once()
    sender.send_to_topic.assert_called_once()
    repo.save_message_mapping.assert_called_once_with(1000, ANY)

    # Check ticket creation
    ticket = repo.save_ticket.call_args[0][0]
    assert ticket.client_id == client_id
    assert ticket.topic_id == 999
    assert len(ticket.messages) == 1


@pytest.mark.asyncio
async def test_handle_client_message_existing_ticket(service, repo, sender):
    # Setup
    client_id = 123
    existing_ticket = Ticket(ticket_id="old-ticket", client_id=client_id, topic_id=999)
    repo.get_user.return_value = User(user_id=client_id, full_name="Test Client")
    repo.get_active_ticket_by_client.return_value = existing_ticket
    sender.send_to_topic.return_value = 2000

    # Act
    await service.handle_client_message(
        client_id=client_id, full_name="Test Client", text="Second message"
    )

    # Assert
    repo.save_user.assert_not_called()
    repo.save_ticket.assert_called_once()
    sender.create_forum_topic.assert_not_called()
    sender.send_to_topic.assert_called_once()

    assert len(existing_ticket.messages) == 1
    assert existing_ticket.messages[0].text == "Second message"


@pytest.mark.asyncio
async def test_take_ticket_success(service, repo, sender):
    # Setup
    ticket_id = "test-uuid"
    ticket = Ticket(ticket_id=ticket_id, client_id=123, topic_id=999, status=TicketStatus.OPEN)
    repo.get_ticket.return_value = ticket

    # Act
    await service.take_ticket(ticket_id, 888, "assistant_user")

    # Assert
    assert ticket.status == TicketStatus.ASSIGNED
    assert ticket.assistant_id == 888
    assert ticket.taken_at is not None
    repo.save_ticket.assert_called_once()
    sender.edit_forum_topic.assert_called_once()


@pytest.mark.asyncio
async def test_close_ticket_success(service, repo, sender, max_sender):
    # Setup
    ticket_id = "test-uuid"
    ticket = Ticket(ticket_id=ticket_id, client_id=123, topic_id=999)
    repo.get_ticket.return_value = ticket

    # Act
    result = await service.close_ticket(ticket_id, 888, "assistant_user")

    # Assert
    assert result is True
    assert ticket.status == TicketStatus.CLOSED
    repo.save_ticket.assert_called_once()
    sender.edit_forum_topic.assert_called_once()
    max_sender.send_to_client.assert_called_once()


@pytest.mark.asyncio
async def test_is_assistant(service, sender):
    # Member of assistants chat → True
    sender.is_chat_member.return_value = True
    assert await service.is_assistant(1) is True
    sender.is_chat_member.assert_called_with(sender.assistants_chat_id, 1)

    # Not a member → False
    sender.is_chat_member.return_value = False
    assert await service.is_assistant(2) is False
