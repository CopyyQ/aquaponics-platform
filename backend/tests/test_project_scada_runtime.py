from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import delete, event, select

from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.actuator import Actuator, ActuatorCommand
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor, SensorModel
from app.services.scada_runtime_service import get_scada_runtime
from test_visibility_authorization import visibility_data


def auth_header(user_id: int, token_version: int, role: str) -> dict[str, str]:
    token = create_access_token(
        str(user_id), {"role": role, "token_version": token_version}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_scada_runtime_is_project_scoped_and_uses_active_denominators(
    visibility_data,
) -> None:
    data = visibility_data
    viewer_headers = auth_header(data["viewer_id"], data["viewer_version"], "VIEWER")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/v1/projects/{data['active_project']}/scada/runtime",
            headers=viewer_headers,
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["project"]["id"] == data["active_project"]
        assert payload["summary"]["active_devices_total"] == 1
        assert payload["summary"]["disconnected_devices"] == 1
        assert payload["summary"]["disabled_devices"] == 0
        assert payload["summary"]["active_sensors_total"] == 1
        assert data["other_device"] not in {
            item["id"] for item in payload["inventory"]["devices"]
        }
        assert payload["summary"]["unplaced_entities"] == 0

        forbidden = await client.get(
            f"/api/v1/projects/{data['project_ids'][1]}/scada/runtime",
            headers=viewer_headers,
        )
        assert forbidden.status_code == 404

    async with AsyncSessionLocal() as db:
        device = await db.get(Device, data["active_device"])
        assert device is not None
        device.is_enabled = False
        await db.commit()
        project = await db.get(Project, data["active_project"])
        assert project is not None
        disabled_runtime = await get_scada_runtime(db, project)
        assert disabled_runtime.summary.active_devices_total == 0
        assert disabled_runtime.summary.disconnected_devices == 0
        assert disabled_runtime.summary.disabled_devices == 1
        assert disabled_runtime.summary.active_sensors_total == 0
        assert disabled_runtime.summary.disabled_sensors == 1
        assert [issue.id for issue in disabled_runtime.issues] == [
            f"device-{data['active_device']}-disabled"
        ]
        device.is_enabled = True
        await db.commit()


@pytest.mark.asyncio
async def test_scada_runtime_batches_latest_commands_and_query_count(
    visibility_data,
) -> None:
    data = visibility_data
    actuator_id: int | None = None
    command_id: int | None = None
    extra_sensor_ids: list[int] = []
    async with AsyncSessionLocal() as db:
        actuator = Actuator(
            device_id=data["active_device"],
            sequence_number=91,
            code=f"SCADA-PUMP-{data['active_project']}",
            name="Bơm SCADA test",
            is_enabled=True,
            desired_state=True,
            reported_state=False,
        )
        db.add(actuator)
        await db.flush()
        command = ActuatorCommand(
            actuator_id=actuator.id,
            desired_state=True,
            status="TIMEOUT",
            requested_by_user_id=data["admin_id"],
            requested_at=datetime.now(timezone.utc),
            timed_out_at=datetime.now(timezone.utc),
        )
        db.add(command)
        await db.commit()
        actuator_id = actuator.id
        command_id = command.id

        project = await db.get(Project, data["active_project"])
        assert project is not None
        statements = 0

        def count_statement(*_args) -> None:
            nonlocal statements
            statements += 1

        event.listen(engine.sync_engine, "before_cursor_execute", count_statement)
        try:
            runtime = await get_scada_runtime(db, project)
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", count_statement)
        assert statements <= 9
        assert runtime.summary.active_actuators_total == 1
        assert runtime.summary.actuators_out_of_sync == 1
        assert runtime.summary.commands_timeout == 1
        actuator_state = next(item for item in runtime.runtime.actuators if item.id == actuator.id)
        assert actuator_state.command_status == "TIMEOUT"
        assert any(issue.actuator_id == actuator.id for issue in runtime.issues)
        assert not any(
            item.entity_type == "ACTUATOR" and item.entity_id == actuator.id
            for item in runtime.unplaced_entities
        )

        model = await db.scalar(select(SensorModel).where(SensorModel.is_deleted.is_(False)))
        assert model is not None
        sensors = [
            Sensor(
                device_id=data["active_device"],
                sensor_model_id=model.id,
                code=f"SCADA-BATCH-{data['active_project']}-{index}",
                name=f"SCADA Batch {index}",
            )
            for index in range(5)
        ]
        db.add_all(sensors)
        await db.commit()
        extra_sensor_ids = [sensor.id for sensor in sensors]
        statements_with_more_sensors = 0

        def count_more(*_args) -> None:
            nonlocal statements_with_more_sensors
            statements_with_more_sensors += 1

        event.listen(engine.sync_engine, "before_cursor_execute", count_more)
        try:
            await get_scada_runtime(db, project)
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", count_more)
        assert statements_with_more_sensors == statements

    async with AsyncSessionLocal() as db:
        await db.execute(delete(Sensor).where(Sensor.id.in_(extra_sensor_ids)))
        if command_id is not None:
            await db.execute(delete(ActuatorCommand).where(ActuatorCommand.id == command_id))
        if actuator_id is not None:
            await db.execute(delete(Actuator).where(Actuator.id == actuator_id))
        await db.commit()
