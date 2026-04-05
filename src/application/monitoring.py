import asyncio
import logging
from datetime import datetime, time, timezone
import structlog

from src.application.interfaces import BotSenderInterface, RepositoryInterface
from src.domain.models import TicketStatus

logger = structlog.get_logger()

# Working hours: 09:00 - 18:00
WORKING_START = time(9, 0)
WORKING_END = time(18, 0)


def is_working_hours() -> bool:
    now = datetime.now()  # Use local time for working hours check
    current_time = now.time()
    return WORKING_START <= current_time <= WORKING_END


class AlarmService:
    def __init__(self, repo: RepositoryInterface, sender: BotSenderInterface):
        self.repo = repo
        self.sender = sender
        self.log = logger.bind(service="alarm_service")

    async def start_monitoring(self):
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

    async def check_tickets(self):
        active_tickets = await self.repo.get_all_active_tickets()
        now = datetime.now(timezone.utc)
        
        for ticket in active_tickets:
            if not ticket.messages:
                continue
                
            last_msg = ticket.messages[-1]
            # If last message is from client
            if last_msg.sender_id == ticket.client_id:
                diff = now - last_msg.timestamp
                if diff.total_seconds() > 2 * 3600:
                    # Check if we already sent alarm? For now, just send it.
                    # In a real app, we'd add a flag 'alarm_sent'.
                    self.log.info("sending_alarm", ticket_id=ticket.ticket_id)
                    await self.sender.send_to_topic(
                        self.sender.assistants_chat_id,
                        ticket.topic_id,
                        "🚨 ВНИМАНИЕ: На этот вопрос нет ответа уже более 2 часов в рабочее время!"
                    )
