from fastapi import APIRouter

from app.api.v1 import aquaponics_systems, auth, canonical_catalogs, canonical_operations, canonical_extensions, rbac, sensor_models

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(canonical_operations.router)
api_router.include_router(canonical_extensions.router)
api_router.include_router(rbac.router)
api_router.include_router(aquaponics_systems.router)
api_router.include_router(sensor_models.router)
api_router.include_router(canonical_catalogs.router)
