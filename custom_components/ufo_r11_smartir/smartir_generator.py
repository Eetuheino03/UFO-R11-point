"""SmartIR JSON configuration generator for UFO-R11 SmartIR integration."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from .ha_helpers import HomeAssistant
# Removed unused imports from homeassistant.components.climate.const
# The non-existent enums were causing import errors and were not used

from .ir_codes import IRCodeSet, IRCodeManager
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    POINTCODES_MIN_TEMP,
    POINTCODES_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_TARGET_TEMP,
    DEFAULT_TEMP_STEP,
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    SWING_OFF,
    SWING_VERTICAL,
)

_LOGGER = logging.getLogger(__name__)


class SmartIRGenerator:
    """Generate SmartIR-compatible JSON configurations from UFO-R11 IR codes."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the SmartIR generator."""
        self.hass = hass
        self._ir_manager = IRCodeManager(hass)
    
    def _get_hvac_mode_mapping(self) -> Dict[str, str]:
        """Get mapping from internal HVAC modes to SmartIR format."""
        return {
            "cool": "cool",
            "heat": "heat", 
            "dry": "dry",
            "fan_only": "fan_only",
            "auto": "auto",
            "sleep": "auto",  # Map sleep to auto for SmartIR compatibility
        }
    
    def _get_fan_mode_mapping(self) -> Dict[str, str]:
        """Get mapping from internal fan modes to SmartIR format."""
        return {
            "low": "low",
            "medium": "medium", 
            "high": "high",
            "auto": "auto",
        }
    
    def _get_swing_mode_mapping(self) -> Dict[str, str]:
        """Get mapping from internal swing modes to SmartIR format."""
        return {
            "off": "off",
            "on": "vertical",  # Map "on" to "vertical" for SmartIR
        }
    
    def _build_temperature_commands(self, code_set: IRCodeSet) -> Dict[str, Any]:
        """Build temperature command structure for SmartIR."""
        temp_commands = {}
        
        # Get all available temperatures
        available_temps = sorted([int(temp) for temp in code_set.temperature.keys() if temp.isdigit()])
        
        if not available_temps:
            _LOGGER.warning("No temperature commands found in code set")
            return temp_commands
        
        min_temp = min(available_temps)
        max_temp = max(available_temps)
        
        _LOGGER.info("Temperature range: %d°C - %d°C", min_temp, max_temp)
        
        # Build temperature commands for each mode
        hvac_mapping = self._get_hvac_mode_mapping()
        
        for internal_mode, smartir_mode in hvac_mapping.items():
            mode_command = code_set.get_command("mode", internal_mode)
            if not mode_command or not mode_command.validated:
                continue
                
            temp_commands[smartir_mode] = {}
            
            # For each temperature, use the mode command
            # In SmartIR, each temperature/mode combination needs a specific command
            for temp in available_temps:
                temp_command = code_set.get_command("temperature", str(temp))
                if temp_command and temp_command.validated:
                    # Use temperature-specific command
                    temp_commands[smartir_mode][str(temp)] = temp_command.code
                else:
                    # Fallback to mode command (less ideal but functional)
                    temp_commands[smartir_mode][str(temp)] = mode_command.code
        
        return temp_commands
    
    def _build_fan_commands(self, code_set: IRCodeSet) -> Dict[str, str]:
        """Build fan speed command structure for SmartIR."""
        fan_commands = {}
        fan_mapping = self._get_fan_mode_mapping()
        
        for internal_fan, smartir_fan in fan_mapping.items():
            fan_command = code_set.get_command("fan_speed", internal_fan)
            if fan_command and fan_command.validated:
                fan_commands[smartir_fan] = fan_command.code
        
        return fan_commands
    
    def _build_swing_commands(self, code_set: IRCodeSet) -> Dict[str, str]:
        """Build swing command structure for SmartIR."""
        swing_commands = {}
        swing_mapping = self._get_swing_mode_mapping()
        
        for internal_swing, smartir_swing in swing_mapping.items():
            swing_command = code_set.get_command("swing", internal_swing)
            if swing_command and swing_command.validated:
                swing_commands[smartir_swing] = swing_command.code
        
        return swing_commands
    
    def _get_supported_modes(self, code_set: IRCodeSet) -> List[str]:
        """Get list of supported HVAC modes."""
        supported_modes = ["off"]  # Always include off
        hvac_mapping = self._get_hvac_mode_mapping()
        
        for internal_mode, smartir_mode in hvac_mapping.items():
            mode_command = code_set.get_command("mode", internal_mode)
            if mode_command and mode_command.validated:
                if smartir_mode not in supported_modes:
                    supported_modes.append(smartir_mode)
        
        return supported_modes
    
    def _get_supported_fan_modes(self, code_set: IRCodeSet) -> List[str]:
        """Get list of supported fan modes."""
        supported_modes = []
        fan_mapping = self._get_fan_mode_mapping()
        
        for internal_fan, smartir_fan in fan_mapping.items():
            fan_command = code_set.get_command("fan_speed", internal_fan)
            if fan_command and fan_command.validated:
                supported_modes.append(smartir_fan)
        
        return supported_modes
    
    def _get_supported_swing_modes(self, code_set: IRCodeSet) -> List[str]:
        """Get list of supported swing modes."""
        supported_modes = []
        swing_mapping = self._get_swing_mode_mapping()
        
        for internal_swing, smartir_swing in swing_mapping.items():
            swing_command = code_set.get_command("swing", internal_swing)
            if swing_command and swing_command.validated:
                supported_modes.append(smartir_swing)
        
        return supported_modes
    
    def _get_temperature_range(self, code_set: IRCodeSet) -> tuple[int, int]:
        """Get temperature range from code set."""
        available_temps = [int(temp) for temp in code_set.temperature.keys() if temp.isdigit()]
        
        if available_temps:
            return min(available_temps), max(available_temps)
        else:
            return POINTCODES_MIN_TEMP, POINTCODES_MAX_TEMP
    
    async def async_generate_smartir_config(
        self,
        device_id: str,
        output_path: Optional[str] = None,
        device_code: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate SmartIR configuration for a device."""
        try:
            _LOGGER.info("Generating SmartIR configuration for device %s", device_id)
            
            # Load device code set
            code_set = await self._ir_manager.async_load_device(device_id)
            if not code_set:
                _LOGGER.error("No code set found for device %s", device_id)
                return None
            
            # Validate essential commands
            validation = code_set.validate_commands()
            if validation["missing"]:
                _LOGGER.warning("Missing essential commands for SmartIR: %s", validation["missing"])
            
            # Get power commands
            power_on = code_set.get_command("power", "on")
            power_off = code_set.get_command("power", "off")
            
            if not power_on or not power_on.validated:
                _LOGGER.error("Missing or invalid power on command")
                return None
            
            if not power_off or not power_off.validated:
                _LOGGER.error("Missing or invalid power off command")
                return None
            
            # Get temperature range
            min_temp, max_temp = self._get_temperature_range(code_set)
            
            # Build SmartIR configuration
            config = {
                "manufacturer": code_set.manufacturer,
                "supportedModels": [code_set.model],
                "supportedController": "UFO-R11",
                "commandsEncoding": "Base64",
                "minTemperature": min_temp,
                "maxTemperature": max_temp,
                "precision": 1.0,
                "operationModes": self._get_supported_modes(code_set),
                "fanModes": self._get_supported_fan_modes(code_set),
                "swingModes": self._get_supported_swing_modes(code_set),
                "commands": {
                    "off": power_off.code,
                    "on": power_on.code,
                    "temperature": self._build_temperature_commands(code_set),
                    "fanSpeed": self._build_fan_commands(code_set),
                    "swing": self._build_swing_commands(code_set),
                }
            }
            
            # Add device code if provided
            if device_code:
                config["deviceCode"] = device_code
            
            # Add metadata
            config["_metadata"] = {
                "generated_by": f"{DOMAIN}",
                "generated_at": datetime.now().isoformat(),
                "device_id": device_id,
                "device_name": code_set.device_name,
                "total_commands": code_set.get_command_count(),
                "valid_commands": len(validation["valid"]),
                "invalid_commands": len(validation["invalid"]),
                "source_created_at": code_set.created_at,
                "source_updated_at": code_set.updated_at,
            }
            
            # Save to file if path provided
            if output_path:
                await self._save_config_file(config, output_path, device_id)
            
            _LOGGER.info("SmartIR configuration generated successfully for device %s", device_id)
            return config
            
        except Exception as e:
            _LOGGER.error("Failed to generate SmartIR config for device %s: %s", device_id, str(e))
            return None
    
    async def _save_config_file(
        self,
        config: Dict[str, Any],
        output_path: str,
        device_id: str
    ) -> bool:
        """Save SmartIR configuration to file."""
        try:
            output_file = Path(output_path)
            
            # Ensure directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate filename if directory provided
            if output_file.is_dir():
                filename = f"smartir_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                output_file = output_file / filename
            
            # Write configuration
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            _LOGGER.info("SmartIR configuration saved to %s", output_file)
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to save SmartIR config to %s: %s", output_path, str(e))
            return False
    
    async def async_generate_bulk_configs(
        self,
        output_dir: str,
        device_filter: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Generate SmartIR configurations for all devices."""
        results = {}
        
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            devices = self._ir_manager.get_all_devices()
            if device_filter:
                devices = [d for d in devices if d in device_filter]
            
            _LOGGER.info("Generating SmartIR configs for %d devices", len(devices))
            
            for device_id in devices:
                try:
                    config = await self.async_generate_smartir_config(
                        device_id=device_id,
                        output_path=str(output_path)
                    )
                    results[device_id] = config is not None
                    
                except Exception as e:
                    _LOGGER.error("Failed to generate config for device %s: %s", device_id, str(e))
                    results[device_id] = False
            
            successful = sum(1 for success in results.values() if success)
            _LOGGER.info("Generated %d/%d SmartIR configurations successfully", 
                       successful, len(devices))
            
            return results
            
        except Exception as e:
            _LOGGER.error("Failed to generate bulk SmartIR configs: %s", str(e))
            return {}
    
    def validate_smartir_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate SmartIR configuration structure."""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        
        # Required fields
        required_fields = [
            "manufacturer", "supportedModels", "commandsEncoding",
            "minTemperature", "maxTemperature", "precision",
            "operationModes", "commands"
        ]
        
        for field in required_fields:
            if field not in config:
                validation["errors"].append(f"Missing required field: {field}")
                validation["valid"] = False
        
        # Validate commands structure
        if "commands" in config:
            commands = config["commands"]
            
            # Check for required command categories
            if "off" not in commands:
                validation["errors"].append("Missing power off command")
                validation["valid"] = False
            
            if "temperature" not in commands or not commands["temperature"]:
                validation["errors"].append("Missing temperature commands")
                validation["valid"] = False
            
            # Validate temperature commands structure
            if "temperature" in commands:
                temp_commands = commands["temperature"]
                if not isinstance(temp_commands, dict):
                    validation["errors"].append("Temperature commands must be a dictionary")
                    validation["valid"] = False
                else:
                    for mode, temps in temp_commands.items():
                        if not isinstance(temps, dict):
                            validation["warnings"].append(f"Temperature commands for mode {mode} should be a dictionary")
        
        # Validate temperature range
        if "minTemperature" in config and "maxTemperature" in config:
            min_temp = config["minTemperature"]
            max_temp = config["maxTemperature"]
            
            if min_temp >= max_temp:
                validation["errors"].append("minTemperature must be less than maxTemperature")
                validation["valid"] = False
            
            if min_temp < 0 or max_temp > 50:
                validation["warnings"].append("Temperature range seems unusual (0-50°C expected)")
        
        return validation
    
    async def async_export_device_smartir(
        self,
        device_id: str,
        output_path: Optional[str] = None,
        device_code: Optional[int] = None
    ) -> bool:
        """Export device IR codes as SmartIR configuration."""
        try:
            config = await self.async_generate_smartir_config(
                device_id=device_id,
                output_path=output_path,
                device_code=device_code
            )
            
            if config:
                # Validate generated config
                validation = self.validate_smartir_config(config)
                if not validation["valid"]:
                    _LOGGER.error("Generated SmartIR config is invalid: %s", validation["errors"])
                    return False
                
                if validation["warnings"]:
                    _LOGGER.warning("SmartIR config warnings: %s", validation["warnings"])
                
                return True
            
            return False
            
        except Exception as e:
            _LOGGER.error("Failed to export SmartIR config for device %s: %s", device_id, str(e))
            return False


def create_smartir_generator(hass: HomeAssistant) -> SmartIRGenerator:
    """Create and return a SmartIR generator instance."""
    return SmartIRGenerator(hass)