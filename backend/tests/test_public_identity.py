from uuid import UUID

import pytest

from app.models.actuator import Actuator
from app.models.device import Device
from app.models.project import Project
from app.models.sensor import Sensor
from app.models.user import User


@pytest.fixture(scope="session")
def disposable_runtime_fixture():
    """These metadata checks do not need the integration database fixture."""
    yield


@pytest.mark.parametrize("model", [User, Project, Device, Sensor, Actuator])
def test_core_entities_have_uuid4_public_identity(model) -> None:
    column = model.__table__.c.public_id

    assert column.primary_key is False
    assert column.nullable is False
    assert column.unique is True
    assert column.index is True

    generated = column.default.arg(None)
    assert isinstance(generated, UUID)
    assert generated.version == 4


def test_core_relations_keep_bigint_foreign_keys() -> None:
    assert Project.__table__.c.owner_user_id.type.python_type is int
    assert Device.__table__.c.aquaponics_system_id.type.python_type is int
    assert Sensor.__table__.c.device_id.type.python_type is int
    assert Actuator.__table__.c.device_id.type.python_type is int
