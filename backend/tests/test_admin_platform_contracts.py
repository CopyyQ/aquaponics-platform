from app.api.v1 import admin_alerts, admin_monitoring, admin_user_lifecycle, device_templates
from app.core.enums import UserRole, UserStatus
from app.schemas.device import DeviceCreate


def test_template_admin_api_contract() -> None:
    paths = {route.path for route in device_templates.router.routes}
    assert "/admin/device-templates" in paths
    assert "/admin/device-templates/{template_id}/sensors" in paths
    assert "/admin/device-templates/{template_id}/sensors/{mapping_id}" in paths
    assert "/admin/device-templates/{template_id}/actuators" in paths
    assert "/admin/device-templates/{template_id}/actuators/{mapping_id}" in paths
    assert "/admin/device-templates/actuator-current-profiles" in paths


def test_device_from_template_payload_keeps_project_out_of_body() -> None:
    payload = DeviceCreate(
        device_template_id=5,
        name="Thiết bị bể cá số 1",
        code="AQUA-MEKONG-DEVICE-01",
        installation_location="Bể cá khu A",
        notes="Thiết bị triển khai thực tế",
        create_default_sensors=True,
    )
    assert payload.device_template_id == 5
    assert "project_id" not in payload.model_dump()


def test_admin_monitoring_and_alert_context_routes_exist() -> None:
    monitoring_paths = {route.path for route in admin_monitoring.router.routes}
    alert_paths = {route.path for route in admin_alerts.router.routes}
    assert "/admin/monitoring/projects" in monitoring_paths
    assert "/admin/monitoring/projects/{project_id}" in monitoring_paths
    assert "/admin/alerts" in alert_paths
    assert "/admin/alerts/{alert_id}/acknowledge" in alert_paths
    assert "/admin/alerts/{alert_id}/resolve" in alert_paths


def test_admin_role_and_account_lifecycle_are_not_downgraded() -> None:
    assert UserRole.ADMIN.value == "ADMIN"
    assert UserStatus.LOCKED.value == "LOCKED"
    paths = {route.path for route in admin_user_lifecycle.router.routes}
    for action in ("activate", "disable", "lock", "unlock", "restore"):
        assert f"/admin/users/{{user_id}}/{action}" in paths
