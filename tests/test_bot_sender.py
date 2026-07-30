from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from src.domain.models import Attachment, AttachmentType
from src.infrastructure.telegram import bot_sender as bot_sender_module
from src.infrastructure.telegram.bot_sender import BotSender


class FakeHttpClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def get(self, url: str) -> httpx.Response:
        request = httpx.Request("GET", url)
        return httpx.Response(200, content=b"file content", request=request)


@pytest.mark.asyncio
async def test_send_file_to_topic_removes_temporary_file(monkeypatch, tmp_path):
    bot = AsyncMock()
    bot.send_document.return_value = SimpleNamespace(message_id=42)
    monkeypatch.setattr(bot_sender_module, "ATTACHMENTS_DIR", tmp_path)
    monkeypatch.setattr(
        bot_sender_module.httpx,
        "AsyncClient",
        lambda **kwargs: FakeHttpClient(),
    )
    sender = BotSender(bot, assistants_chat_id=-100)
    attachment = Attachment(
        type=AttachmentType.FILE,
        url="https://example.com/document.pdf",
        filename="document.pdf",
    )

    message_id = await sender.send_file_to_topic(-100, 123, attachment)

    assert message_id == 42
    assert list(tmp_path.iterdir()) == []
