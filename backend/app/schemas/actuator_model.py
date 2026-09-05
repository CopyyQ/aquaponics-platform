from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ActuatorModelFeedbackInput(BaseModel):
    feedback_role: str = Field(default="RUNNING_CURRENT", pattern="^(SUPPLY_VOLTAGE|RUNNING_CURRENT)$")
    sensor_model_id: int
    value_key: str = Field(default="current_a", pattern=r"^[a-z][a-z0-9_]*$", min_length=2, max_length=80)
    unit: str = Field(min_length=1, max_length=50)
    data_type: str = Field(default="FLOAT", pattern="^FLOAT$")
    default_lower_threshold: float | None = None
    default_upper_threshold: float | None = None
    is_required: bool = True
    is_enabled: bool = True
    display_order: int = Field(default=0, ge=0)

    @field_validator("default_upper_threshold")
    @classmethod
    def validate_threshold_order(cls, value: float | None, info):
        lower = info.data.get("default_lower_threshold")
        if value is not None and lower is not None and lower >= value:
            raise ValueError("Ngưỡng dưới phải nhỏ hơn ngưỡng trên")
        return value


class ActuatorModelFeedbackRead(ActuatorModelFeedbackInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sensor_model_code: str
    sensor_model_name: str


class ActuatorModelCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$", min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = None
    data_type: str = Field(default="BOOLEAN", pattern="^BOOLEAN$")
    default_state: bool = False
    is_active: bool = True
    feedbacks: list[ActuatorModelFeedbackInput] = Field(default_factory=list, max_length=2)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return str(value).strip().upper()


class ActuatorModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    default_state: bool | None = None
    is_active: bool | None = None
    feedbacks: list[ActuatorModelFeedbackInput] | None = Field(default=None, max_length=2)


class ActuatorModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: str | None
    data_type: str
    default_state: bool
    is_active: bool
    sort_order: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    feedbacks: list[ActuatorModelFeedbackRead] = Field(default_factory=list)
