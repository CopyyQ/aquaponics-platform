from dataclasses import dataclass
import re

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actuator import Actuator
from app.models.actuator_model import ActuatorModel
from app.models.device import Device
from app.models.project import Project

_INVALID_CODE_CHARACTERS = re.compile(r"[^A-Z0-9_-]+")
_REPEATED_SEPARATORS = re.compile(r"[-_]{2,}")


@dataclass(frozen=True, slots=True)
class GeneratedActuatorIdentity:
    code: str
    display_name: str
    sequence_number: int


def _normalize_code_part(value: str) -> str:
    normalized = _INVALID_CODE_CHARACTERS.sub("-", value.strip().upper())
    return _REPEATED_SEPARATORS.sub("-", normalized).strip("-_")


def validate_local_actuator_code(
    code: str, *, project_code: str, device_code: str
) -> str:
    """Reject project/device-qualified codes at actuator creation boundaries."""
    normalized = _normalize_code_part(code)
    qualified_prefixes = (
        f"{_normalize_code_part(project_code)}-",
        f"{_normalize_code_part(device_code)}-",
        f"{_normalize_code_part(project_code)}-{_normalize_code_part(device_code)}-",
    )
    if normalized.startswith(qualified_prefixes):
        raise ValueError("Actuator code must be device-local")
    return normalized


async def generate_actuator_identity(
    db: AsyncSession,
    *,
    project: Project,
    device: Device,
    actuator_model: ActuatorModel,
) -> GeneratedActuatorIdentity:
    """Generate a device-local actuator identity while holding a transaction lock."""

    if db.bind is not None and db.bind.dialect.name == "postgresql":
        await db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {
                "lock_key": (
                    f"actuator-identity:{device.id}:{actuator_model.id}"
                )
            },
        )

    current_sequence = await db.scalar(
        select(func.max(Actuator.sequence_number))
        .where(
            Actuator.device_id == device.id,
            Actuator.actuator_model_id == actuator_model.id,
        )
    )
    sequence_number = int(current_sequence or 0) + 1
    suffix = f"-{sequence_number:02d}"
    raw_prefix = _normalize_code_part(actuator_model.code)
    prefix = raw_prefix[: 80 - len(suffix)].rstrip("-_")
    return GeneratedActuatorIdentity(
        code=f"{prefix}{suffix}",
        display_name=f"{actuator_model.name} {sequence_number:02d}",
        sequence_number=sequence_number,
    )
