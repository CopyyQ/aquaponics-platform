from sqlalchemy import Select, and_, exists, select
from sqlalchemy.orm import aliased

from app.core.enums import ProjectStatus, UserRole, UserStatus
from app.models.device import Device
from app.models.project import Project, ProjectMember
from app.models.user import User


def active_owner_clause(project: type[Project] = Project):
    owner = aliased(User)
    return exists(
        select(owner.id).where(
            owner.id == project.owner_user_id,
            owner.status == UserStatus.ACTIVE,
            owner.is_deleted.is_(False),
            owner.deleted_at.is_(None),
        )
    )


def active_project_clause(project: type[Project] = Project):
    return and_(
        project.status == ProjectStatus.ACTIVE,
        project.is_deleted.is_(False),
        project.deleted_at.is_(None),
        active_owner_clause(project),
    )


def existing_project_clause(project: type[Project] = Project):
    """Projects visible to Admin, including DISABLED but excluding soft-deleted rows."""
    return and_(
        project.is_deleted.is_(False),
        project.deleted_at.is_(None),
        active_owner_clause(project),
    )


def accessible_project_clause(user: User):
    if user.system_role == UserRole.ADMIN:
        return existing_project_clause(Project)
    if user.system_role == UserRole.OWNER:
        return (Project.owner_user_id == user.id) & active_project_clause(Project)
    return exists(
        select(ProjectMember.id).where(
            ProjectMember.project_id == Project.id,
            ProjectMember.user_id == user.id,
            ProjectMember.role == UserRole.VIEWER.value,
            active_project_clause(Project),
        )
    )


def accessible_device_clause(user: User):
    if user.system_role == UserRole.ADMIN:
        return and_(
            Device.id.is_not(None),
            exists(
                select(Project.id)
                .where(Project.id == Device.project_id, active_project_clause(Project))
                .correlate_except(Project)
            ),
        )
    if user.system_role == UserRole.OWNER:
        return exists(
            select(Project.id)
            .where(
                Project.id == Device.project_id,
                Project.owner_user_id == user.id,
                active_project_clause(Project),
            )
            .correlate_except(Project)
        )
    return exists(
        select(ProjectMember.id)
        .join(Project, Project.id == ProjectMember.project_id)
        .where(
            Project.id == Device.project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.role == UserRole.VIEWER.value,
            active_project_clause(Project),
        )
        .correlate_except(ProjectMember, Project)
    )


def scope_devices(query: Select, user: User) -> Select:
    return query.where(
        Device.is_deleted.is_(False),
        Device.deleted_at.is_(None),
        Device.is_enabled.is_(True),
        accessible_device_clause(user),
    )
