from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.models.user import User
from app.schemas.project import ProjectDeviceConfig
from app.services.project_device_config_service import export_project_device_config

router = APIRouter(prefix="/projects", tags=["Project device config"])


@router.get("/{project_id}/device-config", response_model=ProjectDeviceConfig, deprecated=True)
@router.get("/{project_id}/device-config/export", response_model=ProjectDeviceConfig)
async def export_config(
    project_id: int,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
) -> ProjectDeviceConfig:
    return await export_project_device_config(db, project_id=project_id)
