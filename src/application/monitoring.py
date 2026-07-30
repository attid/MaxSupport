import asyncio
from datetime import UTC, datetime, time

import structlog

from src.application.interfaces import BotSenderInterface, RepositoryInterface

logger = structlog.get_logger()

# Working hours: 09:00 - 18:00 MSK (UTC+3)
WORKING_START = time(6, 0)  # 09:00 MSK = 06:00 UTC
WORKING_END = time(15, 0)  # 18:00 MSK = 15:00 UTC


def is_working_hours() -> bool:
    now = datetime.now(UTC)
    current_time = now.time()
    return WORKING_START <= current_time <= WORKING_END


class AlarmService:
    def __init__(self, repo: RepositoryInterface, sender: BotSenderInterface):
        self.repo = repo
        self.sender = sender
        self._alarmed_tickets: set[str] = set()
        self.log = logger.bind(service="alarm_service")

    async def start_monitoring(self) -> None:
        self.log.info("starting_monitoring_loop")
        while True:
            try:
                if is_working_hours():
                    await self.check_tickets()
                else:
                    self.log.debug("outside_working_hours")
            except Exception as e:
                self.log.error("monitoring_error", error=str(e))

            await asyncio.sleep(60)  # Check every minute

    async def check_tickets(self) -> None:
        active_tickets = await self.repo.get_all_active_tickets()
        now = datetime.now(UTC)

        for ticket in active_tickets:
            if not ticket.messages:
                continue
            if ticket.topic_id is None:
                self.log.warning("ticket_without_topic", ticket_id=ticket.ticket_id)
                continue

            last_msg = ticket.messages[-1]
            # Only alarm if last message is from client and ticket is not yet alarmed
            if (
                last_msg.sender_id == ticket.client_id
                and (now - last_msg.timestamp).total_seconds() > 2 * 3600
                and ticket.ticket_id not in self._alarmed_tickets
            ):
                self.log.info("sending_alarm", ticket_id=ticket.ticket_id)
                await self.sender.send_to_topic(
                    self.sender.assistants_chat_id,
                    ticket.topic_id,
                    "🚨 ВНИМАНИЕ: На этот вопрос нет ответа уже более 2 часов в рабочее время!",
                )
                self._alarmed_tickets.add(ticket.ticket_id)
