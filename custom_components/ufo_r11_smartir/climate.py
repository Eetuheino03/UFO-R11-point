"""Climate platform for UFO-R11 SmartIR integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_FAN_MODE,
    ATTR_SWING_MODE,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    SWING_OFF,
    SWING_VERTICAL,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from . import UFODataUpdateCoordinator
from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_MQTT_TOPIC,
    CONF_DEVICE_TYPE,
    CONF_CODE_SOURCE,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_TARGET_TEMP,
    DEFAULT_TEMP_STEP,
    POINTCODES_MIN_TEMP,
    POINTCODES_MAX_TEMP,
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    HVAC_MODE_SLEEP,
    SUPPORTED_HVAC_MODES,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    SUPPORTED_FAN_MODES,
    SWING_OFF,
    SWING_VERTICAL,
    SUPPORTED_SWING_MODES,
    MQTT_TOPIC_PREFIX,
    MQTT_COMMAND_SET,
    MQTT_IR_CODE_FIELD,
    CODE_SOURCE_POINTCODES,
    ATTR_LAST_COMMAND,
    ATTR_COMMAND_TIME,
    ATTR_AVAILABLE_CODES,
    ATTR_DEVICE_TEMPLATE,
)

_LOGGER = logging.getLogger(__name__)

# Map HA HVAC modes to our internal modes
HVAC_MODE_MAP = {
    HVACMode.OFF: HVAC_MODE_OFF,
    HVACMode.COOL: HVAC_MODE_COOL,
    HVACMode.HEAT: HVAC_MODE_HEAT,
    HVACMode.DRY: HVAC_MODE_DRY,
    HVACMode.FAN_ONLY: HVAC_MODE_FAN_ONLY,
    HVACMode.AUTO: HVAC_MODE_AUTO,
}

# Reverse mapping for internal to HA modes
INTERNAL_TO_HVAC_MODE = {v: k for k, v in HVAC_MODE_MAP.items()}

# Map HA fan modes to our internal modes
FAN_MODE_MAP = {
    FAN_LOW: FAN_LOW,
    FAN_MEDIUM: FAN_MEDIUM,
    FAN_HIGH: FAN_HIGH,
    FAN_AUTO: FAN_AUTO,
}

# Map HA swing modes to our internal modes
SWING_MODE_MAP = {
    SWING_OFF: SWING_OFF,
    SWING_VERTICAL: SWING_VERTICAL,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    async_add_entities([
        UFORClimateEntity(coordinator, config_entry)
    ])


class UFORClimateEntity(CoordinatorEntity, ClimateEntity):
    """Representation of a UFO-R11 climate entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = DEFAULT_TEMP_STEP
    _attr_target_temperature_step = DEFAULT_TEMP_STEP

    def __init__(
        self,
        coordinator: UFODataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        
        self._config_entry = config_entry
        self._device_id = config_entry.data[CONF_DEVICE_ID]
        self._device_name = config_entry.data[CONF_DEVICE_NAME]
        self._mqtt_topic = config_entry.data[CONF_MQTT_TOPIC]
        self._device_type = config_entry.data[CONF_DEVICE_TYPE]
        self._code_source = config_entry.data[CONF_CODE_SOURCE]
        
        # Set temperature limits based on code source
        if self._code_source == CODE_SOURCE_POINTCODES:
            self._attr_min_temp = POINTCODES_MIN_TEMP
            self._attr_max_temp = POINTCODES_MAX_TEMP
        else:
            self._attr_min_temp = DEFAULT_MIN_TEMP
            self._attr_max_temp = DEFAULT_MAX_TEMP
        
        # Initialize state
        self._attr_target_temperature = DEFAULT_TARGET_TEMP
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_fan_mode = FAN_AUTO
        self._attr_swing_mode = SWING_OFF
        
        # Custom attributes
        self._last_command = None
        self._command_time = None
        self._available_codes = []
        
        # Generate unique ID
        self._attr_unique_id = f"{self._device_id}_climate"
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._device_id)},
            "name": self._device_name,
            "manufacturer": "MOES",
            "model": "UFO-R11",
            "via_device": (DOMAIN, self._device_id),
        }

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
        )
        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return the list of available HVAC operation modes."""
        return [INTERNAL_TO_HVAC_MODE.get(mode, HVACMode.OFF) for mode in SUPPORTED_HVAC_MODES if mode != HVAC_MODE_SLEEP]

    @property
    def fan_modes(self) -> list[str]:
        """Return the list of available fan modes."""
        return SUPPORTED_FAN_MODES

    @property
    def swing_modes(self) -> list[str]:
        """Return the list of available swing modes."""
        return SUPPORTED_SWING_MODES

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the optional state attributes."""
        attributes = {
            "ir_device": self._device_id,
            ATTR_DEVICE_TEMPLATE: f"{self._device_type}_{self._code_source}",
        }
        
        if self._last_command:
            attributes[ATTR_LAST_COMMAND] = self._last_command
            
        if self._command_time:
            attributes[ATTR_COMMAND_TIME] = self._command_time.isoformat()
        
        # Get available codes from device manager
        device_manager = self.coordinator.device_manager
        if device_manager:
            try:
                # Get code count from device manager
                code_set = device_manager.ir_code_manager.get_device_codes(self._device_id)
                if code_set:
                    self._available_codes = list(code_set.commands.keys())
                    attributes[ATTR_AVAILABLE_CODES] = len(self._available_codes)
                    # Optionally add the actual command names for debugging
                    attributes["available_commands"] = self._available_codes
            except Exception as err:
                _LOGGER.debug("Could not get available codes: %s", err)
                
        return attributes

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target HVAC mode."""
        if hvac_mode not in self.hvac_modes:
            raise ServiceValidationError(f"Invalid HVAC mode: {hvac_mode}")
        
        internal_mode = HVAC_MODE_MAP.get(hvac_mode, HVAC_MODE_OFF)
        
        # Get IR code for the mode
        ir_code = await self._get_ir_code("hvac_mode", internal_mode)
        if ir_code:
            await self._send_ir_command(ir_code, f"hvac_mode_{internal_mode}")
            self._attr_hvac_mode = hvac_mode
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return
        
        if target_temp < self.min_temp or target_temp > self.max_temp:
            raise ServiceValidationError(
                f"Temperature {target_temp} is out of range ({self.min_temp}-{self.max_temp})"
            )
        
        # Get IR code for the temperature
        ir_code = await self._get_ir_code("temperature", int(target_temp))
        if ir_code:
            await self._send_ir_command(ir_code, f"temperature_{int(target_temp)}")
            self._attr_target_temperature = target_temp
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        if fan_mode not in self.fan_modes:
            raise ServiceValidationError(f"Invalid fan mode: {fan_mode}")
        
        # Get IR code for fan mode
        ir_code = await self._get_ir_code("fan_mode", fan_mode)
        if ir_code:
            await self._send_ir_command(ir_code, f"fan_{fan_mode}")
            self._attr_fan_mode = fan_mode
            self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        if swing_mode not in self.swing_modes:
            raise ServiceValidationError(f"Invalid swing mode: {swing_mode}")
        
        # Get IR code for swing mode
        ir_code = await self._get_ir_code("swing_mode", swing_mode)
        if ir_code:
            await self._send_ir_command(ir_code, f"swing_{swing_mode}")
            self._attr_swing_mode = swing_mode
            self.async_write_ha_state()

    async def _get_ir_code(self, command_type: str, value: Any) -> str | None:
        """Get IR code for the specified command."""
        device_manager = self.coordinator.device_manager
        if not device_manager:
            _LOGGER.error("Device manager not available for device %s", self._device_id)
            return None
        
        try:
            # Map command types to IR code categories
            command_mapping = {
                "hvac_mode": {
                    HVAC_MODE_OFF: "OFF",
                    HVAC_MODE_COOL: "cool",
                    HVAC_MODE_HEAT: "heat",
                    HVAC_MODE_DRY: "dry",
                    HVAC_MODE_FAN_ONLY: "fan",
                    HVAC_MODE_AUTO: "auto",
                    HVAC_MODE_SLEEP: "sleep",
                },
                "fan_mode": {
                    FAN_LOW: "low",
                    FAN_MEDIUM: "medium",
                    FAN_HIGH: "high",
                    FAN_AUTO: "auto",
                },
                "swing_mode": {
                    SWING_OFF: "swing_off",
                    SWING_VERTICAL: "swing_on",
                },
                "temperature": lambda temp: f"{temp}c",  # Temperature uses direct mapping
            }
            
            # Get the command name for lookup
            if command_type == "temperature":
                command_name = f"{value}c"
            else:
                mapping = command_mapping.get(command_type, {})
                command_name = mapping.get(value)
            
            if not command_name:
                _LOGGER.warning(
                    "No command mapping found for %s: %s",
                    command_type,
                    value
                )
                return None
            
            # Get IR code from device manager
            ir_code = await device_manager.get_ir_code(self._device_id, command_name)
            
            _LOGGER.debug(
                "Retrieved IR code for %s: %s on device %s -> %s",
                command_type,
                value,
                self._device_id,
                "Found" if ir_code else "Not found",
            )
            
            return ir_code
            
        except Exception as err:
            _LOGGER.error(
                "Failed to get IR code for %s: %s on device %s: %s",
                command_type,
                value,
                self._device_id,
                err,
            )
            return None

    async def _send_ir_command(self, ir_code: str, command_name: str) -> None:
        """Send IR command to UFO-R11 device via MQTT."""
        device_manager = self.coordinator.device_manager
        if not device_manager:
            _LOGGER.error("Device manager not available for device %s", self._device_id)
            raise ServiceValidationError("Device manager not available")
        
        try:
            # Use device manager to send IR command
            success = await device_manager.send_ir_command(self._device_id, ir_code)
            
            if success:
                # Update tracking attributes
                self._last_command = command_name
                self._command_time = dt_util.utcnow()
                
                _LOGGER.debug(
                    "Sent IR command %s to device %s",
                    command_name,
                    self._device_id,
                )
            else:
                raise ServiceValidationError("Failed to send IR command via device manager")
            
        except Exception as err:
            _LOGGER.error(
                "Failed to send IR command %s to device %s: %s",
                command_name,
                self._device_id,
                err,
            )
            raise ServiceValidationError(f"Failed to send IR command: {err}") from err

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self.coordinator.data:
            return
        
        # Update availability based on coordinator data
        self._attr_available = self.coordinator.data.get("available", False)
        
        # Update any other state from coordinator if needed
        super()._handle_coordinator_update()