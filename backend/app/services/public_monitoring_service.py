from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import MonitoringRange, ProjectStatus
from app.models.device import Device
from app.models.device_template import DeviceTemplate
from app.models.project import Project
from app.models.project_settings import ProjectPublicSettings
from app.services.energy_monitor_read_service import (
    get_energy_monitor_overview,
    get_energy_power_series,
)
from app.services.monitoring_service import (
    get_project_monitoring_latest,
    get_project_monitoring_series,
    get_project_monitoring_summary,
)


async def require_public_project(
    db: AsyncSession,
) -> Project:
    """
    Resolve Project được phép hiển thị trên Public Monitoring.

    Public Monitoring không nhận project_id từ browser.
    Project được cố định bằng PUBLIC_MONITORING_PROJECT_ID
    và phải:
    - tồn tại;
    - đang ACTIVE;
    - chưa bị xóa;
    - đã bật ProjectPublicSettings.enabled.
    """

    project_id = settings.public_monitoring_project_id

    if project_id is None:
        raise HTTPException(
            status_code=404,
            detail="Theo dõi từ xa chưa được cấu hình",
        )

    project = await db.scalar(
        select(Project)
        .join(
            ProjectPublicSettings,
            ProjectPublicSettings.project_id == Project.id,
        )
        .where(
            Project.id == project_id,
            ProjectPublicSettings.enabled.is_(True),
            Project.status == ProjectStatus.ACTIVE,
            Project.is_deleted.is_(False),
            Project.deleted_at.is_(None),
        )
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy trang theo dõi công khai",
        )

    return project


def _build_public_device(
    device: dict,
) -> dict:
    """
    Tạo payload Device cho Public Monitoring.

    Quan trọng:
    - Giữ sensors.
    - Giữ actuators.
    - Không xóa actuator trong chế độ read-only.
    - Read-only chỉ có nghĩa là Public API không expose
      endpoint command/mutation.
    """

    public_device = dict(device)

    # Clone các collection để Public payload không chia sẻ trực tiếp
    # mutable list với payload từ monitoring service.
    public_device["sensors"] = [
        dict(sensor)
        for sensor in device.get("sensors", [])
    ]

    # FIX:
    # Trước đây code gán:
    #
    # public_device["actuators"] = []
    #
    # làm Public Monitoring luôn thấy actuator = 0.
    #
    # Monitoring service đã tạo actuator read model an toàn,
    # nên giữ lại dữ liệu này cho giao diện read-only.
    public_device["actuators"] = [
        dict(actuator)
        for actuator in device.get("actuators", [])
    ]

    return public_device


async def get_public_overview(
    db: AsyncSession,
    project: Project,
) -> dict:
    """
    Read model chính cho trang Public Monitoring.

    Bao gồm:
    - Project metadata;
    - Project health/summary;
    - Devices;
    - Sensors;
    - Actuators read-only;
    - Energy Monitor;
    - Recent alerts.
    """

    summary = await get_project_monitoring_summary(
        db,
        project.id,
        project_status=project.status,
    )

    latest = await get_project_monitoring_latest(
        db,
        project.id,
    )

    # ------------------------------------------------------------------
    # Energy Monitor
    # ------------------------------------------------------------------

    energy_device = (
        await db.execute(
            select(
                Device.id,
                Device.code,
            )
            .join(
                DeviceTemplate,
                DeviceTemplate.id
                == Device.device_template_id,
            )
            .where(
                Device.project_id == project.id,
                Device.is_enabled.is_(True),
                Device.is_deleted.is_(False),
                Device.deleted_at.is_(None),
                DeviceTemplate.device_kind
                == "ENERGY_MONITOR",
            )
            .order_by(Device.id)
            .limit(1)
        )
    ).first()

    energy = None

    if energy_device is not None:
        energy = await get_energy_monitor_overview(
            db,
            project_id=project.id,
            device_id=energy_device.id,
        )

        # Không expose internal DB ID/template
        # không cần thiết cho Public Monitoring.
        energy["device"].pop(
            "id",
            None,
        )

        energy["device"].pop(
            "template",
            None,
        )

        # Không expose internal sensor ID
        # trong dedicated Energy Monitor payload.
        for measurement in energy[
            "measurements"
        ].values():
            measurement.pop(
                "sensor_id",
                None,
            )

    # ------------------------------------------------------------------
    # Devices / Sensors / Actuators
    # ------------------------------------------------------------------

    devices: list[dict] = []
    sensors: list[dict] = []

    for device in latest.get(
        "devices",
        [],
    ):
        public_device = _build_public_device(
            device,
        )

        devices.append(
            public_device,
        )

        # Flatten sensor list phục vụ các Sensor chart
        # của PublicMonitoringPage.
        for sensor in device.get(
            "sensors",
            [],
        ):
            sensors.append(
                {
                    "id": sensor["id"],
                    "code": sensor["code"],
                    "name": sensor["name"],
                    "device_code": device["code"],
                    "unit": sensor["unit"],
                    "connection_status": sensor[
                        "connection_status"
                    ],
                    "latest": sensor["latest"],
                }
            )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    #
    # Không expose project_id vì Project đã deployment-scoped.
    #
    # actuator_inventory vẫn giữ private vì Public page hiện không
    # cần read model đó.
    #
    # summary["actuators"] cũng tiếp tục bỏ ở đây vì trạng thái actuator
    # đã được expose theo từng devices[].actuators.
    #
    # Điều này tránh duplicate payload và tránh mở rộng Public contract
    # không cần thiết.
    # ------------------------------------------------------------------

    public_summary = {
        key: value
        for key, value in summary.items()
        if key
        not in {
            "project_id",
            "actuators",
            "actuator_inventory",
        }
    }

    # ------------------------------------------------------------------
    # Recent alerts
    # ------------------------------------------------------------------

    alerts = [
        {
            "severity": item["severity"],
            "status": item["status"],
            "message": item["message"],
            "started_at": item["started_at"],
        }
        for item in summary.get(
            "recent_alerts",
            [],
        )
    ]

    # ------------------------------------------------------------------
    # Response
    # ------------------------------------------------------------------

    return {
        "project": {
            "code": project.code,
            "name": project.name,
            "location": project.location,
        },
        "health": summary["health"],
        "summary": public_summary,
        "devices": devices,
        "sensors": sensors,
        "energy": energy,
        "alerts": alerts,
        "updated_at": (
            summary["freshness"][
                "last_received_at"
            ]
            or datetime.now(
                timezone.utc,
            )
        ),
    }


async def get_public_series(
    db: AsyncSession,
    project: Project,
    monitoring_range: MonitoringRange,
) -> dict:
    """
    Public Sensor telemetry history.

    Project ID không nhận từ client mà lấy trực tiếp
    từ Project đã được require_public_project xác thực.
    """

    return await get_project_monitoring_series(
        db,
        project_id=project.id,
        monitoring_range=monitoring_range,
    )


async def get_public_power_series(
    db: AsyncSession,
    project: Project,
    device_code: str,
    monitoring_range: MonitoringRange,
) -> dict:
    """
    Public POWER_W history của Energy Monitor.

    Chỉ chấp nhận Device:
    - thuộc Public Project hiện tại;
    - enabled;
    - chưa bị xóa;
    - template ENERGY_MONITOR.
    """

    device_id = await db.scalar(
        select(Device.id)
        .join(
            DeviceTemplate,
            DeviceTemplate.id
            == Device.device_template_id,
        )
        .where(
            Device.project_id == project.id,
            Device.code == device_code,
            Device.is_enabled.is_(True),
            Device.is_deleted.is_(False),
            Device.deleted_at.is_(None),
            DeviceTemplate.device_kind
            == "ENERGY_MONITOR",
        )
    )

    if device_id is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Không tìm thấy Energy Monitor "
                "công khai"
            ),
        )

    payload = await get_energy_power_series(
        db,
        project_id=project.id,
        device_id=device_id,
        monitoring_range=monitoring_range,
    )

    # Không expose internal DB IDs
    # không cần thiết ở Power Series endpoint.
    payload.pop(
        "device_id",
        None,
    )

    sensor = payload.get(
        "sensor",
    )

    if isinstance(
        sensor,
        dict,
    ):
        sensor.pop(
            "id",
            None,
        )

    return payload