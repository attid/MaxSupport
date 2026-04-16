from unittest.mock import AsyncMock

import pytest

from src.application.monitoring import AlarmService, is_working_hours
from src.domain.models import Ticket, TicketMessage, TicketStatus


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def sender():
    mock = AsyncMock()
    mock.assistants_chat_id = -100123456
    return mock


@pytest.fixture
def alarm_service(repo, sender):
    return AlarmService(repo, sender)


def test_is_working_hours_returns_bool():
    # Just check it returns a bool — actual time depends on when test runs
    result = is_working_hours()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_alarm_sent_once_for_same_ticket(alarm_service, repo, sender):
    """Alarm should be sent only once per ticket, not every minute."""
    client_id = 100
    ticket = Ticket(
        ticket_id="alarm-test",
        client_id=client_id,
        topic_id=555,
        status=TicketStatus.OPEN,
        messages=[
            TicketMessage(sender_id=client_id, text="help"),
        ],
    )
    # Make the message old enough (>2h)
    from datetime import datetime, timedelta, timezone

    ticket.messages[0].timestamp = datetime.now(timezone.utc) - timedelta(hours=3)
    repo.get_all_active_tickets.return_value = [ticket]

    # First check — alarm sent
    await alarm_service.check_tickets()
    sender.send_to_topic.assert_called_once()

    # Second check — alarm NOT sent again
    sender.send_to_topic.reset_mock()
    await alarm_service.check_tickets()
    sender.send_to_topic.assert_not_called()


@pytest.mark.asyncio
async def test_no_alarm_for_recent_message(alarm_service, repo, sender):
    """No alarm if message is recent (<2h)."""
    ticket = Ticket(
        ticket_id="recent-msg",
        client_id=100,
        topic_id=555,
        status=TicketStatus.OPEN,
        messages=[TicketMessage(sender_id=100, text="help")],
    )
    repo.get_all_active_tickets.return_value = [ticket]

    await alarm_service.check_tickets()
    sender.send_to_topic.assert_not_called()


@pytest.mark.asyncio
async def test_no_alarm_for_assistant_reply(alarm_service, repo, sender):
    """No alarm if last message is from assistant."""
    ticket = Ticket(
        ticket_id="assistant-replied",
        client_id=100,
        topic_id=555,
        status=TicketStatus.ASSIGNED,
        assistant_id=200,
        messages=[TicketMessage(sender_id=200, text="here is the answer")],
    )
    repo.get_all_active_tickets.return_value = [ticket]

    await alarm_service.check_tickets()
    sender.send_to_topic.assert_not_called()
