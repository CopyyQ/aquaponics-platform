from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    OWNER = "OWNER"
    TECHNICIAN = "TECHNICIAN"
    VIEWER = "VIEWER"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"
    SOFT_DELETED = "SOFT_DELETED"


class AquaponicsSystemStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"
    DISABLED = "DISABLED"


# Internal persistence code retains this compatibility name. Public schemas
# expose AquaponicsSystemStatus.
ProjectStatus = AquaponicsSystemStatus


class DeviceStatus(StrEnum):
    WAITING_CONNECTION = "WAITING_CONNECTION"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"


class DeviceType(StrEnum):
    SENSOR_DEVICE = "SENSOR_DEVICE"
    ACTUATOR_DEVICE = "ACTUATOR_DEVICE"


class MeasurementSemantics(StrEnum):
    GAUGE = "GAUGE"
    COUNTER = "COUNTER"


class SensorStatus(StrEnum):
    WAITING_CONNECTION = "WAITING_CONNECTION"
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"


class AggregatePeriod(StrEnum):
    HOUR = "HOUR"
    DAY = "DAY"


class MonitoringRange(StrEnum):
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWELVE_HOURS = "12h"
    TWENTY_FOUR_HOURS = "24h"
    THIRTY_DAYS = "30d"


class ThresholdMetricType(StrEnum):
    SENSOR_VALUE = "SENSOR_VALUE"
    VOLTAGE = "VOLTAGE"
    CURRENT = "CURRENT"


class ActuatorThresholdMetric(StrEnum):
    VOLTAGE = "VOLTAGE"
    CURRENT = "CURRENT"


class AlertResourceType(StrEnum):
    SENSOR = "SENSOR"
    ACTUATOR = "ACTUATOR"


class AlertDirection(StrEnum):
    BELOW = "BELOW"
    ABOVE = "ABOVE"


class AlertLifecycleStatus(StrEnum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    NORMALIZED = "NORMALIZED"
    RESOLVED = "RESOLVED"


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
