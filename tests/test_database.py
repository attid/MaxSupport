from datetime import UTC

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.domain.models import Ticket, TicketMessage, User
from src.infrastructure.database import SQLiteRepository, setup_sqlite_engine


@pytest.mark.asyncio
async def test_sqlite_repository_round_trip_preserves_ticket_contract(tmp_path):
    database_path = tmp_path / "repository.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    setup_sqlite_engine(engine)
    repository = SQLiteRepository(async_sessionmaker(engine, expire_on_commit=False))

    try:
        await repository.init_db()
        await repository.save_user(User(user_id=10, full_name="Client"))
        ticket = Ticket(
            ticket_id="ticket-1",
            client_id=10,
            topic_id=20,
            messages=[TicketMessage(sender_id=10, text="Help")],
        )
        await repository.save_ticket(ticket)
        await repository.save_message_mapping(30, ticket.ticket_id)

        restored = await repository.get_ticket(ticket.ticket_id)

        assert restored is not None
        assert restored.created_at.tzinfo is UTC
        assert restored.messages[0].timestamp.tzinfo is not None
        assert await repository.get_ticket_by_topic(20) == restored
        assert await repository.get_ticket_id_by_message(30) == ticket.ticket_id
    finally:
        await engine.dispose()
