"""Max API sender — реализация MaxSenderInterface через httpx."""

import httpx
import structlog

from src.application.interfaces import MaxSenderInterface
from src.domain.models import Attachment, AttachmentType

logger = structlog.get_logger()

MAX_API_BASE_URL = "https://platform-api.max.ru"

# Mapping AttachmentType → Max API attachment type string
_ATTACHMENT_TYPE_MAP = {
    AttachmentType.IMAGE: "image",
    AttachmentType.FILE: "file",
    AttachmentType.AUDIO: "file",  # audio sent as file in Max
}


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

    async def upload_file(self, file_data: bytes, filename: str) -> str | None:
        """Upload file to Max: POST /uploads → get URL → PUT file → get token."""
        log = logger.bind(action="upload_file", filename=filename)
        try:
            # Step 1: get upload URL
            r = await self._client.post("/uploads", params={"type": "file"})
            r.raise_for_status()
            upload_url = r.json().get("url")
            if not upload_url:
                log.error("upload_no_url")
                return None

            # Step 2: upload file to the URL
            async with httpx.AsyncClient(timeout=60.0) as tmp:
                r2 = await tmp.post(
                    upload_url,
                    files={"file": (filename, file_data)},
                )
                r2.raise_for_status()
                # Response should contain a token
                token = r2.json().get("token")
                if not token:
                    # Try fileId-based token
                    token = r2.json().get("id")
                log.info("file_uploaded", token=token)
                return token
        except Exception as e:
            log.error("max_api_error", error=str(e))
            return None

    async def send_to_client(
        self, chat_id: int, text: str, attachments: list[Attachment] | None = None
    ) -> int:
        log = logger.bind(action="send_to_client", chat_id=chat_id)
        try:
            body: dict = {}
            if text:
                body["text"] = text
            if attachments:
                body["attachments"] = [
                    {
                        "type": _ATTACHMENT_TYPE_MAP.get(a.type, "file"),
                        "payload": {"token": a.token},
                    }
                    for a in attachments
                    if a.token
                ]
            response = await self._client.post(
                "/messages",
                params={"chat_id": chat_id},
                json=body,
            )
            response.raise_for_status()
            return 0
        except Exception as e:
            log.error("max_api_error", error=str(e))
            return 0
