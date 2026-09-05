import pytest
from pydantic import ValidationError

from app.api.v1 import devices, project_members, projects
from app.schemas.auth import ChangePasswordRequest


def test_change_password_requires_confirmation() -> None:
    with pytest.raises(ValidationError):
        ChangePasswordRequest(
            current_password="OldPassword1",
            new_password="NewPassword1",
            confirm_password="DifferentPassword1",
        )


def test_device_has_no_direct_member_api() -> None:
    paths = {route.path for route in devices.router.routes}
    project_paths = {route.path for route in project_members.router.routes}
    assert "/devices/{device_id}/members" not in paths
    assert "/devices/{device_id}/members/{user_id}" not in paths
    assert "/projects/{project_id}/members" in project_paths


def test_project_device_api_returns_collection_contract() -> None:
    paths = {route.path for route in projects.router.routes}
    assert "/projects/{project_id}/devices" in paths
    assert "/projects/{project_id}/device-config" in paths
    assert (
        "/projects/{project_id}/devices/{device_id}/mqtt-connection-config"
        in paths
    )


def test_device_api_only_exposes_simple_mqtt_configuration() -> None:
    paths = {route.path for route in devices.router.routes}
    assert "/devices/{device_id}/mqtt-config" in paths
    assert not any("credentials" in path for path in paths)
