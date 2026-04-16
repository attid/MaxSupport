import asyncio

import structlog

from src.application.interfaces import MaxSenderInterface
from src.application.use_cases import SupportService

logger = structlog.get_logger()

INITIAL_POLL_DELAY = 1.0
MAX_POLL_DELAY = 60.0
BACKOFF_FACTOR = 2.0


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

        # chat_id from recipient or directly from message
        recipient = message.get("recipient", {})
        chat_id = recipient.get("chat_id") or message.get("chat_id")

        if client_id and text:
            self.log.info("received_new_message", client_id=client_id, chat_id=chat_id, text=text)
            await self.support_service.handle_client_message(
                client_id=client_id,
                full_name=full_name,
                username=username,
                text=text,
                max_chat_id=chat_id,
            )
