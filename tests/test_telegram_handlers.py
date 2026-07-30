from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.interfaces import RepositoryInterface
from src.application.use_cases import SupportService
from src.domain.models import Ticket
from src.interface.telegram.handlers.assistant import create_router


def make_service() -> MagicMock:
    service = MagicMock(spec=SupportService)
    service.is_assistant = AsyncMock(return_value=True)
    service.take_ticket = AsyncMock()
    service.close_ticket = AsyncMock()
    service.handle_another_question = AsyncMock()
    service.handle_assistant_reply = AsyncMock()
    service.repo = MagicMock(spec=RepositoryInterface)
    service.repo.get_ticket_by_topic = AsyncMock()
    return service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler_index", "callback_data", "method_name", "answer_text"),
    [
        (0, "take:ticket-1", "take_ticket", "Вы взяли тикет в работу."),
        (1, "close:ticket-1", "close_ticket", "Тикет закрыт."),
        (
            2,
            "another:ticket-1",
            "handle_another_question",
            "Тикет закрыт. Попросите клиента написать новый вопрос.",
        ),
    ],
)
async def test_callback_handlers_call_support_service(
    handler_index,
    callback_data,
    method_name,
    answer_text,
):
    service = make_service()
    router = create_router(service)
    callback = SimpleNamespace(
        data=callback_data,
        from_user=SimpleNamespace(id=10, username="helper", full_name="Helper"),
        message=None,
        answer=AsyncMock(),
    )

    await router.callback_query.handlers[handler_index].callback(callback)

    getattr(service, method_name).assert_awaited_once_with("ticket-1", 10, "helper")
    callback.answer.assert_awaited_once_with(answer_text)


@pytest.mark.asyncio
async def test_take_callback_rejects_non_assistant():
    service = make_service()
    service.is_assistant.return_value = False
    router = create_router(service)
    callback = SimpleNamespace(
        data="take:ticket-1",
        from_user=SimpleNamespace(id=10, username="stranger", full_name="Stranger"),
        message=None,
        answer=AsyncMock(),
    )

    await router.callback_query.handlers[0].callback(callback)

    service.take_ticket.assert_not_awaited()
    callback.answer.assert_awaited_once_with(
        "У вас нет прав для этого действия.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_topic_message_forwards_assistant_reply():
    service = make_service()
    service.repo.get_ticket_by_topic.return_value = Ticket(
        ticket_id="ticket-1",
        client_id=20,
        topic_id=30,
    )
    router = create_router(service)
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=10, username="helper", full_name="Helper"),
        message_thread_id=30,
        text="Answer",
        caption=None,
        photo=None,
        document=None,
        audio=None,
        voice=None,
        bot=None,
    )

    await router.message.handlers[0].callback(message)

    service.handle_assistant_reply.assert_awaited_once_with(
        assistant_id=10,
        ticket_id="ticket-1",
        text="Answer",
        username="helper",
        attachments=None,
    )
