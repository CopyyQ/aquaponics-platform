from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    OWNER = "OWNER"
    VIEWER = "VIEWER"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"
    SOFT_DELETED = "SOFT_DELETED"


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
    DISABLED = "DISABLED"


class DeviceStatus(StrEnum):
    WAITING_CONNECTION = "WAITING_CONNECTION"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"


class DeviceKind(StrEnum):
    GENERIC = "GENERIC"
    ENERGY_MONITOR = "ENERGY_MONITOR"


class MeasurementSemantics(StrEnum):
    GAUGE = "GAUGE"
    COUNTER = "COUNTER"


class SensorStatus(StrEnum):
    WAITING_CONNECTION = "WAITING_CONNECTION"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"


class SensorPurpose(StrEnum):
    GENERAL = "GENERAL"
    ACTUATOR_FEEDBACK = "ACTUATOR_FEEDBACK"


class AggregatePeriod(StrEnum):
    HOUR = "HOUR"
    DAY = "DAY"


class MonitoringRange(StrEnum):
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWELVE_HOURS = "12h"
    TWENTY_FOUR_HOURS = "24h"
    ONE_MONTH = "1m"


class AlertType(StrEnum):
    BELOW_LOWER_THRESHOLD = "BELOW_LOWER_THRESHOLD"
    ABOVE_UPPER_THRESHOLD = "ABOVE_UPPER_THRESHOLD"
    SENSOR_OFFLINE = "SENSOR_OFFLINE"


class AlertSeverity(StrEnum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(StrEnum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
