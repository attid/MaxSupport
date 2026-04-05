from src.domain.models import User, UserRole, Ticket, TicketMessage, TicketStatus


def test_user_creation():
    """Test basic user creation with default role."""
    user = User(user_id=123, full_name="Test User")
    assert user.user_id == 123
    assert user.full_name == "Test User"
    assert user.role == UserRole.CLIENT


def test_user_with_optional_fields():
    """Test user creation with optional username."""
    user = User(
        user_id=456,
        full_name="John Doe",
        username="johndoe",
        role=UserRole.ASSISTANT,
    )
    assert user.username == "johndoe"
    assert user.role == UserRole.ASSISTANT


def test_ticket_default_status():
    """Test that new ticket has OPEN status by default."""
    ticket = Ticket(ticket_id="test-123", client_id=1)
    assert ticket.status == TicketStatus.OPEN
    assert len(ticket.messages) == 0


def test_ticket_message_has_timestamp():
    """Test that ticket message has auto-generated timestamp."""
    msg = TicketMessage(sender_id=1, text="Hello")
    assert msg.timestamp is not None
    assert msg.timestamp.tzinfo is not None  # Should be timezone-aware


def test_ticket_messages_list():
    """Test adding messages to ticket."""
    ticket = Ticket(ticket_id="test-456", client_id=1)
    assert len(ticket.messages) == 0

    msg = TicketMessage(sender_id=1, text="Hi")
    ticket.messages.append(msg)
    assert len(ticket.messages) == 1
    assert ticket.messages[0].text == "Hi"


def test_ticket_status_transitions():
    """Test ticket status changes."""
    ticket = Ticket(ticket_id="test-789", client_id=1)
    assert ticket.status == TicketStatus.OPEN

    ticket.status = TicketStatus.ASSIGNED
    assert ticket.status == TicketStatus.ASSIGNED

    ticket.status = TicketStatus.CLOSED
    assert ticket.status == TicketStatus.CLOSED


def test_ticket_assign_assistant():
    """Test assigning an assistant to ticket."""
    ticket = Ticket(ticket_id="test-assign", client_id=1)
    assert ticket.assistant_id is None

    ticket.assistant_id = 999
    ticket.status = TicketStatus.ASSIGNED
    assert ticket.assistant_id == 999
    assert ticket.status == TicketStatus.ASSIGNED
