# Telegram service flow

`TelegramNotifier.send_message(chat_id, text)` uses `httpx.AsyncClient.post`
to the Telegram Bot `sendMessage` endpoint. Token comes solely from
`settings.telegram_bot_token`; connect/read timeouts are settings with defaults
of 5 and 10 seconds. The payload has no parse mode or explicit message-length
handling. HTTP 400/401/403/429 map to named error categories; timeout and HTTP
errors map to `TIMEOUT` and `NETWORK_ERROR`.

The notifier suppresses `httpx` and `httpcore` request-level logs because the
URL embeds the token. Retry is owned by outbox/delivery state: exponential
minutes and a five-attempt cap.
