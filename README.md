# Aquaponics Platform

Nền tảng modular monolith đa khách hàng để quản lý `User -> Project -> Device -> Sensor/Actuator`, nhận telemetry qua MQTT, giám sát/cảnh báo và điều khiển actuator.

## Kiến trúc

FastAPI API, MQTT consumer và scheduler dùng chung application services, SQLAlchemy models, authorization và PostgreSQL. Frontend React/Vite tuân theo `app -> pages -> widgets -> features -> entities -> shared`. Xem [modular monolith](docs/architecture/modular-monolith.md) và [module boundaries](docs/architecture/module-boundaries.md).

## Yêu cầu và môi trường

- Docker + Docker Compose; hoặc Python 3.12 và Node 22.
- Frontend `3000`, backend `8000`, MQTT `1883`; PostgreSQL chỉ nội bộ Compose.
- Sao chép `backend/.env.example` và `frontend/.env.example`; không commit `.env`.

```bash
make setup
docker compose config --quiet
docker compose up --build
```

Health: `curl http://localhost:8000/health` và `curl http://localhost:3000`.

## Database, migration và seed

Database hiện hữu ở `0016` cần backup/audit rồi:

```bash
cd backend
alembic upgrade head
python scripts/seed.py
```

Fresh database dùng baseline guard; tên database bắt buộc có prefix disposable/fresh:

```bash
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aquaponics_fresh_local
cd backend
python scripts/bootstrap_fresh_database.py
python scripts/seed.py
```

Không chạy bootstrap trên database có bảng hoặc tên không được phép. Chi tiết: [database migrations](docs/operations/database-migrations.md).

## Development commands

```bash
make backend-dev
make frontend-dev
make validate
make validate-database
```

Backend: `python -m compileall -q app`, architecture checker, pytest. Frontend: typecheck, lint, Vitest, build.

## MQTT

- Telemetry: `aquaponics/{device_code}/telemetry`
- Status: `aquaponics/{device_code}/status`
- Commands/ACK dùng Device-scoped actuator code theo cấu hình hiện tại.

MQTT hiện không được thiết kế để public trực tiếp ra Internet. Port 1883 anonymous/no TLS chỉ dành cho development hoặc LAN được kiểm soát. Frontend không kết nối broker trực tiếp.

## Power monitoring

Sáu đại lượng điện áp đầu ra, điện áp đầu vào, dòng tải, dòng đầu vào, công suất và điện năng là Sensor trên Device hiện hữu. UI power dùng `POWER_W` do thiết bị đo; không tự tính `V × I`. `ENERGY_TOTAL_WH` là counter raw duy nhất; server tính delta theo các đoạn để reset không tạo giá trị âm. Project power tính AVG từng Device rồi SUM, với `partial=true` khi thiếu Device.

## Giới hạn đã biết

- MQTT TLS/certificate/authentication redesign chưa thuộc phạm vi hiện tại.
- AC/DC, meter chipset, energy reset/wrap, sampling và retention production cần xác nhận.
- Historical Alembic `0001` phụ thuộc current metadata; fresh install dùng guarded baseline thay vì replay `0001–0016`.
