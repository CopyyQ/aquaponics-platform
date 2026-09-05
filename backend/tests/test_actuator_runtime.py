import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from sqlalchemy import delete, select

from app.core.enums import DeviceStatus, ProjectStatus, UserRole
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.actuator import Actuator, ActuatorCommand
from app.models.actuator_model import ActuatorModel
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.sensor_model import SensorModel
from app.models.user import User
from app.mqtt.handlers import handle_status


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        str(user.id),
        {"role": user.system_role.value, "token_version": user.token_version},
    )
    return {"Authorization": f"Bearer {token}"}


async def test_actuator_identity_removal_and_mqtt_config_contract() -> None:
    suffix = uuid4().hex[:8].upper()
    async with AsyncSessionLocal() as db:
        admin = await db.scalar(
            select(User).where(
                User.system_role == UserRole.ADMIN,
                User.is_deleted.is_(False),
            )
        )
        owner = await db.scalar(
            select(User).where(
                User.system_role == UserRole.OWNER,
                User.is_deleted.is_(False),
            )
        )
        actuator_model = await db.scalar(
            select(ActuatorModel).where(
                ActuatorModel.code == "IRRIGATION_PUMP",
                ActuatorModel.is_active.is_(True),
            )
        )
        sensor_model = await db.scalar(
            select(SensorModel).where(SensorModel.is_deleted.is_(False))
        )
        assert admin is not None
        assert owner is not None
        assert actuator_model is not None
        assert sensor_model is not None

        project = Project(
            owner_user_id=owner.id,
            code=f"ACT-{suffix}",
            name=f"Actuator test {suffix}",
            status=ProjectStatus.ACTIVE,
        )
        db.add(project)
        await db.flush()
        device = Device(
            project_id=project.id,
            code=f"CTRL-{suffix}",
            name=f"Controller {suffix}",
            status=DeviceStatus.ONLINE,
            is_enabled=True,
        )
        db.add(device)
        await db.flush()
        sensor = Sensor(
            device_id=device.id,
            sensor_model_id=sensor_model.id,
            code=f"SENSOR-{suffix}",
            name=f"Sensor {suffix}",
            is_enabled=True,
        )
        db.add(sensor)
        await db.commit()
        project_id = project.id
        device_id = device.id
        model_id = actuator_model.id
        sensor_id = sensor.id
        headers = auth_header(admin)

    created_ids: list[int] = []
    command_id: int | None = None
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            rejected = await client.post(
                f"/api/v1/projects/{project_id}/devices/{device_id}/actuators",
                json={
                    "actuator_model_id": model_id,
                    "code": "CLIENT-CODE",
                    "name": "Client name",
                },
                headers=headers,
            )
            assert rejected.status_code == 422

            async def create_one(location: str) -> httpx.Response:
                return await client.post(
                    (
                        f"/api/v1/projects/{project_id}/devices/"
                        f"{device_id}/actuators"
                    ),
                    json={
                        "actuator_model_id": model_id,
                        "location": location,
                        "notes": "Created by regression test",
                    },
                    headers=headers,
                )

            first_response, second_response = await asyncio.gather(
                create_one("Khu A"),
                create_one("Khu B"),
            )
            assert first_response.status_code == 201
            assert second_response.status_code == 201
            created = [first_response.json(), second_response.json()]
            created_ids = [item["id"] for item in created]
            assert {item["sequence_number"] for item in created} == {1, 2}
            assert {item["name"] for item in created} == {
                "Bơm tưới 01",
                "Bơm tưới 02",
            }
            assert len({item["code"] for item in created}) == 2
            assert all(item["reported_state"] is None for item in created)
            assert all(item["desired_state"] is False for item in created)
            assert all(
                item["actuator_model"]["code"] == "IRRIGATION_PUMP"
                for item in created
            )

            config_response = await client.get(
                (
                    f"/api/v1/projects/{project_id}/devices/{device_id}/"
                    "mqtt-connection-config"
                ),
                headers=headers,
            )
            assert config_response.status_code == 200
            assert config_response.headers["content-type"].startswith(
                "application/json"
            )
            assert "mqtt-config.json" in config_response.headers[
                "content-disposition"
            ]
            config = config_response.json()
            assert config["schema_version"] == "2.0"
            assert config["project"]["code"] == f"ACT-{suffix}"
            assert config["device"]["code"] == f"CTRL-{suffix}"
            assert len(config["sensors"]) == 1
            assert {
                item["actuator_code"] for item in config["actuators"]
            } == {item["code"] for item in created}
            assert config["mqtt"]["topics"]["commands"].endswith("/commands")
            assert config["mqtt"]["topics"]["command_ack"].endswith(
                "/command-ack"
            )
            assert "status" in config["payload_contracts"]["status"]["payload"]
            assert "sent_at" in config["payload_contracts"]["status"]["payload"]

            disabled_id = created_ids[0]
            disabled = await client.post(
                (
                    f"/api/v1/projects/{project_id}/devices/{device_id}/"
                    f"actuators/{disabled_id}/disable"
                ),
                json={"reason": "Regression test"},
                headers=headers,
            )
            assert disabled.status_code == 204
            current_list = await client.get(
                f"/api/v1/projects/{project_id}/devices/{device_id}/actuators",
                headers=headers,
            )
            assert current_list.status_code == 200
            assert {item["id"] for item in current_list.json()} == set(
                created_ids
            )
            config_after_disable = await client.get(
                (
                    f"/api/v1/projects/{project_id}/devices/{device_id}/"
                    "mqtt-connection-config"
                ),
                headers=headers,
            )
            assert {
                item["actuator_code"]
                for item in config_after_disable.json()["actuators"]
            } == {created[1]["code"]}

        async with AsyncSessionLocal() as db:
            command = ActuatorCommand(
                actuator_id=created_ids[1],
                desired_state=True,
                status="PENDING",
                requested_by_user_id=admin.id,
                requested_at=datetime.now(UTC),
            )
            db.add(command)
            await db.commit()
            command_id = command.id

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            blocked = await client.delete(
                (
                    f"/api/v1/projects/{project_id}/devices/{device_id}/"
                    f"actuators/{created_ids[1]}"
                ),
                headers=headers,
            )
            assert blocked.status_code == 409

        async with AsyncSessionLocal() as db:
            command = await db.get(ActuatorCommand, command_id)
            assert command is not None
            command.status = "ACKNOWLEDGED"
            await db.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            removed = await client.delete(
                (
                    f"/api/v1/projects/{project_id}/devices/{device_id}/"
                    f"actuators/{created_ids[1]}"
                ),
                headers=headers,
            )
            assert removed.status_code == 204
            current_list = await client.get(
                f"/api/v1/projects/{project_id}/devices/{device_id}/actuators",
                headers=headers,
            )
            assert {item["id"] for item in current_list.json()} == {
                created_ids[0]
            }
            config_after_remove = await client.get(
                (
                    f"/api/v1/projects/{project_id}/devices/{device_id}/"
                    "mqtt-connection-config"
                ),
                headers=headers,
            )
            assert config_after_remove.json()["actuators"] == []

        async with AsyncSessionLocal() as db:
            assert await db.get(ActuatorCommand, command_id) is not None
            removed_actuator = await db.get(Actuator, created_ids[1])
            assert removed_actuator is not None
            assert removed_actuator.removed_at is not None
            assert removed_actuator.is_enabled is False
    finally:
        async with AsyncSessionLocal() as db:
            if created_ids:
                await db.execute(
                    delete(AuditLog).where(
                        AuditLog.entity_type == "ACTUATOR",
                        AuditLog.entity_id.in_(created_ids),
                    )
                )
            await db.execute(
                delete(AuditLog).where(
                    AuditLog.entity_type == "DEVICE",
                    AuditLog.entity_id == device_id,
                )
            )
            if command_id is not None:
                await db.execute(
                    delete(ActuatorCommand).where(
                        ActuatorCommand.id == command_id
                    )
                )
            await db.execute(
                delete(Actuator).where(Actuator.device_id == device_id)
            )
            await db.execute(delete(Sensor).where(Sensor.id == sensor_id))
            await db.execute(delete(Device).where(Device.id == device_id))
            await db.execute(delete(Project).where(Project.id == project_id))
            await db.commit()
        await engine.dispose()


async def test_mqtt_status_updates_device_scoped_actuator_without_rewriting_desired_or_terminal_commands(caplog) -> None:
    suffix = uuid4().hex[:8].upper()
    now = datetime.now(UTC).replace(microsecond=0)
    async with AsyncSessionLocal() as db:
        owner = await db.scalar(select(User).where(User.system_role == UserRole.OWNER, User.is_deleted.is_(False)))
        actuator_model = await db.scalar(select(ActuatorModel).where(ActuatorModel.is_active.is_(True)))
        assert owner is not None and actuator_model is not None
        project = Project(owner_user_id=owner.id, code=f"MQTT-ACT-{suffix}", name="MQTT actuator test", status=ProjectStatus.ACTIVE)
        db.add(project)
        await db.flush()
        device = Device(project_id=project.id, code=f"MQTT-DEV-{suffix}", name="MQTT Device", status=DeviceStatus.OFFLINE, is_enabled=True)
        other_device = Device(project_id=project.id, code=f"MQTT-OTHER-{suffix}", name="Other Device", status=DeviceStatus.ONLINE, is_enabled=True)
        db.add_all([device, other_device])
        await db.flush()
        actuator = Actuator(device_id=device.id, actuator_model_id=actuator_model.id, sequence_number=1, code="PUMP-01", name="Bơm tưới", is_enabled=True, desired_state=True, reported_state=False)
        other_actuator = Actuator(device_id=other_device.id, actuator_model_id=actuator_model.id, sequence_number=1, code="PUMP-01", name="Bơm khác", is_enabled=True, desired_state=False, reported_state=False)
        db.add_all([actuator, other_actuator])
        await db.flush()
        command = ActuatorCommand(actuator_id=actuator.id, desired_state=True, status="PUBLISHED", requested_by_user_id=owner.id, requested_at=now - timedelta(seconds=1))
        terminal = ActuatorCommand(actuator_id=actuator.id, desired_state=True, status="TIMEOUT", requested_by_user_id=owner.id, requested_at=now - timedelta(minutes=2), timed_out_at=now - timedelta(minutes=1))
        db.add_all([command, terminal])
        await db.commit()
        ids = project.id, device.id, other_device.id, actuator.id, other_actuator.id, command.id, terminal.id

    async def status(sent_at: datetime, state: bool, code: str = "PUMP-01") -> None:
        await handle_status(f"MQTT-DEV-{suffix}", json.dumps({"status": "ONLINE", "sent_at": sent_at.isoformat(), "actuators": [{"actuator_code": code, "state": state}]}).encode())

    try:
        await status(now - timedelta(seconds=2), False)  # OFF is persisted first.
        await status(now, True)  # ON confirms the outstanding command.
        async with AsyncSessionLocal() as db:
            after_state_change = (await db.get(Actuator, ids[3])).last_reported_at
        await status(now, True)  # Same-state heartbeat still refreshes freshness.
        async with AsyncSessionLocal() as db:
            after_same_state = (await db.get(Actuator, ids[3])).last_reported_at
        assert after_state_change is not None and after_same_state is not None
        assert after_same_state > after_state_change
        await status(now - timedelta(seconds=1), False)  # late packet cannot revert ON.
        await status(now + timedelta(seconds=1), True, "UNKNOWN-XYZ")
        async with AsyncSessionLocal() as db:
            before_rejected_status = (await db.get(Actuator, ids[3])).last_reported_at
        await status(now - timedelta(days=31), False)  # Invalid heartbeat is ignored.
        async with AsyncSessionLocal() as db:
            stored = await db.get(Actuator, ids[3])
            stored_other = await db.get(Actuator, ids[4])
            acknowledged = await db.get(ActuatorCommand, ids[5])
            terminal_command = await db.get(ActuatorCommand, ids[6])
            assert stored is not None and stored_other is not None and acknowledged is not None and terminal_command is not None
            assert stored.desired_state is True
            assert stored.reported_state is True
            assert stored.last_reported_at is not None
            assert stored.last_reported_at >= after_same_state
            assert stored.last_reported_at == before_rejected_status
            assert stored.reported_state_at == now
            assert acknowledged.status == "ACKNOWLEDGED"
            assert stored_other.reported_state is False  # Same code on another Device is untouched.
            assert terminal_command.status == "TIMEOUT"
        assert "event=mqtt_actuator_unknown" in caplog.text
    finally:
        async with AsyncSessionLocal() as db:
            await db.execute(delete(ActuatorCommand).where(ActuatorCommand.id.in_([ids[5], ids[6]])))
            await db.execute(delete(Actuator).where(Actuator.id.in_([ids[3], ids[4]])))
            await db.execute(delete(Device).where(Device.id.in_([ids[1], ids[2]])))
            await db.execute(delete(Project).where(Project.id == ids[0]))
            await db.commit()
