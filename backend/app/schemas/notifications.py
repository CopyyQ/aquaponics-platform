from datetime import datetime

from typing import Literal

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RiskLevel = Literal["EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW"]
TELEGRAM_CHAT_ID_PATTERN = re.compile(r"^(?:-100|-)?[1-9][0-9]{4,19}$")


class NotificationRiskPolicy(BaseModel):
    risk_level: RiskLevel
    telegram_enabled: bool
    notify_on_open: bool = True
    notify_on_escalation: bool = True
    notify_on_recovery: bool = True
    notify_on_resolved: bool = True
    reminder_enabled: bool = False
    initial_reminder_seconds: int = Field(ge=0, le=2_592_000)
    repeat_interval_seconds: int = Field(ge=0, le=2_592_000)
    max_reminders: int = Field(ge=0, le=100)
    stop_reminders_on_ack: bool = True


class NotificationRecipientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    telegram_chat_id: str = Field(min_length=1, max_length=64)
    enabled: bool = True

    @field_validator("name", "telegram_chat_id", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> str:
        return str(value).strip()

    @model_validator(mode="after")
    def validate_chat_id(self) -> "NotificationRecipientCreate":
        if not TELEGRAM_CHAT_ID_PATTERN.fullmatch(self.telegram_chat_id):
            raise ValueError("Telegram Chat ID phải là một định danh số hợp lệ")
        return self


class NotificationRecipientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    telegram_chat_id: str | None = Field(default=None, min_length=1, max_length=64)
    enabled: bool | None = None

    @field_validator("name", "telegram_chat_id", mode="before")
    @classmethod
    def trim_optional_text(cls, value: object) -> object:
        return str(value).strip() if value is not None else value

    @model_validator(mode="after")
    def validate_chat_id(self) -> "NotificationRecipientUpdate":
        if self.telegram_chat_id is not None and not TELEGRAM_CHAT_ID_PATTERN.fullmatch(self.telegram_chat_id):
            raise ValueError("Telegram Chat ID phải là một định danh số hợp lệ")
        return self


class NotificationRecipientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    system_id: int = Field(validation_alias="project_id")
    name: str
    telegram_chat_id: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class NotificationSettingsUpdate(BaseModel):
    enabled: bool = True
    in_app_enabled: bool = True
    telegram_enabled: bool
    notify_alert_opened: bool
    notify_alert_resolved: bool
    notify_alert_recovered: bool = True
    notify_alert_escalated: bool = True
    notify_alert_reminder: bool = False
    reminder_interval_minutes: int | None = Field(default=None, ge=1, le=10080)
    minimum_business_risk_level: str = Field(default="LOW", pattern="^(EXTREME|VERY_HIGH|HIGH|MEDIUM|LOW_MEDIUM|LOW)$")
    risk_extreme_enabled: bool = True
    risk_very_high_enabled: bool = True
    risk_high_enabled: bool = True
    risk_medium_enabled: bool = True
    risk_low_medium_enabled: bool = True
    risk_low_enabled: bool = True
    risk_policies: list[NotificationRiskPolicy] = []

    @model_validator(mode="after")
    def validate_risk_policies(self) -> "NotificationSettingsUpdate":
        if self.risk_policies:
            levels = [item.risk_level for item in self.risk_policies]
            expected = {"EXTREME", "VERY_HIGH", "HIGH", "MEDIUM", "LOW_MEDIUM", "LOW"}
            if len(levels) != 6 or set(levels) != expected:
                raise ValueError("Cần cấu hình đúng một policy cho mỗi mức rủi ro")
            for item in self.risk_policies:
                if item.reminder_enabled and (item.initial_reminder_seconds <= 0 or item.repeat_interval_seconds <= 0 or item.max_reminders <= 0):
                    raise ValueError("Policy bật nhắc lại cần thời gian và số lần nhắc lớn hơn 0")
        return self


class NotificationSettingsRead(NotificationSettingsUpdate):
    telegram_bot_configured: bool
    notification_generation: int = 0
    recipients: list[NotificationRecipientRead]


class TestMessageResult(BaseModel):
    sent: bool
    detail: str


class PublicSettingsUpdate(BaseModel):
    enabled: bool


class PublicSettingsRead(PublicSettingsUpdate):
    remote_monitoring_available: bool
