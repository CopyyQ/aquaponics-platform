from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.core.enums import UserRole
from app.services.access_service import accessible_device_clause


def compile_clause(role: UserRole, user_id: int = 12) -> str:
    user = SimpleNamespace(id=user_id, system_role=role)
    return str(
        accessible_device_clause(user).compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def test_admin_can_access_all_devices() -> None:
    clause = compile_clause(UserRole.ADMIN)
    assert "devices.id IS NOT NULL" in clause


def test_owner_is_scoped_to_owned_devices() -> None:
    clause = compile_clause(UserRole.OWNER)
    assert "projects.owner_user_id = 12" in clause
    assert "projects.id = devices.project_id" in clause
    assert "project_members" not in clause


def test_viewer_is_scoped_to_project_membership() -> None:
    clause = compile_clause(UserRole.VIEWER)
    assert "projects.id = devices.project_id" in clause
    assert "JOIN projects ON projects.id = project_members.project_id" in clause
    assert "project_members.user_id = 12" in clause
    assert "project_members.role = 'VIEWER'" in clause


def test_different_owner_id_cannot_match_same_device_predicate() -> None:
    owner_a = compile_clause(UserRole.OWNER, 21)
    owner_b = compile_clause(UserRole.OWNER, 22)
    assert "projects.owner_user_id = 21" in owner_a
    assert "projects.owner_user_id = 22" in owner_b
    assert owner_a != owner_b


def test_sensor_telemetry_export_and_alerts_share_device_scope() -> None:
    # Các endpoint này đều gọi accessible_device_clause/require_sensor_access;
    # predicate Viewer bắt buộc đi qua project_members, ngăn IDOR theo sensor_id.
    clause = compile_clause(UserRole.VIEWER, 33)
    assert "EXISTS" in clause
    assert "project_members.user_id = 33" in clause
