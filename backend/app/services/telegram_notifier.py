import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

# Telegram embeds the bot token in the request URL. Never let httpx/httpcore
# emit request URLs at INFO level.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramDeliveryResult:
    sent: bool
    status_code: int | None = None
    error_category: str | None = None
    retry_after_seconds: int | None = None


class TelegramNotifier:
    @property
    def configured(self) -> bool:
        return bool(self._token)

    @property
    def _token(self) -> str:
        return (settings.telegram_bot_token or "").strip()

    def _url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._token}/{method}"

    @staticmethod
    def _error_result(response: httpx.Response) -> TelegramDeliveryResult:
        category = {
            400: "BAD_REQUEST",
            401: "INVALID_TOKEN",
            403: "FORBIDDEN",
            429: "RATE_LIMITED",
        }.get(response.status_code, "TELEGRAM_ERROR")
        retry_after = None
        if response.status_code == 429:
            try:
                retry_after = int((response.json().get("parameters") or {}).get("retry_after"))
            except (TypeError, ValueError):
                retry_after = None
        return TelegramDeliveryResult(
            False,
            status_code=response.status_code,
            error_category=category,
            retry_after_seconds=retry_after,
        )

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
    ) -> TelegramDeliveryResult:
        if not self.configured:
            return TelegramDeliveryResult(False, error_category="NOT_CONFIGURED")
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        timeout = httpx.Timeout(
            settings.telegram_read_timeout_seconds,
            connect=settings.telegram_connect_timeout_seconds,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self._url("sendMessage"), json=payload)
            if response.is_success:
                return TelegramDeliveryResult(True, status_code=response.status_code)
            return self._error_result(response)
        except httpx.TimeoutException:
            return TelegramDeliveryResult(False, error_category="TIMEOUT")
        except httpx.HTTPError:
            return TelegramDeliveryResult(False, error_category="NETWORK_ERROR")

    async def edit_message_text(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
    ) -> TelegramDeliveryResult:
        if not self.configured:
            return TelegramDeliveryResult(False, error_category="NOT_CONFIGURED")
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        timeout = httpx.Timeout(
            settings.telegram_read_timeout_seconds,
            connect=settings.telegram_connect_timeout_seconds,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self._url("editMessageText"), json=payload)
            if response.is_success:
                return TelegramDeliveryResult(True, status_code=response.status_code)
            # Telegram returns BAD_REQUEST when the rendered text is unchanged.
            # Treating that as success keeps refresh callbacks idempotent.
            if response.status_code == 400 and "message is not modified" in response.text.lower():
                return TelegramDeliveryResult(True, status_code=response.status_code)
            return self._error_result(response)
        except httpx.TimeoutException:
            return TelegramDeliveryResult(False, error_category="TIMEOUT")
        except httpx.HTTPError:
            return TelegramDeliveryResult(False, error_category="NETWORK_ERROR")

    async def answer_callback_query(
        self, callback_query_id: str, *, text: str | None = None
    ) -> bool:
        if not self.configured:
            return False
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self._url("answerCallbackQuery"), json=payload)
            return response.is_success
        except httpx.HTTPError:
            return False

    async def get_updates(
        self,
        *,
        offset: int | None = None,
        timeout_seconds: int = 20,
    ) -> list[dict[str, Any]]:
        if not self.configured:
            return []
        payload: dict[str, Any] = {
            "timeout": max(0, timeout_seconds),
            "allowed_updates": ["callback_query", "message"],
        }
        if offset is not None:
            payload["offset"] = offset
        timeout = httpx.Timeout(
            max(settings.telegram_read_timeout_seconds, timeout_seconds + 5),
            connect=settings.telegram_connect_timeout_seconds,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(self._url("getUpdates"), json=payload)
            response.raise_for_status()
            body = response.json()
            result = body.get("result") if body.get("ok") else []
            return result if isinstance(result, list) else []
        except (httpx.HTTPError, ValueError, TypeError):
            logger.exception("event=telegram_get_updates_failed")
            return []
