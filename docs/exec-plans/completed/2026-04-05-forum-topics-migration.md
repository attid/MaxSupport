# Plan: Migration to Telegram Forum Topics with Interactive Support

## Context
Goal: Improve support organization by creating a new topic for each client question in a forum-enabled Telegram group.
Visual indicators: 🔴 (New), 🟡 (Taken), 🟢 (Closed).
Interactive: "Take", "Close", "Another Question" buttons.
Monitoring: Alarm if no response in 2 hours during working hours (9-18).

## 1. Domain & Data Changes
- **models.py**: 
    - Update `Ticket` to include `topic_id: Optional[int]`, `taken_by: Optional[int]`, `taken_at: Optional[datetime]`.
    - Update `TicketStatus` (add `TAKEN` if needed, or use existing `ASSIGNED`).
- **database.py**: 
    - Update SQLAlchemy models `TicketTable` with `topic_id`, `taken_by`, `taken_at`.
    - Implement methods to find ticket by `topic_id`.

## 2. Infrastructure & Communication
- **interfaces.py**: Add methods to `BotSenderInterface`:
    - `create_forum_topic(chat_id: int, name: str) -> int` (returns thread_id)
    - `edit_forum_topic(chat_id: int, thread_id: int, name: str) -> None`
    - `send_to_topic(chat_id: int, thread_id: int, text: str, reply_markup: Any = None) -> int` (returns message_id)
- **main.py / BotSender**: Implement these methods using `aiogram` (e.g., `bot.create_forum_topic`).

## 3. Application Logic (SupportService)
- **use_cases.py**:
    - Update `handle_client_message`:
        - If new ticket: create topic (🔴 NEW), send initial message with "Take" button.
        - If existing ticket: send to topic with "Close" / "Another Question" buttons.
    - Implement `take_ticket(ticket_id, assistant_id)`:
        - Update status to `ASSIGNED`.
        - Rename topic (🟡 TAKEN).
        - Update buttons on the message (change "Take" to "Taken by @username").
    - Implement `close_ticket(ticket_id, assistant_id)`:
        - Update status to `CLOSED`.
        - Rename topic (🟢 CLOSED by @username).
        - Notify client.
    - Implement `handle_another_question(ticket_id)`:
        - Close current ticket.
        - Mark message as "redirected" or just create a new one (as if client sent a new message).

## 4. Background Monitoring (Alarm)
- Create `src/application/monitoring.py`:
    - Simple async loop that checks tickets with status `OPEN`.
    - Logic for "Working Hours" (9-18).
    - Threshold: 2 hours without assistant message.
    - Send "ALARM: Question forgotten" to the topic.

## 5. UI / Handlers
- **assistant.py**:
    - Callback handlers for "Take", "Close", "Another Question".
- **client.py**:
    - Update to use new `SupportService` logic.

## Risks & Open Questions
- Group forum settings: The bot must be an admin in `assistants_chat_id` with permissions to manage topics.
- Thread ID management: In aiogram, `message_thread_id` is used in `send_message`.
- "Another question" flow: Should it close the topic completely or just mark it? (User: "creates a new theme").

## Verification
- Unit tests for new service logic.
- Manual verification of topic creation/renaming.
- Alarm service log check.
