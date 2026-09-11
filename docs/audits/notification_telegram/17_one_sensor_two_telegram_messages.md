# 1. Executive Summary

**Kết luận đã được chứng minh:** tại thời điểm `08/09/2026 17:13:37` (Asia/Ho_Chi_Minh), một reading pH `10,8` của Sensor `93` đã đi qua **hai evaluator OperationalIncident đang cùng được gọi trong telemetry ingest**:

1. canonical Sensor threshold dùng `threshold_alert_configs`, tạo Incident `125`, Outbox `720`, event `OPEN`;
2. rule/profile path dùng `WATER_PH_OUT_OF_RANGE`, tạo Incident `126`, Outbox `721`, event `OPEN`.

Ba recipient đều nhận cả Outbox `720` và `721` lúc `18:12:32`. Đây là cùng reading, cùng lifecycle event `OPEN`, nhưng là hai Incident semantic trùng nhau với threshold, risk, message snapshot và nhánh formatter khác nhau. Root cause tại thời điểm xảy ra là **RC-A (two active notification pipelines)**, kéo theo **RC-C (two renderer branches)** và **RC-D (custom threshold message versus rule message)**. Severity: **P1** vì cùng sự cố gửi hai nội dung Telegram không thống nhất; bằng chứng không cho thấy cùng một Incident/event bị gửi hai lần nên không xếp P0 idempotency failure.

Current source và các container đang chạy đã không còn gọi rule/profile evaluator từ telemetry. Byte hash của `telemetry_service.py`, `operational_incident_service.py` và `notification_outbox_service.py` trong container trùng workspace; container rollout lúc `08/09/2026 18:12:17`, và DB không có rule-based Sensor Incident mới sau thời điểm đó. Report này không sửa code và không khẳng định file rule evaluator đã bị xóa: function vẫn tồn tại nhưng hiện không có production caller.

`notification_message_catalog` **không tạo ra cặp 10,8**: hai snapshot của cặp này được tạo trước khi catalog fields được materialize. Catalog hiện tham gia canonical snapshot cho các reading sau rollout; nó bổ sung title/consequence/actions, còn custom `above_message`/`below_message` vẫn là `message`/ghi chú. DB không có `ACTIVE_SYNC`, và `REMINDER`/recovery/resolved không phải hai `OPEN` trong forensic pair.

Phạm vi bằng chứng: source hiện tại, source tại commit cha `91528d4`, DB PostgreSQL schema head `0053`, container runtime, Docker logs hiện còn giữ. Telegram body không được persist và `provider_message_id` đều null; hai body ở mục 11–12 được tái dựng deterministically từ snapshot DB và đúng formatter/runtime code tại `processed_at`, không phải nội dung đọc ngược từ Telegram API.

# 2. Sensor Forensic Example

| Field | Value |
| --- | --- |
| System | `81`, `TB-0015`, “Dự án nuôi cá trê” |
| Device | `86`, `TB-0015-MT-3022-01`, “Thiết bị đo nhiệt độ, độ ẩm” |
| Sensor | `93`, `TB-0015-MT-3022-01-PH-02`, “Độ pH” |
| SensorModel | `PH`, “Cảm biến pH”, unit `pH` |
| Reading | `telemetry_readings.id=1634532`, value `10.8` |
| Recorded | `2026-09-08 10:13:37+00` / `17:13:37+07` |
| Received | `2026-09-08 10:13:37.106623+00` |

Sensor legacy columns vẫn có `lower_threshold=0`, `upper_threshold=14`, nhưng current evaluator không đọc chúng. Canonical authority là row `threshold_alert_configs.id=19`.

# 3. Threshold Configuration

| Field | Value |
| --- | --- |
| sensor_id / metric_type | `93` / `SENSOR_VALUE` |
| enabled | `true` |
| lower / upper | `7.0` / `9.0` |
| below / above risk | `LOW` / `HIGH` |
| below / above message | `Thấp quá` / `Cao quá` |
| delay_seconds | `0` |
| updated_at | `2026-09-08 09:39:16.738235+00` (trước forensic reading) |

Model/table evidence: `backend/app/models/threshold_alert_config.py::ThresholdAlertConfig` khai báo duy nhất một row mỗi Sensor (`uq_threshold_alert_config_sensor`) và các fields `enabled`, thresholds, directional risks/messages, `delay_seconds`. `backend/app/services/threshold_alert_config_service.py::get_sensor_threshold_alert_config` lọc `sensor_id` + `SENSOR_VALUE`; `evaluate_threshold` chọn `BELOW` trước, rồi `ABOVE`, rồi `NORMAL`.

Rule path thứ hai không dùng row này. Incident `126` dùng rule `8`, revision `8`, `WATER_PH_OUT_OF_RANGE`, evaluator `RANGE_BANDS`, band rộng `6.0–8.0`, risk `VERY_HIGH`, message `pH bất thường, hãy kiểm tra môi trường nước`.

# 4. Runtime Call Graph

## Current canonical telemetry path

```text
backend/app/mqtt/consumer.py::main.on_message
  -> backend/app/mqtt/handlers.py::handle_telemetry
  -> backend/app/services/telemetry_ingest_service.py::ingest_mqtt_telemetry
  -> backend/app/services/telemetry_service.py::ingest_telemetry
     -> INSERT telemetry_readings ON CONFLICT(sensor_id, recorded_at) DO NOTHING
     -> backend/app/services/operational_incident_service.py::evaluate_sensor_threshold_incident
        -> threshold_alert_config_service.py::get_sensor_threshold_alert_config
        -> threshold_alert_config_service.py::evaluate_threshold
        -> notification_message_catalog.py::sensor_condition_key / catalog_snapshot
        -> OperationalIncident (`operational_incidents`)
        -> operational_incident_service.py::_enqueue
        -> NotificationOutbox (`notification_outbox`, event OPEN/RECOVERED/...)
  -> COMMIT

backend/app/jobs/runner.py::background_loop / run_scheduler_cycle (mỗi 60 giây)
  -> backend/app/jobs/notification_outbox.py::dispatch_operational_notifications
     -> notification_outbox_service.py::enqueue_due_reminders
     -> notification_outbox_service.py::process_notification_outbox
        -> evaluate_notification_policy
        -> resolve_notification_recipients
        -> _payload_at_delivery
        -> format_operational_message
           -> format_canonical_operational_message when resource_type + metric_type exist
           -> generic fallback otherwise
        -> TelegramNotifier.send_message
        -> httpx.AsyncClient.post(.../sendMessage)
```

Models/tables/events:

- `TelemetryReading` / `telemetry_readings`.
- `ThresholdAlertConfig` / `threshold_alert_configs`.
- `OperationalIncident` / `operational_incidents`, statuses `PENDING`, `OPEN`, `ACKNOWLEDGED`, `NORMALIZED`, `RESOLVED`.
- `NotificationOutbox` / `notification_outbox`, incident events `OPEN`, `ACTIVE_SYNC`, `ESCALATED`, `REMINDER`, `RECOVERED`, `RESOLVED`.
- `NotificationDelivery` / `notification_deliveries`, channel `TELEGRAM`.

## Path active at forensic event

At commit cha `91528d4`, `telemetry_service.py::ingest_telemetry` gọi tuần tự cả:

```text
evaluate_sensor_threshold_incident(...)                 # canonical config
evaluate_operational_rules_for_sensor(...)              # rule/profile
  -> _evaluate_sensor_profiles
  -> EVALUATOR_REGISTRY['RANGE_BANDS'].evaluate
  -> _transition_sensor_incident
  -> _enqueue
```

DB timestamps giống hệt tới microsecond cho Incidents `125` và `126`, và source lịch sử cho thấy hai calls nằm kế tiếp trong cùng loop/transaction. Current `telemetry_service.py` chỉ còn call đầu.

## Threshold-save reconciliation path

`backend/app/api/v1/aquaponics_systems.py::{create,update,delete}_sensor_threshold` gọi `reevaluate_latest_sensor_threshold`, rồi dùng cùng canonical evaluator và cùng `_enqueue`. Nó có thể mở/normalize Incident dựa trên reading mới nhất khi config đổi, nhưng không tạo một loại formatter riêng.

# 5. Telegram Send Call Sites

| Callsite | Classification | Production reachability |
| --- | --- | --- |
| `notification_outbox_service.py::process_notification_outbox` → `notifier.send_message` | Canonical alert/operational sender | Active; scheduler gọi mỗi cycle |
| `canonical_extensions.py::test_recipient` → `TelegramNotifier().send_message` | Explicit administrative test | Active endpoint, nhưng không thuộc telemetry/alert path và task này không gọi |
| Fake notifier `send_message` trong `test_notification_contract_idempotency.py` và `test_telegram_alert_canonical_pipeline.py` | Test-only | Không production |

Chỉ `backend/app/services/telegram_notifier.py::TelegramNotifier.send_message` gọi Telegram Bot API qua `httpx .../sendMessage`. Không có browser/frontend call Telegram API và không có sender nào trong `alert_service.py` hoặc `project_notification_service.py`.

# 6. Message Renderers

1. `notification_outbox_service.py::format_canonical_operational_message`: Sensor/Actuator snapshot có cả `resource_type` và `metric_type`; hiển thị resource, value, threshold, catalog title/consequence/actions và custom note.
2. `notification_outbox_service.py::format_operational_message` generic branch: payload thiếu canonical discriminator; dùng project/device/sensor, threshold/range, duration và raw `message`.
3. `notification_outbox_service.py::format_project_activity_message`: trả raw snapshotted project activity text.
4. `project_notification_service.py` dựng sẵn text cho connectivity, actuator command, project health rồi enqueue `SYSTEM_EVENT`; common worker vẫn là sender.
5. `project_activity_service.py::format_project_activity_message` dựng activity text trước khi enqueue; không phải Sensor alert renderer.

`TelegramNotifier` nhận `chat_id` + raw rendered `text` và không format lại.

# 7. Message Source Precedence

Current canonical Sensor threshold resolution:

```text
priority 1 (field message/Ghi chú) = non-blank directional custom message
  ABOVE -> ThresholdAlertConfig.above_message
  BELOW -> ThresholdAlertConfig.below_message

priority 2 (field message fallback) = catalog title

catalog semantic fields (always snapshotted) = title + consequence + recommended_actions
fallback catalog key = SENSOR_THRESHOLD_HIGH / SENSOR_THRESHOLD_LOW
```

Key resolution is `SensorModel.code.upper()` + direction:

- `PH` → `SENSOR_PH_HIGH` / `SENSOR_PH_LOW`;
- `TEMP` or `WATER_TEMPERATURE` above → `SENSOR_WATER_TEMPERATURE_HIGH`;
- `TDS` below → `SENSOR_TDS_LOW`;
- `WATER_LEVEL` below → `SENSOR_WATER_LEVEL_LOW`;
- otherwise generic `SENSOR_THRESHOLD_HIGH/LOW`.

Catalog không có numeric threshold. Runtime number luôn đến từ `ThresholdAlertConfig`. Với Sensor `93`, current BELOW resolves `SENSOR_PH_LOW`; current snapshot cho Incident `130` chứa catalog title/consequence/actions và custom `message="Thấp quá"`.

OPEN, REMINDER, RECOVERED và RESOLVED đều đi qua cùng resolution snapshot/renderer. `_payload_at_delivery` còn merge selected fields từ **live `incident.trigger_snapshot`**, override outbox snapshot; do đó nội dung một outbox cũ có thể nhận wording/số đo mới hơn trước lúc gửi. Đây là nguy cơ RC-H, không phải nguyên nhân đã chứng minh của cặp 10,8.

# 8. Incident Timeline

| Time (UTC / +07) | Reading | Incident | Condition | Event transition | Message source |
| --- | ---: | --- | --- | --- | --- |
| `10:13:22` / `17:13:22` | `6.0` | prior canonical BELOW `124` | `sensor:93:threshold:BELOW` | active | canonical custom |
| `10:13:37.106623` / `17:13:37` | `10.8` | `125`, `rule_id=NULL`, HIGH | `sensor:93:threshold:ABOVE` | OPEN | ThresholdAlertConfig `above_message="Cao quá"`, threshold `9` |
| same microsecond | `10.8` | `126`, `rule_id=8`, VERY_HIGH | `sensor:93` / `WATER_PH_OUT_OF_RANGE` | OPEN | AlertRule revision message, range `6–8` |
| `10:13:52.108505` / `17:13:52` | `6.7` | `125` and `126` | both prior high conditions | both RESOLVED; corresponding delivery later skipped by policy | separate lifecycle event |

The exact same semantic duplication repeats at reading `11.0`, producing Incidents `128` and `129` at `10:14:52.135582+00`. These are the only exact canonical/rule same-start pairs found by the DB join.

# 9. Outbox Timeline

| Created UTC | Incident | Event | Outbox | Idempotency | Status | Message source |
| --- | --- | --- | --- | --- | --- | --- |
| `10:13:37.109780` | `125` | `OPEN` | `720` | `incident:125:OPEN` | SENT | canonical threshold snapshot |
| same | `126` | `OPEN` | `721` | `incident:126:OPEN` | SENT | rule/profile snapshot |
| `10:13:52.111318` | `125` | `RESOLVED` | `722` | `incident:125:RESOLVED` | SKIPPED / EVENT_DISABLED | legitimate later event |
| `10:13:52.111318` | `126` | `RESOLVED` | `724` | `incident:126:RESOLVED` | SKIPPED / EVENT_DISABLED | legitimate later event |

Hai OPEN không trùng `idempotency_key` vì chúng thuộc hai Incident khác nhau. Vì vậy per-Incident idempotency hoạt động đúng nhưng không thể nhận ra semantic duplicate giữa pipelines.

# 10. Delivery Timeline

| Sent UTC / +07 | Outbox | Incident | Event | Recipients | Attempts | Result |
| --- | --- | --- | --- | ---: | ---: | --- |
| `11:12:32.223838` / `18:12:32` | `720` | `125` | OPEN | IDs `1,3,4` | 1 mỗi recipient | SENT / HTTP 200 |
| same | `721` | `126` | OPEN | IDs `1,3,4` | 1 mỗi recipient | SENT / HTTP 200 |

There are six delivery rows because there are three recipients, but the bug is not “multiple recipients”: each individual recipient has one delivery for Outbox `720` **and** one for `721`. No Telegram delivery row has `provider_message_id`, so provider-side text/ID cannot be independently replayed from DB.

# 11. Message A

Message A is Outbox `720`, reconstructed using `_payload_at_delivery(outbox, incident, processed_at)` and the runtime formatter:

```text
🔴 CẢNH BÁO CAO — HỆ THỐNG AQUAPONICS

MỨC ĐỘ: CAO
HỆ THỐNG: Dự án nuôi cá trê
THIẾT BỊ: Thiết bị đo nhiệt độ, độ ẩm
NGUỒN: Độ pH
Chỉ số: SENSOR VALUE
Giá trị: 10,8 pH
Ngưỡng: > 9 pH
Thời gian: 08/09/2026 17:13:37

Ghi chú: Cao quá
```

Source: `ThresholdAlertConfig.id=19`, canonical Incident `125`, canonical renderer. Snapshot này có `resource_type=SENSOR`, `metric_type=SENSOR_VALUE`, nhưng chưa có catalog fields.

# 12. Message B

Message B is Outbox `721`, reconstructed bằng cùng worker/runtime formatter:

```text
🔴 CẢNH BÁO RẤT CAO

Hệ thống Aquaponics: Dự án nuôi cá trê
Thiết bị: Thiết bị đo nhiệt độ, độ ẩm
Cảm biến: Độ pH
Mã cảm biến: TB-0015-MT-3022-01-PH-02
Ngưỡng cảnh báo: < 6 hoặc > 8 pH
Bắt đầu: 08/09/2026 17:13:37
Đã kéo dài: 58 phút 55 giây

pH bất thường, hãy kiểm tra môi trường nước
```

Source: AlertRule `WATER_PH_OUT_OF_RANGE`, revision `8`, Incident `126`, generic renderer. Rule snapshot có consequence nhưng generic renderer không hiển thị nó.

# 13. Difference Analysis

| Field | Message A | Message B | Why |
| --- | --- | --- | --- |
| Incident | `125` | `126` | two evaluator paths |
| Risk | HIGH | VERY_HIGH | config row vs rule revision |
| Threshold | `> 9` | outside `6–8` | two threshold authorities at event time |
| Naming | `NGUỒN: Độ pH` | `Cảm biến` + code | canonical vs generic renderer |
| Body | custom `Cao quá` as note | rule message as main text | different snapshot source |
| Duration | omitted | 58m55s | renderer branch |
| Catalog guidance | absent | absent/rendered absent | pair predates catalog materialization; not its cause |

The 58m55s duration is calculated at delayed dispatch (`processed_at - started_at`), not at the reading time.

# 14. Legacy Path Audit

`backend/app/services/alert_service.py` contains legacy `SensorAlert` operations. Caller proof in current tree:

- `telemetry_service.py` calls only `normalize_active_alert(... SENSOR_OFFLINE ...)` when telemetry resumes.
- `jobs/offline_scanner.py` calls `get_active_alert` and creates/updates `SensorAlert` for offline visibility.
- `alert_service.py::evaluate_threshold` has no current production caller.
- `project_notification_service.py::dispatch_alert_transition` is a retired no-op and has no caller.
- No legacy `SensorAlert` code enqueues notification or calls Telegram.

Therefore legacy `SensorAlert` is **partly active for offline state persistence, but not an active Telegram sender**. The proven second sender source was not `SensorAlert`; it was the OperationalIncident rule/profile path (`evaluate_operational_rules_for_sensor`) that was actively called by the historical telemetry source.

Current state: the rule/profile evaluator function remains in `operational_incident_service.py`, but repo-wide caller search finds no current production caller. One historical rule Incident (`117`, AIR_TEMPERATURE_HIGH) remains OPEN in DB, last triggered before rollout; the current reminder scanner can still inspect retained open incidents, so lifecycle cleanup/audit remains advisable.

# 15. ACTIVE_SYNC Audit

Migration `0053_telegram_alert_reconciliation.py` adds `notification_generation`, `target_recipient_id` and supporting schema. Current endpoints trigger `reconcile_active_incident_notifications` when settings/policy changes or a recipient is created/enabled/Chat ID changes.

ACTIVE_SYNC uses:

- the Incident `trigger_snapshot`;
- `event_type=ACTIVE_SYNC`;
- generation + recipient-scoped outbox key;
- OPEN policy switch;
- the same canonical/generic formatter selection as OPEN.

DB evidence: `count(notification_outbox where event_type='ACTIVE_SYNC') = 0`, and System `81` has `notification_generation=0`. ACTIVE_SYNC is **not involved** in the forensic duplicate.

# 16. Reminder Audit

`jobs/notification_outbox.py` calls `enqueue_due_reminders` before dispatch. Reminder eligibility requires active OPEN/ACKNOWLEDGED Incident, global Telegram enabled, matching risk policy enabled, `reminder_enabled`, `max_reminders > 0`, due interval, and optionally not acknowledged.

Keys are `incident:{id}:REMINDER:{sequence}` and deliveries use the same sequence. Multiple reminders for one Incident are expected multi-event behavior. Sensor `93` has historical rule reminders, but Incidents `125`/`126` have no REMINDER row. Thus reminder is not Message A/B.

Current renderer weakness: canonical and generic formatters do not visibly label `REMINDER` (all non-recovery/resolution events use a warning heading). That can make valid reminders look like duplicate OPEN messages; classify as separate **P2 clarity issue**, not this pair's cause.

# 17. Recovery Audit

Canonical Sensor normal/cross-direction transition currently emits `RECOVERED` and moves OPEN/ACKNOWLEDGED to `NORMALIZED`; manual resolve emits `RESOLVED`. Historical forensic rows emitted `RESOLVED`. Policy can independently enable/disable these lifecycle events.

For the 10,8 pair, later RESOLVED Outboxes `722` and `724` were skipped with `EVENT_DISABLED`; they are not Message A/B. The canonical renderer labels `RECOVERED` and `RESOLVED` distinctly, while generic fallback also now lacks event-specific heading except through the outer branch behavior; retained legacy payloads deserve regression coverage.

# 18. Idempotency Audit

- `notification_outbox.idempotency_key` is unique; duplicate-key count in DB is `0`.
- `_enqueue` uses `incident:{id}:{event}`; escalation adds risk; reminder adds sequence; ACTIVE_SYNC adds generation and recipient.
- Inserts use `ON CONFLICT DO NOTHING`.
- `notification_deliveries.idempotency_key` is unique; duplicate-key count is `0`.
- Delivery identity includes Incident/event semantics and then channel/recipient.
- Worker additionally checks prior SENT for same Incident + event + recipient for OPEN/RECOVERED/RESOLVED/ESCALATED.
- Active Incident partial unique indexes enforce `(project, context_key)` and `(rule_id, context_key)` for active statuses.

One Incident OPEN cannot normally enqueue/deliver twice. However, ids/keys are Incident-scoped, not semantic-condition-scoped. Incidents `125` and `126` have different ids/context keys, so both correctly bypass these guards. No evidence supports RC-F.

# 19. Worker Concurrency Audit

Compose defines one `scheduler` service; runtime `docker compose top` showed one `python -m app.jobs.runner` process and one MQTT consumer process. Job interval is 60 seconds.

Worker claims Incident first and Outbox second using `FOR UPDATE`, with `skip_locked=True` on Outbox, then holds the transaction while calling Telegram and commits at the end. A competing worker would re-check status after acquiring locks. No duplicate delivery keys, each forensic delivery has one attempt, and only one scheduler instance exists. No evidence supports RC-G.

Operational note outside the root cause: retained logs show repeated `project_health_evaluator` insert failures after rollout. They do not reference forensic outboxes and are not a second Telegram sender, so this report does not classify them as causal.

# 20. Root Causes

| Code | Finding | Evidence | Status |
| --- | --- | --- | --- |
| RC-A | Two active OperationalIncident notification pipelines | historical caller graph + paired DB Incidents `125/126`, `128/129` | **Proven at event time; caller removed in current runtime** |
| RC-C | Two formatter branches | canonical discriminator on Outbox `720`; absent on `721`; deterministic bodies differ | **Proven** |
| RC-D | Custom threshold message vs rule message | `Cao quá` vs rule revision text | **Proven contributor** |
| RC-E | Duplicate semantic conditions/keys | `sensor:93:threshold:ABOVE` and `sensor:93` both represent same pH-high reading | **Proven** |
| RC-H | Live Incident snapshot can override historical Outbox snapshot | `_payload_at_delivery` merge order; Incident `130` later gains catalog fields | **Design risk; not needed to explain pair** |
| RC-B | OPEN + ACTIVE_SYNC/reminder/recovery | both forensic messages are OPEN | Rejected for pair |
| RC-F | Duplicate Outbox/idempotency failure | unique keys, zero duplicate keys, distinct Incidents | Rejected |
| RC-G | Multiple-worker race | one scheduler, row locks, one attempt | Rejected |

# 21. Severity

**P1** — the same telemetry condition caused two Telegram OPEN messages with conflicting risk (`HIGH` vs `VERY_HIGH`), thresholds (`>9` vs outside `6–8`) and wording. It is not P0 under the supplied definition because there is no duplicate Outbox/delivery for the same Incident/event generation and no repeated send attempt. The separate unlabeled-reminder concern is P2.

Current exposure is lower than event-time exposure because the second telemetry caller is absent in the deployed bytes. Historical OPEN rule Incidents and old outboxes remain retained data and must not be deleted/reset without a separately approved data plan.

# 22. Recommended Fix Plan

No implementation is part of this audit. Recommended order:

1. Formally lock Sensor thresholds to the single canonical `ThresholdAlertConfig -> OperationalIncident(rule_id=NULL)` path; add an architecture test that telemetry cannot call `evaluate_operational_rules_for_sensor` for Sensor threshold semantics.
2. Lock one message-resolution contract: catalog supplies title/consequence/actions; directional custom message supplies only an explicitly named note/override field; generic fallback only for truly non-canonical retained payloads.
3. Define lifecycle headings for OPEN, ACTIVE_SYNC, ESCALATED, REMINDER, RECOVERED and RESOLVED in both renderer branches; include event type visibly.
4. Add a semantic idempotency/contract assertion for `(sensor, metric, direction, condition generation)` so a rule/profile cannot coexist with canonical threshold meaning even under regression.
5. Remove or disable any future duplicate runtime caller only after auditing advanced non-threshold rule consumers; separately decide how to normalize retained active rule Incidents without destructive ad-hoc DB work.
6. Add backend tests reproducing Sensor `PH`, custom `above_message`, catalog mapping, one Incident/OPEN/outbox per crossing, recipient-level dedupe, reminder labeling, recovery, and ACTIVE_SYNC.
7. Validate API create/update/delete threshold reconciliation and notification-policy changes against the same event contract.
8. Change frontend only if needed to expose event/reason clearly; frontend remains configuration-only and must never render/send Telegram bodies.

## Audit safety record

- Source code changed: **NO**.
- Database changed: **NO**; all forensic SQL was SELECT/catalog inspection.
- Telegram sent: **NO**; test endpoint was not called.
- Containers restarted/scaled: **NO**.
- Artifacts created: this Markdown report and `one_sensor_two_messages_trace.json` only.
