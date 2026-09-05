import logging

from app.services.telegram_notifier import TelegramNotifier


def test_telegram_http_client_does_not_log_token_bearing_urls_at_info() -> None:
    assert TelegramNotifier
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING
