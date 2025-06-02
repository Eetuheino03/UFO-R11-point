"""Constants for the UFO-R11 SmartIR integration."""
from __future__ import annotations

from typing import Final

# Integration constants
DOMAIN: Final = "ufo_r11_smartir"
PLATFORM: Final = "climate"
MANUFACTURER: Final = "MOES"
MODEL: Final = "UFO-R11"

# Configuration constants
CONF_DEVICE_ID: Final = "device_id"
CONF_DEVICE_NAME: Final = "device_name"
CONF_MQTT_TOPIC: Final = "mqtt_topic"
CONF_DEVICE_TYPE: Final = "device_type"
CONF_CODE_SOURCE: Final = "code_source"
CONF_TEMPLATE: Final = "template"

# Device types
DEVICE_TYPE_AC: Final = "air_conditioner"
DEVICE_TYPE_TV: Final = "television"
DEVICE_TYPE_CUSTOM: Final = "custom"

DEVICE_TYPES: Final = [
    DEVICE_TYPE_AC,
    DEVICE_TYPE_TV,
    DEVICE_TYPE_CUSTOM,
]

# Code sources
CODE_SOURCE_POINTCODES: Final = "pointcodes"
CODE_SOURCE_LEARN: Final = "learn"
CODE_SOURCE_IMPORT: Final = "import"
CODE_SOURCE_TEMPLATE: Final = "template"

CODE_SOURCES: Final = [
    CODE_SOURCE_POINTCODES,
    CODE_SOURCE_LEARN,
    CODE_SOURCE_IMPORT,
    CODE_SOURCE_TEMPLATE,
]

# MQTT constants
MQTT_TOPIC_PREFIX: Final = "zigbee2mqtt"
MQTT_COMMAND_SET: Final = "set"
MQTT_COMMAND_GET: Final = "get"
MQTT_IR_CODE_FIELD: Final = "ir_code_to_send"
MQTT_LEARNED_CODE_FIELD: Final = "learned_ir_code"

# Climate constants
DEFAULT_MIN_TEMP: Final = 16
DEFAULT_MAX_TEMP: Final = 30
DEFAULT_TARGET_TEMP: Final = 24
DEFAULT_TEMP_STEP: Final = 1

# Temperature range from Point-codes
POINTCODES_MIN_TEMP: Final = 17
POINTCODES_MAX_TEMP: Final = 30

# HVAC modes
HVAC_MODE_OFF: Final = "off"
HVAC_MODE_COOL: Final = "cool"
HVAC_MODE_HEAT: Final = "heat"
HVAC_MODE_DRY: Final = "dry"
HVAC_MODE_FAN_ONLY: Final = "fan_only"
HVAC_MODE_AUTO: Final = "auto"
HVAC_MODE_SLEEP: Final = "sleep"

SUPPORTED_HVAC_MODES: Final = [
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    HVAC_MODE_SLEEP,
]

# Fan modes
FAN_LOW: Final = "low"
FAN_MEDIUM: Final = "medium"
FAN_HIGH: Final = "high"
FAN_AUTO: Final = "auto"

SUPPORTED_FAN_MODES: Final = [
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
]

# Swing modes
SWING_OFF: Final = "off"
SWING_VERTICAL: Final = "vertical"
SWING_HORIZONTAL: Final = "horizontal"
SWING_BOTH: Final = "both"

SUPPORTED_SWING_MODES: Final = [
    SWING_OFF,
    SWING_VERTICAL,
]

# Service names
SERVICE_LEARN_IR_CODE: Final = "learn_ir_code"
SERVICE_EXPORT_SMARTIR: Final = "export_smartir"
SERVICE_IMPORT_CODES: Final = "import_codes"
SERVICE_TEST_COMMAND: Final = "test_command"

# Coordinator update interval
UPDATE_INTERVAL: Final = 30  # seconds

# Learning timeout
LEARN_TIMEOUT: Final = 30  # seconds

# Error messages
ERROR_DEVICE_NOT_FOUND: Final = "device_not_found"
ERROR_MQTT_CONNECTION: Final = "mqtt_connection_failed"
ERROR_INVALID_CODE: Final = "invalid_ir_code"
ERROR_TIMEOUT: Final = "learning_timeout"
ERROR_UNKNOWN: Final = "unknown_error"

# Attributes
ATTR_DEVICE_ID: Final = "device_id"
ATTR_COMMAND_NAME: Final = "command_name"
ATTR_TIMEOUT: Final = "timeout"
ATTR_OUTPUT_PATH: Final = "output_path"
ATTR_IR_CODE: Final = "ir_code"
ATTR_LAST_COMMAND: Final = "last_command"
ATTR_COMMAND_TIME: Final = "command_time"
ATTR_AVAILABLE_CODES: Final = "available_codes"
ATTR_DEVICE_TEMPLATE: Final = "device_template"

# Default configuration
DEFAULT_CONFIG: Final = {
    CONF_DEVICE_TYPE: DEVICE_TYPE_AC,
    CONF_CODE_SOURCE: CODE_SOURCE_POINTCODES,
}

# Point-codes dataset size
POINTCODES_COMMAND_COUNT: Final = 55