import asyncio
import structlog
from src.application.interfaces import MaxSenderInterface
from src.application.use_cases import SupportService

logger = structlog.get_logger()


class MaxPollingService:
    def __init__(self, max_sender: MaxSenderInterface, support_service: SupportService):
        self.max_sender = max_sender
        self.support_service = support_service
        self.last_update_id = 0
        self.log = logger.bind(service="max_polling")

    async def start_polling(self):
        self.log.info("starting_max_polling_loop")
        while True:
            try:
                updates = await self.max_sender.get_updates(self.last_update_id)
                for update in updates:
                    await self.process_update(update)
                    # Update the last_update_id to avoid processing same update again
                    # Assuming update has an 'update_id' field
                    uid = update.get("update_id")
                    if uid and uid >= self.last_update_id:
                        self.last_update_id = uid + 1
            except Exception as e:
                self.log.error("polling_error", error=str(e))
            
            await asyncio.sleep(1)  # Wait 1 second between polls

    async def process_update(self, update: dict):
        # Assuming update contains a 'message' field with 'from', 'text', etc.
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
                text=text
            )
