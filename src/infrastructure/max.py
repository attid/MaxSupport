"""Max API sender — реализация MaxSenderInterface через httpx."""

import httpx
import structlog

from src.application.interfaces import MaxSenderInterface

logger = structlog.get_logger()

MAX_API_BASE_URL = "https://platform-api.max.ru"


class MaxSender(MaxSenderInterface):
    def __init__(self, token: str):
        self._token = token
        self._client = httpx.AsyncClient(
            base_url=MAX_API_BASE_URL,
            headers={"Authorization": token},
            timeout=60.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_me(self) -> dict:
        log = logger.bind(action="get_me")
        try:
            response = await self._client.get("/me")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            log.error("max_api_error", error=str(e))
            return {}

    async def get_updates(self, marker: int | None) -> tuple[list[dict], int | None]:
        log = logger.bind(action="get_updates", marker=marker)
        try:
            params: dict = {"limit": 100, "timeout": 30}
            if marker is not None:
                params["marker"] = marker
            response = await self._client.get("/updates", params=params)
            response.raise_for_status()
            data = response.json()
            updates = data.get("updates", [])
            new_marker = data.get("marker")
            return updates, new_marker
        except Exception as e:
            log.error("max_api_error", error=str(e))
            return [], marker

    async def send_to_client(self, chat_id: int, text: str) -> int:
        log = logger.bind(action="send_to_client", chat_id=chat_id)
        try:
            response = await self._client.post(
                "/messages",
                json={"chat_id": chat_id, "text": text},
            )
            response.raise_for_status()
            res_data = response.json()
            return res_data.get("message_id", 0)
        except Exception as e:
            log.error("max_api_error", error=str(e))
            return 0
