import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

# httpx logs the full request URL at INFO. Telegram embeds the bot token in that
# URL, so suppress request-level logs before any notifier client is created.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@dataclass(frozen=True)
class TelegramDeliveryResult:
    sent: bool
    status_code: int | None = None
    error_category: str | None = None


class TelegramNotifier:
    @property
    def configured(self) -> bool:
        return bool(settings.telegram_bot_token and settings.telegram_bot_token.strip())

    async def send_message(self, chat_id: str, text: str) -> TelegramDeliveryResult:
        token = (settings.telegram_bot_token or "").strip()
        if not token:
            return TelegramDeliveryResult(False, error_category="NOT_CONFIGURED")
        timeout = httpx.Timeout(
            settings.telegram_read_timeout_seconds,
            connect=settings.telegram_connect_timeout_seconds,
        )
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
            if response.is_success:
                return TelegramDeliveryResult(True, status_code=response.status_code)
            category = {
                400: "BAD_REQUEST",
                401: "INVALID_TOKEN",
                403: "FORBIDDEN",
                429: "RATE_LIMITED",
            }.get(response.status_code, "TELEGRAM_ERROR")
            return TelegramDeliveryResult(False, response.status_code, category)
        except httpx.TimeoutException:
            return TelegramDeliveryResult(False, error_category="TIMEOUT")
        except httpx.HTTPError:
            return TelegramDeliveryResult(False, error_category="NETWORK_ERROR")
