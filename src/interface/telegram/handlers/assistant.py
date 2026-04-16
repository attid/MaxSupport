import io

from aiogram import F, Router, types

from src.application.use_cases import SupportService
from src.domain.models import Attachment, AttachmentType


def create_router(support_service: SupportService) -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("take:"))
    async def on_take_ticket(callback: types.CallbackQuery):
        ticket_id = callback.data.split(":")[1]

        # Проверка роли
        if not await support_service.is_assistant(callback.from_user.id):
            await callback.answer("У вас нет прав для этого действия.", show_alert=True)
            return

        await support_service.take_ticket(
            ticket_id,
            callback.from_user.id,
            callback.from_user.username or callback.from_user.full_name,
        )
        await callback.answer("Вы взяли тикет в работу.")
        try:
            await callback.message.edit_reply_markup(
                reply_markup=support_service.sender.get_taken_keyboard(
                    ticket_id, callback.from_user.username or callback.from_user.full_name
                )
            )
        except Exception:
            pass

    @router.callback_query(F.data.startswith("close:"))
    async def on_close_ticket(callback: types.CallbackQuery):
        ticket_id = callback.data.split(":")[1]

        if not await support_service.is_assistant(callback.from_user.id):
            await callback.answer("У вас нет прав.", show_alert=True)
            return

        await support_service.close_ticket(
            ticket_id,
            callback.from_user.id,
            callback.from_user.username or callback.from_user.full_name,
        )
        await callback.answer("Тикет закрыт.")

    @router.callback_query(F.data.startswith("another:"))
    async def on_another_question(callback: types.CallbackQuery):
        ticket_id = callback.data.split(":")[1]

        if not await support_service.is_assistant(callback.from_user.id):
            await callback.answer("У вас нет прав.", show_alert=True)
            return

        await support_service.handle_another_question(
            ticket_id,
            callback.from_user.id,
            callback.from_user.username or callback.from_user.full_name,
        )
        await callback.answer("Тикет закрыт. Попросите клиента написать новый вопрос.")

    @router.message(F.message_thread_id)
    async def on_assistant_reply(message: types.Message):
        has_text = bool(message.text or message.caption)
        has_file = bool(message.photo or message.document or message.audio or message.voice)

        if not has_text and not has_file:
            return

        # Проверка роли
        if not await support_service.is_assistant(message.from_user.id):
            return

        # Ищем тикет по topic_id
        ticket = await support_service.repo.get_ticket_by_topic(message.message_thread_id)
        if not ticket:
            return

        text = message.text or message.caption or ""
        username = message.from_user.username or message.from_user.full_name
        attachments = await _extract_tg_attachments(message)

        await support_service.handle_assistant_reply(
            assistant_id=message.from_user.id,
            ticket_id=ticket.ticket_id,
            text=text,
            username=username,
            attachments=attachments or None,
        )

    return router


async def _extract_tg_attachments(message: types.Message) -> list[Attachment]:
    """Download files from TG message, returning Attachment list with raw bytes."""
    bot = message.bot
    attachments: list[Attachment] = []

    if message.photo:
        # Take the largest photo
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        attachments.append(
            Attachment(
                type=AttachmentType.IMAGE,
                url="",  # no URL — we have raw bytes
                filename=f"photo_{photo.file_id}.jpg",
                token=None,
                file_data=buf.getvalue(),
            )
        )

    if message.document:
        file = await bot.get_file(message.document.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        attachments.append(
            Attachment(
                type=AttachmentType.FILE,
                url="",
                filename=message.document.file_name or "document",
                token=None,
                file_data=buf.getvalue(),
            )
        )

    if message.audio:
        file = await bot.get_file(message.audio.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        attachments.append(
            Attachment(
                type=AttachmentType.AUDIO,
                url="",
                filename=message.audio.file_name or "audio",
                token=None,
                file_data=buf.getvalue(),
            )
        )

    if message.voice:
        file = await bot.get_file(message.voice.file_id)
        buf = io.BytesIO()
        await bot.download_file(file.file_path, buf)
        attachments.append(
            Attachment(
                type=AttachmentType.AUDIO,
                url="",
                filename="voice.ogg",
                token=None,
                file_data=buf.getvalue(),
            )
        )

    return attachments
