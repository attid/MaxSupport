# Plan: Enhance Reliability and Security of MaxSupport

## Context
Based on the project review, several areas for improvement were identified: security of assistant handlers, error handling in the application layer, and the fragility of ticket ID extraction from message text.

## Plan of Changes
1. [ ] **Security**: Add a check for the `ASSISTANT` role in `src/interface/telegram/handlers/assistant.py`.
2. [ ] **Error Handling**: 
    - Add `structlog` for structured logging in `SupportService`.
    - Handle cases where tickets or users are not found with proper logging and/or exceptions.
3. [ ] **Tests**: Create `tests/test_application.py` to test `SupportService` using mocks for repository and sender.
4. [ ] **Robustness**: 
    - Update `RepositoryInterface` to include a way to map Telegram message IDs to Ticket IDs.
    - Update `BotSender` to return the message ID after notifying assistants.
    - Update `on_assistant_reply` to use the message mapping instead of regex parsing (if possible) or at least make regex more robust.

## Risks and Open Questions
- Changing the ticket ID extraction might require a database schema change to store `message_id -> ticket_id` mapping. 
- *Decision*: For now, I will start with Security, Logging, and Tests. If we decide to change the mapping logic, I'll create a separate ADR.

## Verification
- Run `just check` (lint + test).
- New tests in `tests/test_application.py` must pass with 100% coverage for the service.
- Manual verification of the bot's behavior (if environment allows).
