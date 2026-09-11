# Message rendering

`format_operational_message` renders payload and incident snapshot fields into
Vietnamese plain text. It does not call Telegram-specific threshold evaluation,
but it still branches on legacy actuator feedback roles. The canonical target
is one renderer that formats an immutable incident/event snapshot.
