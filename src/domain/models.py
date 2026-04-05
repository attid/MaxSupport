from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    CLIENT = "client"
    ASSISTANT = "assistant"


class User(BaseModel):
    user_id: int
    username: Optional[str] = None
    full_name: str
    role: UserRole = UserRole.CLIENT


class TicketStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    CLOSED = "closed"


class TicketMessage(BaseModel):
    sender_id: int
    text: str
    timestamp: datetime = Field(default_factory=utc_now)


class Ticket(BaseModel):
    ticket_id: str
    client_id: int
    assistant_id: Optional[int] = None
    status: TicketStatus = TicketStatus.OPEN
    messages: List[TicketMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
