import asyncio

import structlog

from src.application.interfaces import MaxSenderInterface
from src.application.use_cases import SupportService
from src.domain.models import Attachment, AttachmentType

logger = structlog.get_logger()

INITIAL_POLL_DELAY = 1.0
MAX_POLL_DELAY = 60.0
BACKOFF_FACTOR = 2.0

SUPPORTED_ATTACHMENT_TYPES = {"image", "file", "audio"}

_DEFAULT_EXTENSIONS = {
    "image": "jpg",
    "audio": "mp3",
    "file": "bin",
}


def _default_filename(att_type: str, payload: dict) -> str:
    """Generate a readable filename for attachments without one."""
    ext = _DEFAULT_EXTENSIONS.get(att_type, "bin")
    mid = payload.get("mid") or payload.get("id") or "attachment"
    return f"{att_type}_{mid}.{ext}"


class MaxPollingService:
    def __init__(self, max_sender: MaxSenderInterface, support_service: SupportService):
        self.max_sender = max_sender
        self.support_service = support_service
        self._marker: int | None = None
        self._poll_delay = INITIAL_POLL_DELAY
        self.log = logger.bind(service="max_polling")

    async def start_polling(self) -> None:
        self.log.info("starting_max_polling_loop")
        while True:
            try:
                updates, new_marker = await self.max_sender.get_updates(self._marker)
                if new_marker is not None:
                    self._marker = new_marker
                for update in updates:
                    await self.process_update(update)

                # Reset delay on success
                self._poll_delay = INITIAL_POLL_DELAY
            except Exception as e:
                self.log.error("polling_error", error=str(e))
                self._poll_delay = min(self._poll_delay * BACKOFF_FACTOR, MAX_POLL_DELAY)
                self.log.info("backing_off", delay=self._poll_delay)

            await asyncio.sleep(self._poll_delay)

    async def process_update(self, update: dict) -> None:
        if update.get("update_type") != "message_created":
            return

        message = update.get("message")
        if not message:
            return

        sender = message.get("sender", {})
        client_id = sender.get("user_id")
        first_name = sender.get("first_name", "")
        last_name = sender.get("last_name") or ""
        full_name = f"{first_name} {last_name}".strip() or "Unknown Max User"
        username = sender.get("username")
        body = message.get("body", {})
        text = body.get("text") if isinstance(body, dict) else message.get("text")

        # chat_id from recipient
        recipient = message.get("recipient", {})
        chat_id = recipient.get("chat_id") or message.get("chat_id")

        # Parse attachments
        raw_attachments = body.get("attachments", []) if isinstance(body, dict) else []
        attachments: list[Attachment] = []
        has_unsupported = False

        for att in raw_attachments:
            att_type = att.get("type", "")
            if att_type in SUPPORTED_ATTACHMENT_TYPES:
                payload = att.get("payload", {})
                filename = att.get("filename") or _default_filename(att_type, payload)
                attachments.append(
                    Attachment(
                        type=AttachmentType(att_type),
                        url=payload.get("url", ""),
                        filename=filename,
                        token=payload.get("token"),
                    )
                )
            else:
                has_unsupported = True

        if not client_id:
            return

        # Reply about unsupported format if there's nothing useful
        if has_unsupported and not attachments and not text:
            self.log.info("unsupported_attachment", client_id=client_id)
            if chat_id:
                await self.max_sender.send_to_client(
                    chat_id,
                    "Формат сообщения не поддерживается. "
                    "Пожалуйста, отправьте текст, фото, файл или аудио.",
                )
            return

        if text or attachments:
            self.log.info(
                "received_new_message",
                client_id=client_id,
                chat_id=chat_id,
                text=text,
                attachments_count=len(attachments),
            )
            await self.support_service.handle_client_message(
                client_id=client_id,
                full_name=full_name,
                username=username,
                text=text or "",
                max_chat_id=chat_id,
                attachments=attachments,
            )
