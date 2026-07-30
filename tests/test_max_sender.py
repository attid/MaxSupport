from unittest.mock import AsyncMock

import httpx
import pytest

from src.infrastructure.max import MaxSender


@pytest.mark.asyncio
async def test_get_updates_propagates_network_error_for_polling_backoff():
    sender = object.__new__(MaxSender)
    sender._token = "test"
    sender._client = AsyncMock()
    request = httpx.Request("GET", "https://platform-api.max.ru/updates")
    sender._client.get.side_effect = httpx.ConnectError("offline", request=request)

    with pytest.raises(httpx.ConnectError, match="offline"):
        await sender.get_updates(marker=None)
