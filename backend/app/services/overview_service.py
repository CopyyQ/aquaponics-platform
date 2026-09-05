from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.project_health_service import build_project_health_rows


async def get_user_overview(db: AsyncSession, actor: User) -> dict:
    rows = await build_project_health_rows(db, actor)
    return {
        "summary": {
            "total_projects": len(rows),
            "active_projects": len(rows),
            "attention_projects": sum(row["health_status"] != "HEALTHY" for row in rows),
            "online_devices": sum(row["online_device_count"] for row in rows),
            "offline_devices": sum(row["offline_device_count"] for row in rows),
            "online_sensors": sum(row["online_sensor_count"] for row in rows),
            "offline_sensors": sum(row["offline_sensor_count"] for row in rows),
            "open_alerts": sum(row["open_alert_count"] for row in rows),
            "latest_received_at": max(
                (row["last_telemetry_at"] for row in rows if row["last_telemetry_at"]),
                default=None,
            ),
        },
        "projects": rows,
    }
