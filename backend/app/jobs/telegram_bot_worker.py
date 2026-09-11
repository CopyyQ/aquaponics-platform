from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.db.session import async_session_factory
from app.services.telegram_bot_query_service import (
    list_authorized_projects,
    project_picker_keyboard,
    render_project_view,
    telegram_action_keyboard,
)
from app.services.telegram_notifier import TelegramNotifier

logger = logging.getLogger(__name__)


def parse_callback_data(value: object) -> tuple[str, int] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(":")
    if len(parts) == 2 and parts[0] in {"a", "s", "m"}:
        view, project = parts
    elif len(parts) == 3 and parts[0] == "r" and parts[1] in {"a", "s"}:
        _, view, project = parts
    else:
        return None
    try:
        project_id = int(project)
    except ValueError:
        return None
    return (view, project_id) if project_id > 0 else None


async def _handle_callback(notifier: TelegramNotifier, callback: dict[str, Any]) -> None:
    callback_id = str(callback.get("id") or "")
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    message_id = message.get("message_id")
    parsed = parse_callback_data(callback.get("data"))
    if not callback_id or not chat_id or not isinstance(message_id, int) or parsed is None:
        if callback_id:
            await notifier.answer_callback_query(callback_id, text="Yêu cầu không hợp lệ")
        return
    view, project_id = parsed
    async with async_session_factory() as db:
        if view == "m":
            projects = await list_authorized_projects(db, chat_id)
            project = next((item for item in projects if item.id == project_id), None)
            if project is None:
                await notifier.answer_callback_query(callback_id, text="Bạn không có quyền xem hệ thống này")
                return
            text = f"🌿 AQUAPONICS\n\nHệ thống: {project.name} ({project.code})\nChọn thông tin cần xem."
            keyboard = telegram_action_keyboard(project.id)
        else:
            rendered = await render_project_view(
                db, chat_id=chat_id, project_id=project_id, view=view
            )
            if rendered is None:
                await notifier.answer_callback_query(callback_id, text="Bạn không có quyền xem hệ thống này")
                return
            text, keyboard = rendered

    await notifier.answer_callback_query(callback_id)
    result = await notifier.edit_message_text(
        chat_id, message_id, text, reply_markup=keyboard
    )
    if not result.sent:
        logger.warning(
            "event=telegram_callback_edit_failed chat_id=%s category=%s",
            chat_id,
            result.error_category,
        )


async def _handle_message(notifier: TelegramNotifier, message: dict[str, Any]) -> None:
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    text = str(message.get("text") or "").strip().lower()
    if not chat_id or text not in {"/start", "/menu", "/alerts", "/status"}:
        return

    async with async_session_factory() as db:
        projects = await list_authorized_projects(db, chat_id)
        if not projects:
            await notifier.send_message(chat_id, "⛔ Chat này chưa được cấp quyền xem hệ thống Aquaponics.")
            return
        if text in {"/alerts", "/status"} and len(projects) == 1:
            view = "a" if text == "/alerts" else "s"
            rendered = await render_project_view(
                db, chat_id=chat_id, project_id=projects[0].id, view=view
            )
            if rendered is not None:
                body, keyboard = rendered
                await notifier.send_message(chat_id, body, reply_markup=keyboard)
            return

        if len(projects) == 1:
            project = projects[0]
            await notifier.send_message(
                chat_id,
                f"🌿 AQUAPONICS\n\nHệ thống: {project.name} ({project.code})\nChọn thông tin cần xem.",
                reply_markup=telegram_action_keyboard(project.id),
            )
            return

        await notifier.send_message(
            chat_id,
            "🌿 AQUAPONICS\n\nBạn được cấp quyền nhiều hệ thống. Chọn hệ thống cần xem:",
            reply_markup=project_picker_keyboard(projects),
        )


async def handle_update(notifier: TelegramNotifier, update: dict[str, Any]) -> None:
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        await _handle_callback(notifier, callback)
        return
    message = update.get("message")
    if isinstance(message, dict):
        await _handle_message(notifier, message)


async def run_telegram_bot_loop() -> None:
    notifier = TelegramNotifier()
    offset: int | None = None
    initialized = False
    while True:
        try:
            if not notifier.configured:
                await asyncio.sleep(30)
                continue
            if not initialized:
                # Drop stale updates left from before this worker was deployed/restarted.
                # Telegram confirms older updates when a negative offset is requested.
                pending = await notifier.get_updates(offset=-1, timeout_seconds=0)
                ids = [item.get("update_id") for item in pending]
                valid_ids = [item for item in ids if isinstance(item, int)]
                if valid_ids:
                    offset = max(valid_ids) + 1
                initialized = True
                continue
            updates = await notifier.get_updates(offset=offset, timeout_seconds=20)
            if not updates:
                await asyncio.sleep(1)
                continue
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = max(offset or 0, update_id + 1)
                try:
                    await handle_update(notifier, update)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "event=telegram_update_failed update_id=%s", update_id
                    )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("event=telegram_long_poll_failed")
            await asyncio.sleep(5)
