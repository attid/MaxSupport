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
        self.last_update_id = 0
        self._poll_delay = INITIAL_POLL_DELAY
        self.log = logger.bind(service="max_polling")

    async def start_polling(self) -> None:
        self.log.info("starting_max_polling_loop")
        while True:
            try:
                updates = await self.max_sender.get_updates(self.last_update_id)
                for update in updates:
                    await self.process_update(update)
                    uid = update.get("update_id")
                    if uid and uid >= self.last_update_id:
                        self.last_update_id = uid + 1

                # Reset delay on success
                self._poll_delay = INITIAL_POLL_DELAY
            except Exception as e:
                self.log.error("polling_error", error=str(e))
                self._poll_delay = min(self._poll_delay * BACKOFF_FACTOR, MAX_POLL_DELAY)
                self.log.info("backing_off", delay=self._poll_delay)

            await asyncio.sleep(self._poll_delay)

    async def process_update(self, update: dict) -> None:
        message = update.get("message")
        if not message:
            return

        client_id = message.get("from", {}).get("user_id")
        full_name = message.get("from", {}).get("full_name", "Unknown Max User")
        username = message.get("from", {}).get("username")
        text = message.get("text")

        if client_id and text:
            self.log.info("received_new_message", client_id=client_id, text=text)
            await self.support_service.handle_client_message(
                client_id=client_id,
                full_name=full_name,
                username=username,
                text=text,
            )
