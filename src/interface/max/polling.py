import asyncio

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

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


class _MaxAttachmentPayload(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    url: str = ""
    token: str | None = None
    mid: str | int | None = None
    id: str | int | None = None


class _MaxAttachment(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    type: str
    payload: _MaxAttachmentPayload = Field(default_factory=_MaxAttachmentPayload)
    filename: str | None = None

    @model_validator(mode="after")
    def supported_attachment_has_download_url(self) -> "_MaxAttachment":
        if self.type in SUPPORTED_ATTACHMENT_TYPES and not self.payload.url:
            raise ValueError("supported attachment requires payload.url")
        return self


class _MaxBody(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    text: str | None = None
    attachments: list[_MaxAttachment] = Field(default_factory=list)


class _MaxSender(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    user_id: int
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None


class _MaxRecipient(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    chat_id: int | None = None


class _MaxMessage(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    sender: _MaxSender
    body: _MaxBody = Field(default_factory=_MaxBody)
    recipient: _MaxRecipient = Field(default_factory=_MaxRecipient)
    chat_id: int | None = None


class _MaxUpdate(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)

    update_type: str
    message: _MaxMessage


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
                await self.process_updates(updates)

                # Reset delay on success
                self._poll_delay = INITIAL_POLL_DELAY
            except Exception as e:
                self.log.error("polling_error", error=str(e))
                self._poll_delay = min(self._poll_delay * BACKOFF_FACTOR, MAX_POLL_DELAY)
                self.log.info("backing_off", delay=self._poll_delay)

            await asyncio.sleep(self._poll_delay)

    async def process_updates(self, updates: list[dict]) -> None:
        for index, update in enumerate(updates):
            try:
                await self.process_update(update)
            except Exception as error:
                self.log.error(
                    "update_processing_error",
                    update_index=index,
                    error_type=type(error).__name__,
                    error=str(error),
                )

    async def process_update(self, update: dict) -> None:
        if update.get("update_type") != "message_created":
            return

        try:
            parsed = _MaxUpdate.model_validate(update)
        except ValidationError as error:
            self.log.warning("invalid_max_update", validation_errors=error.error_count())
            return

        message = parsed.message
        sender = message.sender
        client_id = sender.user_id
        first_name = sender.first_name
        last_name = sender.last_name or ""
        full_name = f"{first_name} {last_name}".strip() or "Unknown Max User"
        username = sender.username
        body = message.body
        text = body.text

        # chat_id from recipient
        chat_id = message.recipient.chat_id or message.chat_id

        # Parse attachments
        attachments: list[Attachment] = []
        has_unsupported = False

        for att in body.attachments:
            att_type = att.type
            if att_type in SUPPORTED_ATTACHMENT_TYPES:
                payload = att.payload
                filename = att.filename or _default_filename(
                    att_type,
                    {"mid": payload.mid, "id": payload.id},
                )
                attachments.append(
                    Attachment(
                        type=AttachmentType(att_type),
                        url=payload.url,
                        filename=filename,
                        token=payload.token,
                    )
                )
            else:
                has_unsupported = True

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
