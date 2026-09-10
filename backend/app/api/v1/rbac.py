from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.permission import Permission, Role, RoleAssignment, RolePermission, UserPermissionOverride
from app.models.project import Project
from app.models.user import User
from app.services.permission_service import get_effective_permissions
from app.services.public_identity_service import (
    PublicIdentityNotFoundError, get_system_by_public_id, get_user_by_public_id,
)

router = APIRouter()
SYSTEM_ROLES = frozenset({"ADMIN", "OWNER", "TECHNICIAN", "VIEWER"})


class PermissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=3, max_length=120, pattern=r"^[a-z][a-z0-9_.]*$")
    resource: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=80)
    description: str | None = None


class PermissionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    resource: str | None = Field(default=None, min_length=1, max_length=80)
    action: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    enabled: bool | None = None


class PermissionRead(PermissionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    enabled: bool


class RoleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=2, max_length=50, pattern=r"^[A-Z][A-Z0-9_]*$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    enabled: bool | None = None


class RoleRead(RoleCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_system: bool
    enabled: bool


class PermissionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permission_ids: set[int]


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    role_id: int
    scope_type: Literal["GLOBAL", "AQUAPONICS_SYSTEM"]
    scope_id: UUID | None = None
    expires_at: datetime | None = None


class AssignmentRead(AssignmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class OverrideWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    permission_id: int
    scope_type: Literal["GLOBAL", "AQUAPONICS_SYSTEM"]
    scope_id: UUID | None = None
    effect: Literal["ALLOW", "DENY"]


class OverrideUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effect: Literal["ALLOW", "DENY"]


class OverrideRead(OverrideWrite):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: UUID
    created_at: datetime
    updated_at: datetime


def _validate_scope(scope_type: str, scope_id: UUID | None) -> None:
    if (scope_type == "GLOBAL") != (scope_id is None):
        raise HTTPException(422, "GLOBAL requires null scope_id; AQUAPONICS_SYSTEM requires scope_id")


async def _entity(db: AsyncSession, model, entity_id: int, label: str):
    row = await db.get(model, entity_id)
    if row is None:
        raise HTTPException(404, f"{label} không tồn tại")
    return row


async def _public_user(db: AsyncSession, user_id: UUID) -> User:
    try: return await get_user_by_public_id(db, user_id)
    except PublicIdentityNotFoundError as exc: raise HTTPException(404, str(exc)) from exc


async def _internal_scope_id(db: AsyncSession, scope_type: str, scope_id: UUID | None) -> int | None:
    _validate_scope(scope_type, scope_id)
    if scope_id is None: return None
    try: return (await get_system_by_public_id(db, scope_id)).id
    except PublicIdentityNotFoundError as exc: raise HTTPException(404, str(exc)) from exc


async def _assignment_read(db: AsyncSession, row: RoleAssignment) -> AssignmentRead:
    user = await db.get(User, row.user_id)
    system = await db.get(Project, row.scope_id) if row.scope_id is not None else None
    return AssignmentRead(id=row.id, user_id=user.public_id, role_id=row.role_id,
        scope_type=row.scope_type, scope_id=system.public_id if system else None,
        expires_at=row.expires_at, created_at=row.created_at, updated_at=row.updated_at)


async def _override_read(db: AsyncSession, row: UserPermissionOverride) -> OverrideRead:
    user = await db.get(User, row.user_id)
    system = await db.get(Project, row.scope_id) if row.scope_id is not None else None
    return OverrideRead(id=row.id, user_id=user.public_id, permission_id=row.permission_id,
        scope_type=row.scope_type, scope_id=system.public_id if system else None,
        effect=row.effect, created_at=row.created_at, updated_at=row.updated_at)


@router.get("/permissions", response_model=list[PermissionRead], tags=["Permissions"])
async def list_permissions(db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("permissions.read"))):
    return (await db.scalars(select(Permission).order_by(Permission.code))).all()


@router.post("/permissions", response_model=PermissionRead, status_code=201, tags=["Permissions"])
async def create_permission(payload: PermissionCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("permissions.create"))):
    if await db.scalar(select(Permission.id).where(Permission.code == payload.code)):
        raise HTTPException(409, "Permission code đã tồn tại")
    row = Permission(**payload.model_dump(), enabled=True); db.add(row); await db.commit(); await db.refresh(row); return row


@router.get("/permissions/{permission_id}", response_model=PermissionRead, tags=["Permissions"])
async def get_permission(permission_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("permissions.read"))):
    return await _entity(db, Permission, permission_id, "Permission")


@router.patch("/permissions/{permission_id}", response_model=PermissionRead, tags=["Permissions"])
async def update_permission(permission_id: int, payload: PermissionUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("permissions.update"))):
    row = await _entity(db, Permission, permission_id, "Permission")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key != "name": setattr(row, key, value)
    await db.commit(); await db.refresh(row); return row


@router.delete("/permissions/{permission_id}", status_code=204, tags=["Permissions"])
async def delete_permission(permission_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("permissions.delete"))):
    row = await _entity(db, Permission, permission_id, "Permission"); row.enabled = False; await db.commit(); return Response(status_code=204)


@router.post("/roles", response_model=RoleRead, status_code=201, tags=["Roles"])
async def create_role(payload: RoleCreate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.create"))):
    if payload.code in SYSTEM_ROLES or await db.scalar(select(Role.id).where(Role.code == payload.code)):
        raise HTTPException(409, "Role code được bảo vệ hoặc đã tồn tại")
    row = Role(**payload.model_dump(), is_system=False, enabled=True); db.add(row); await db.commit(); await db.refresh(row); return row


@router.get("/roles/{role_id}", response_model=RoleRead, tags=["Roles"])
async def get_role(role_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.read"))):
    return await _entity(db, Role, role_id, "Role")


@router.patch("/roles/{role_id}", response_model=RoleRead, tags=["Roles"])
async def update_role(role_id: int, payload: RoleUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.update"))):
    row = await _entity(db, Role, role_id, "Role")
    if row.is_system and payload.enabled is False: raise HTTPException(409, "Không thể vô hiệu hóa system role")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(row, key, value)
    await db.commit(); await db.refresh(row); return row


@router.delete("/roles/{role_id}", status_code=204, tags=["Roles"])
async def delete_role(role_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.delete"))):
    row = await _entity(db, Role, role_id, "Role")
    if row.is_system or row.code in SYSTEM_ROLES: raise HTTPException(409, "Không thể xóa system role")
    row.enabled = False; await db.commit(); return Response(status_code=204)


@router.get("/roles/{role_id}/permissions", response_model=list[PermissionRead], tags=["Role Permissions"])
async def role_permissions(role_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.permissions.read"))):
    await _entity(db, Role, role_id, "Role")
    return (await db.scalars(select(Permission).join(RolePermission).where(RolePermission.role_id == role_id).order_by(Permission.code))).all()


@router.put("/roles/{role_id}/permissions", response_model=list[PermissionRead], tags=["Role Permissions"])
async def replace_role_permissions(role_id: int, payload: PermissionSet, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.permissions.update"))):
    await _entity(db, Role, role_id, "Role")
    found = set((await db.scalars(select(Permission.id).where(Permission.id.in_(payload.permission_ids), Permission.enabled.is_(True)))).all()) if payload.permission_ids else set()
    if found != payload.permission_ids: raise HTTPException(422, "Permission không tồn tại hoặc bị vô hiệu hóa")
    current = set((await db.scalars(select(RolePermission.permission_id).where(RolePermission.role_id == role_id))).all())
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id.in_(current - found)))
    db.add_all(RolePermission(role_id=role_id, permission_id=pid) for pid in found - current)
    await db.commit(); return await role_permissions(role_id, db, _)


@router.post("/roles/{role_id}/permissions/{permission_id}", status_code=201, tags=["Role Permissions"])
async def grant_role_permission(role_id: int, permission_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.permissions.update"))):
    await _entity(db, Role, role_id, "Role"); await _entity(db, Permission, permission_id, "Permission")
    row = await db.scalar(select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id))
    if row is None: row = RolePermission(role_id=role_id, permission_id=permission_id); db.add(row); await db.commit()
    return {"role_id": role_id, "permission_id": permission_id}


@router.delete("/roles/{role_id}/permissions/{permission_id}", status_code=204, tags=["Role Permissions"])
async def revoke_role_permission(role_id: int, permission_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("roles.permissions.update"))):
    await db.execute(delete(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)); await db.commit(); return Response(status_code=204)


@router.get("/users/{user_id}/role-assignments", response_model=list[AssignmentRead], tags=["Role Assignments"])
async def list_assignments(user_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("role_assignments.read"))):
    user = await _public_user(db, user_id)
    rows = (await db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id).order_by(RoleAssignment.id))).all()
    return [await _assignment_read(db, row) for row in rows]


@router.post("/role-assignments", response_model=AssignmentRead, status_code=201, tags=["Role Assignments"])
async def create_assignment(payload: AssignmentCreate, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("role_assignments.update"))):
    user = await _public_user(db, payload.user_id)
    scope_id = await _internal_scope_id(db, payload.scope_type, payload.scope_id)
    role = await _entity(db, Role, payload.role_id, "Role")
    if not role.enabled: raise HTTPException(422, "Role đã bị vô hiệu hóa")
    if payload.scope_type == "AQUAPONICS_SYSTEM":
        if role.code not in {"OWNER", "TECHNICIAN", "VIEWER"}: raise HTTPException(422, "Role không phù hợp project scope")
    existing = await db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.role_id == payload.role_id,
        RoleAssignment.scope_type == payload.scope_type, RoleAssignment.scope_id.is_(None) if scope_id is None else RoleAssignment.scope_id == scope_id))
    if existing: raise HTTPException(409, "Role assignment đã tồn tại")
    row = RoleAssignment(user_id=user.id, role_id=payload.role_id, scope_type=payload.scope_type,
        scope_id=scope_id, expires_at=payload.expires_at, created_by=actor.id)
    db.add(row); await db.commit(); await db.refresh(row); return await _assignment_read(db, row)


@router.delete("/role-assignments/{assignment_id}", status_code=204, tags=["Role Assignments"])
async def delete_assignment(assignment_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("role_assignments.update"))):
    row = await _entity(db, RoleAssignment, assignment_id, "Role assignment"); await db.delete(row); await db.commit(); return Response(status_code=204)


@router.get("/users/{user_id}/permission-overrides", response_model=list[OverrideRead], tags=["Permission Overrides"])
async def list_overrides(user_id: UUID, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("user_permissions.read"))):
    user = await _public_user(db, user_id)
    rows = (await db.scalars(select(UserPermissionOverride).where(UserPermissionOverride.user_id == user.id).order_by(UserPermissionOverride.id))).all()
    return [await _override_read(db, row) for row in rows]


@router.post("/users/{user_id}/permission-overrides", response_model=OverrideRead, status_code=201, tags=["Permission Overrides"])
async def put_override(user_id: UUID, payload: OverrideWrite, db: AsyncSession = Depends(get_db), actor: User = Depends(require_permission("user_permissions.update"))):
    user = await _public_user(db, user_id); scope_id = await _internal_scope_id(db, payload.scope_type, payload.scope_id)
    await _entity(db, Permission, payload.permission_id, "Permission")
    row = await db.scalar(select(UserPermissionOverride).where(UserPermissionOverride.user_id == user.id,
        UserPermissionOverride.permission_id == payload.permission_id, UserPermissionOverride.scope_type == payload.scope_type,
        UserPermissionOverride.scope_id.is_(None) if scope_id is None else UserPermissionOverride.scope_id == scope_id))
    if row is None: row = UserPermissionOverride(user_id=user.id, permission_id=payload.permission_id,
        scope_type=payload.scope_type, scope_id=scope_id, effect=payload.effect, created_by=actor.id); db.add(row)
    else: row.effect = payload.effect
    await db.commit(); await db.refresh(row); return await _override_read(db, row)


@router.patch("/users/{user_id}/permission-overrides/{override_id}", response_model=OverrideRead, tags=["Permission Overrides"])
async def patch_override(user_id: UUID, override_id: int, payload: OverrideUpdate, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("user_permissions.update"))):
    user = await _public_user(db, user_id)
    row = await db.scalar(select(UserPermissionOverride).where(UserPermissionOverride.id == override_id, UserPermissionOverride.user_id == user.id))
    if row is None: raise HTTPException(404, "Permission override không tồn tại")
    row.effect = payload.effect; await db.commit(); await db.refresh(row); return await _override_read(db, row)


@router.delete("/users/{user_id}/permission-overrides/{override_id}", status_code=204, tags=["Permission Overrides"])
async def delete_override(user_id: UUID, override_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("user_permissions.update"))):
    user = await _public_user(db, user_id)
    row = await db.scalar(select(UserPermissionOverride).where(UserPermissionOverride.id == override_id, UserPermissionOverride.user_id == user.id))
    if row is None: raise HTTPException(404, "Permission override không tồn tại")
    await db.delete(row); await db.commit(); return Response(status_code=204)


@router.get("/users/{user_id}/effective-permissions", tags=["Permissions"])
async def effective_permissions(user_id: UUID, system_id: UUID | None = Query(default=None), db: AsyncSession = Depends(get_db), _: User = Depends(require_permission("user_permissions.read"))):
    user = await _public_user(db, user_id)
    internal_system_id = await _internal_scope_id(
        db, "AQUAPONICS_SYSTEM" if system_id is not None else "GLOBAL", system_id
    )
    assignments = (await db.scalars(select(RoleAssignment).options(selectinload(RoleAssignment.role)).where(
        RoleAssignment.user_id == user.id,
        (RoleAssignment.scope_type == "GLOBAL") if internal_system_id is None else
        ((RoleAssignment.scope_type == "GLOBAL") | ((RoleAssignment.scope_type == "AQUAPONICS_SYSTEM") & (RoleAssignment.scope_id == internal_system_id)))
    ))).all()
    overrides = (await db.scalars(select(UserPermissionOverride).options(selectinload(UserPermissionOverride.permission)).where(
        UserPermissionOverride.user_id == user.id,
        (UserPermissionOverride.scope_type == "GLOBAL") if internal_system_id is None else
        ((UserPermissionOverride.scope_type == "GLOBAL") | ((UserPermissionOverride.scope_type == "AQUAPONICS_SYSTEM") & (UserPermissionOverride.scope_id == internal_system_id)))
    ))).all()
    roles = [{
        "id": a.role.id,
        "code": a.role.code,
        "scope_type": a.scope_type,
        "scope_id": system_id if a.scope_type == "AQUAPONICS_SYSTEM" else None,
    } for a in assignments]
    if user.role_id and not any(a.role_id == user.role_id and a.scope_type == "GLOBAL" for a in assignments):
        role = await db.get(Role, user.role_id)
        if role: roles.append({"id": role.id, "code": role.code, "scope_type": "GLOBAL", "scope_id": None})
    role_ids = {r["id"] for r in roles}
    role_permissions = list((await db.scalars(select(Permission.code).join(RolePermission).where(RolePermission.role_id.in_(role_ids)).distinct().order_by(Permission.code))).all()) if role_ids else []
    return {"user_id": user.public_id, "system_id": system_id, "roles": roles, "role_permissions": role_permissions,
            "allows": sorted(o.permission.code for o in overrides if o.effect == "ALLOW"),
            "denies": sorted(o.permission.code for o in overrides if o.effect == "DENY"),
            "effective_permissions": sorted(await get_effective_permissions(db, user, internal_system_id))}
