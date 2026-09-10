from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    app_name: str = "Aquaponics Monitoring API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = 480
    database_url: str
    cors_origins: list[str] | str = ["http://localhost:5173"]
    fernet_key: str = "unused-mqtt-migration-key"
    mqtt_host: str = "mqtt"
    mqtt_public_host: str = "192.168.1.182"
    mqtt_port: int = 1883
    mqtt_public_port: int = 1883
    mqtt_authentication: bool = False
    mqtt_tls: bool = False
    mqtt_client_id: str = "aquaponics-backend"
    mqtt_telemetry_topic: str = "aquaponics/+/telemetry"
    mqtt_status_topic: str = "aquaponics/+/status"
    mqtt_command_topic: str = "aquaponics/{device_code}/commands"
    mqtt_ack_topic: str = "aquaponics/+/command-ack"
    mqtt_qos: int = Field(default=1, ge=0, le=2)
    actuator_command_timeout_seconds: int = 45
    mqtt_max_future_skew_seconds: int = 300
    mqtt_max_past_age_seconds: int = 2_592_000
    device_offline_seconds: int = 300
    sensor_offline_seconds: int = 300
    job_interval_seconds: int = 60
    telegram_bot_token: str | None = None
    telegram_connect_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    telegram_read_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    display_timezone: str = "Asia/Ho_Chi_Minh"
    telegram_device_sensor_limit: int = Field(default=6, ge=1, le=20)
    telegram_notify_actuator_ack: bool = False
    project_health_interval_seconds: int = Field(default=300, ge=60, le=3600)
    health_report_device_issue_limit: int = Field(default=3, ge=1, le=10)
    health_report_sensor_issue_limit: int = Field(default=6, ge=1, le=20)
    health_report_actuator_issue_limit: int = Field(default=5, ge=1, le=20)
    health_report_incident_limit: int = Field(default=5, ge=1, le=20)
    public_monitoring_project_id: int | None = Field(default=None, gt=0)

    default_admin_username: str = "admin"
    default_admin_password: str = Field(min_length=8)
    default_owner_username: str = "owner"
    reset_default_admin_password: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
