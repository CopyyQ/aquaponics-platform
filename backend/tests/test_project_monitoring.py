from datetime import UTC, datetime, timedelta, timezone
from time import perf_counter
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete, event, select

from app.core.enums import DeviceStatus, ProjectStatus, SensorPurpose, SensorStatus, UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.device import Device
from app.models.actuator import Actuator, ActuatorStateHistory
from app.models.actuator_model import ActuatorModel
from app.models.operational_alert import ActuatorFeedbackBinding
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.models.telemetry import TelemetryReading
from app.models.user import User
from app.services.monitoring_service import get_project_monitoring_latest
from app.services.actuator_state_service import record_actuator_reported_state
from test_visibility_authorization import visibility_data


def auth_header(user_id: int, token_version: int, role: str) -> dict[str, str]:
    token = create_access_token(str(user_id), {"role": role, "token_version": token_version})
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_project_overview_and_monitoring_expose_typed_actuator_current_zero(visibility_data) -> None:
    data = visibility_data
    created: dict[str, int] = {}
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        current_model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A"))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        assert current_model is not None
        assert actuator_model is not None
        sensor = Sensor(device_id=data["active_device"], sensor_model_id=current_model.id, code=f"CURRENT-{data['active_project']}", name="Dòng điện kiểm thử", is_enabled=True)
        actuator = Actuator(device_id=data["active_device"], actuator_model_id=actuator_model.id, sequence_number=999, code=f"ACT-CURRENT-{data['active_project']}", name="Bơm kiểm thử dòng điện", is_enabled=True, desired_state=True, reported_state=True, last_reported_at=now)
        db.add_all([sensor, actuator])
        await db.flush()
        binding = ActuatorFeedbackBinding(actuator_id=actuator.id, sensor_id=sensor.id, feedback_role="RUNNING_CURRENT", is_enabled=True)
        reading = TelemetryReading(sensor_id=sensor.id, value=0.0, recorded_at=now, received_at=now)
        db.add_all([binding, reading])
        await db.commit()
        created = {"sensor": sensor.id, "actuator": actuator.id}

    try:
        headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/projects/{data['active_project']}/overview", headers=headers)
            monitoring = await client.get(f"/api/v1/projects/{data['active_project']}/monitoring/inventory", headers=headers)
        assert response.status_code == 200, response.text
        payload = response.json()
        item = next(value for value in payload["actuators"] if value["id"] == created["actuator"])
        assert item["electrical"]["configured"] is True
        assert item["electrical"]["current_a"] == 0.0
        assert item["electrical"]["quality"] == "VALID"
        assert item["electrical"]["freshness"] == "FRESH"
        assert payload["actuator_inventory"]["total"] >= 1
        assert monitoring.status_code == 200, monitoring.text
        device = next(value for value in monitoring.json()["devices"] if value["id"] == data["active_device"])
        monitored = next(value for value in device["actuators"] if value["id"] == created["actuator"])
        assert monitored["electrical"]["configured"] is True
        assert monitored["electrical"]["current_a"] == 0.0
        assert monitored["electrical"]["quality"] == "VALID"
        assert "operational_conclusion" not in monitored
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id == created["actuator"]))
            await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id == created["sensor"]))
            await db.execute(delete(Actuator).where(Actuator.id == created["actuator"]))
            await db.execute(delete(Sensor).where(Sensor.id == created["sensor"]))
            await db.commit()


@pytest.mark.asyncio
async def test_actuator_monitoring_batch_query_for_10_100_300_rows() -> None:
    suffix = uuid4().hex[:8].upper()
    created: list[dict[str, list[int] | int]] = []
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False)))
        current_model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A"))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        assert owner and current_model and actuator_model
        for size in (10, 100, 300):
            project = Project(owner_user_id=owner.id, code=f"PERF-{size}-{suffix}", name=f"Hiệu năng {size}", status=ProjectStatus.ACTIVE)
            db.add(project)
            await db.flush()
            device = Device(project_id=project.id, code=f"PERF-DEV-{size}-{suffix}", name=f"Thiết bị {size}", status=DeviceStatus.ONLINE, is_enabled=True)
            db.add(device)
            await db.flush()
            sensors = [Sensor(device_id=device.id, sensor_model_id=current_model.id, code=f"PERF-CUR-{index}", name=f"Dòng {index}", is_enabled=True) for index in range(size)]
            actuators = [Actuator(device_id=device.id, actuator_model_id=actuator_model.id, sequence_number=index + 1, code=f"PERF-ACT-{index}", name=f"Bơm {index}", is_enabled=True, desired_state=True, reported_state=True) for index in range(size)]
            db.add_all([*sensors, *actuators])
            await db.flush()
            now = datetime.now(UTC)
            readings = [TelemetryReading(sensor_id=sensor.id, value=0.5, recorded_at=now, received_at=now) for sensor in sensors]
            bindings = [ActuatorFeedbackBinding(actuator_id=actuator.id, sensor_id=sensor.id, feedback_role="RUNNING_CURRENT", is_enabled=True) for actuator, sensor in zip(actuators, sensors, strict=True)]
            db.add_all([*readings, *bindings])
            await db.commit()
            created.append({"project": project.id, "device": device.id, "sensors": [item.id for item in sensors], "actuators": [item.id for item in actuators]})

            statement_count = 0
            captured_sql = ""
            captured_parameters = None

            def count_statement(_connection, _cursor, statement, parameters, _context, _executemany) -> None:
                nonlocal statement_count, captured_sql, captured_parameters
                statement_count += 1
                captured_sql = statement
                captured_parameters = parameters

            event.listen(engine.sync_engine, "before_cursor_execute", count_statement)
            started = perf_counter()
            try:
                payload = await get_project_monitoring_latest(db, project.id)
            finally:
                elapsed_ms = (perf_counter() - started) * 1000
                event.remove(engine.sync_engine, "before_cursor_execute", count_statement)
            monitored_device = next(item for item in payload["devices"] if item["id"] == device.id)
            assert len(monitored_device["actuators"]) == size
            assert statement_count == 3
            assert elapsed_ms < 5000
            print(f"MONITORING_ACTUATOR_BENCHMARK size={size} queries={statement_count} elapsed_ms={elapsed_ms:.2f}")
            if size == 300:
                connection = await db.connection()
                explained = await connection.exec_driver_sql(
                    f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {captured_sql}",
                    captured_parameters,
                )
                plan = explained.scalar_one()[0]
                print(
                    "ACTUATOR_EXPLAIN "
                    f"planning_ms={plan['Planning Time']:.2f} "
                    f"execution_ms={plan['Execution Time']:.2f}"
                )

    async with AsyncSessionLocal() as db:
        for item in reversed(created):
            await db.execute(delete(ActuatorFeedbackBinding).where(ActuatorFeedbackBinding.actuator_id.in_(item["actuators"])))
            await db.execute(delete(TelemetryReading).where(TelemetryReading.sensor_id.in_(item["sensors"])))
            await db.execute(delete(Actuator).where(Actuator.id.in_(item["actuators"])))
            await db.execute(delete(Sensor).where(Sensor.id.in_(item["sensors"])))
            await db.execute(delete(Device).where(Device.id == item["device"]))
            await db.execute(delete(Project).where(Project.id == item["project"]))
        await db.commit()


@pytest.mark.asyncio
async def test_monitoring_latest_keeps_offline_inventory_and_nullable_latest(
    visibility_data,
) -> None:
    data = visibility_data
    viewer_headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    admin_headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    url = f"/api/v1/projects/{data['active_project']}/monitoring/latest"

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(url, headers=viewer_headers)
        assert response.status_code == 200
        payload = response.json()
        assert payload["project_id"] == data["active_project"]
        device = next(item for item in payload["devices"] if item["id"] == data["active_device"])
        assert device["connection_status"] == "OFFLINE"
        sensor = next(item for item in device["sensors"] if item["id"] == data["active_sensor"])
        assert sensor["latest"] is None
        assert sensor["connection_status"] == "WAITING_CONNECTION"
        assert sensor["data_status"] == "WAITING_CONNECTION"

        wrong_project = await client.get(
            f"/api/v1/projects/{data['project_ids'][1]}/monitoring/latest",
            headers=viewer_headers,
        )
        assert wrong_project.status_code == 404
        assert (await client.get(url, headers=admin_headers)).status_code == 200


@pytest.mark.asyncio
async def test_monitoring_latest_marks_old_data_offline_and_excludes_disabled(
    visibility_data,
) -> None:
    data = visibility_data
    admin_headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
    recorded_at = datetime(2026, 7, 23, 1, 29, tzinfo=timezone.utc)
    reading_id: int | None = None

    async with AsyncSessionLocal() as db:
        reading = TelemetryReading(
            sensor_id=data["active_sensor"],
            value=7.2,
            recorded_at=recorded_at,
            received_at=recorded_at,
        )
        db.add(reading)
        await db.commit()
        reading_id = reading.id

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            url = f"/api/v1/projects/{data['active_project']}/monitoring/latest"
            payload = (await client.get(url, headers=admin_headers)).json()
            device = next(item for item in payload["devices"] if item["id"] == data["active_device"])
            sensor = next(item for item in device["sensors"] if item["id"] == data["active_sensor"])
            assert sensor["connection_status"] == "OFFLINE"
            assert sensor["latest"]["value"] == 7.2
            assert sensor["latest"]["freshness"] == "STALE"

            async with AsyncSessionLocal() as db:
                stored_sensor = await db.get(Sensor, data["active_sensor"])
                assert stored_sensor is not None
                stored_sensor.is_enabled = False
                stored_sensor.status = SensorStatus.DISABLED
                await db.commit()
            without_sensor = (await client.get(url, headers=admin_headers)).json()
            device = next(item for item in without_sensor["devices"] if item["id"] == data["active_device"])
            assert device["sensors"] == []

            async with AsyncSessionLocal() as db:
                stored_device = await db.get(Device, data["active_device"])
                assert stored_device is not None
                stored_device.is_enabled = False
                stored_device.status = DeviceStatus.DISABLED
                await db.commit()
            without_device = (await client.get(url, headers=admin_headers)).json()
            assert data["active_device"] not in {item["id"] for item in without_device["devices"]}
    finally:
        async with AsyncSessionLocal() as db:
            if reading_id is not None:
                await db.execute(delete(TelemetryReading).where(TelemetryReading.id == reading_id))
            stored_sensor = await db.get(Sensor, data["active_sensor"])
            stored_device = await db.get(Device, data["active_device"])
            if stored_sensor is not None:
                stored_sensor.is_enabled = True
                stored_sensor.status = SensorStatus.WAITING_CONNECTION
            if stored_device is not None:
                stored_device.is_enabled = True
                stored_device.status = DeviceStatus.OFFLINE
            await db.commit()


@pytest.mark.asyncio
async def test_device_inventory_counts_only_operator_visible_sensors(visibility_data) -> None:
    data = visibility_data
    created: list[int] = []
    expected_count = 0
    async with AsyncSessionLocal() as db:
        model = await db.scalar(select(SensorModel).where(SensorModel.code == "LOAD_CURRENT_A"))
        assert model is not None
        expected_count = len((await db.scalars(select(Sensor.id).where(
            Sensor.device_id == data["active_device"],
            Sensor.is_enabled.is_(True),
            Sensor.is_deleted.is_(False),
            Sensor.deleted_at.is_(None),
            Sensor.purpose == SensorPurpose.GENERAL,
        ))).all()) + 1
        db.add_all([
            Sensor(device_id=data["active_device"], sensor_model_id=model.id, code=f"VISIBLE-{uuid4().hex[:12]}", name="Cảm biến vận hành", is_enabled=True),
            Sensor(device_id=data["active_device"], sensor_model_id=model.id, code=f"INTERNAL-{uuid4().hex[:12]}", name="Phản hồi nội bộ", is_enabled=True, purpose=SensorPurpose.ACTUATOR_FEEDBACK),
        ])
        await db.flush()
        created = [item.id for item in (await db.scalars(select(Sensor).where(Sensor.device_id == data["active_device"]).order_by(Sensor.id.desc()).limit(2))).all()]
        await db.commit()

    try:
        headers = auth_header(data["admin_id"], data["admin_version"], "ADMIN")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/projects/{data['active_project']}/devices", headers=headers)
        assert response.status_code == 200, response.text
        device = next(item for item in response.json()["items"] if item["id"] == data["active_device"])
        assert device["sensor_count"] == expected_count
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Sensor).where(Sensor.id.in_(created)))
            await db.commit()


@pytest.mark.asyncio
async def test_monitoring_series_is_batched_range_scoped_and_validated(
    visibility_data,
) -> None:
    data = visibility_data
    viewer_headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    base_url = f"/api/v1/projects/{data['active_project']}/monitoring/series"
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for monitoring_range, resolution in (("1h", "raw"), ("6h", "5m"), ("12h", "10m"), ("24h", "15m"), ("1m", "1d")):
            response = await client.get(base_url, params={"range": monitoring_range}, headers=viewer_headers)
            assert response.status_code == 200
            payload = response.json()
            assert payload["range"] == monitoring_range
            assert payload["resolution"] == resolution
            series = next(item for item in payload["series"] if item["sensor_id"] == data["active_sensor"])
            assert series["points"] == []

        assert (await client.get(base_url, params={"range": "7d"}, headers=viewer_headers)).status_code == 422
        forbidden = await client.get(
            f"/api/v1/projects/{data['project_ids'][1]}/monitoring/series",
            params={"range": "24h"},
            headers=viewer_headers,
        )
        assert forbidden.status_code == 404


@pytest.mark.asyncio
async def test_monitoring_latest_query_count_does_not_grow_per_sensor(
    visibility_data,
) -> None:
    data = visibility_data
    extra_sensor_ids: list[int] = []
    async with AsyncSessionLocal() as db:
        sensor_model = await db.scalar(select(SensorModel).where(SensorModel.is_deleted.is_(False)))
        assert sensor_model is not None
        sensors = [Sensor(
            device_id=data["active_device"],
            sensor_model_id=sensor_model.id,
            code=f"QUERY-COUNT-{index}-{data['active_project']}",
            name=f"Query Count {index}",
        ) for index in range(5)]
        db.add_all(sensors)
        await db.commit()
        extra_sensor_ids = [sensor.id for sensor in sensors]

    statements = 0

    def count_statement(*_args) -> None:
        nonlocal statements
        statements += 1

    event.listen(engine.sync_engine, "before_cursor_execute", count_statement)
    try:
        async with AsyncSessionLocal() as db:
            payload = await get_project_monitoring_latest(db, data["active_project"])
        # Inventory stays batched: Sensor inventory, Actuator summaries and
        # electrical/profile/incident data each use one Project-scoped query.
        assert statements == 3
        device = next(item for item in payload["devices"] if item["id"] == data["active_device"])
        assert len(device["sensors"]) == 6
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", count_statement)
        async with AsyncSessionLocal() as db:
            await db.execute(delete(Sensor).where(Sensor.id.in_(extra_sensor_ids)))
            await db.commit()


@pytest.mark.asyncio
async def test_actuator_history_uses_confirmed_transitions_and_deduplicates_reports(
    visibility_data,
) -> None:
    data = visibility_data
    actuator_id: int | None = None
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as db:
        actuator = Actuator(
            device_id=data["active_device"],
            sequence_number=99,
            code=f"MONITOR-{data['active_project']}-{data['active_device']}",
            name="Bơm monitoring test",
        )
        db.add(actuator)
        await db.flush()
        actuator_id = actuator.id

        assert await record_actuator_reported_state(
            db,
            actuator=actuator,
            state=False,
            source="PERIODIC_STATUS",
            received_at=now - timedelta(minutes=8),
        )
        assert not await record_actuator_reported_state(
            db,
            actuator=actuator,
            state=False,
            source="PERIODIC_STATUS",
            received_at=now - timedelta(minutes=7),
        )
        assert await record_actuator_reported_state(
            db,
            actuator=actuator,
            state=True,
            source="COMMAND_ACK",
            received_at=now - timedelta(minutes=2),
        )
        await db.commit()

    try:
        headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            inventory = await client.get(
                f"/api/v1/projects/{data['active_project']}/monitoring/inventory",
                headers=headers,
            )
            assert inventory.status_code == 200
            device = next(item for item in inventory.json()["devices"] if item["id"] == data["active_device"])
            assert [item["id"] for item in device["actuators"]] == [actuator_id]
            assert device["actuators"][0]["reported_state"] is True

            response = await client.get(
                f"/api/v1/projects/{data['active_project']}/devices/{data['active_device']}/monitoring/actuator-history",
                params={"range": "1h"},
                headers=headers,
            )
            assert response.status_code == 200
            item = next(item for item in response.json()["items"] if item["actuator_id"] == actuator_id)
            assert [point["state"] for point in item["points"]] == [False, True]
            assert item["statistics"]["on_count"] == 1
            assert item["statistics"]["off_count"] == 1
    finally:
        async with AsyncSessionLocal() as db:
            if actuator_id is not None:
                await db.execute(
                    delete(ActuatorStateHistory).where(
                        ActuatorStateHistory.actuator_id == actuator_id
                    )
                )
                await db.execute(delete(Actuator).where(Actuator.id == actuator_id))
                await db.commit()
