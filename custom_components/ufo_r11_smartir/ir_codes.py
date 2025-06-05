"""IR code data models and management for UFO-R11 SmartIR integration."""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import aiofiles

from .ha_helpers import HomeAssistant, dt_util

from .const import (
    DOMAIN,
    HVAC_MODE_OFF,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO,
    HVAC_MODE_SLEEP,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_AUTO,
    SWING_OFF,
    SWING_VERTICAL,
    POINTCODES_MIN_TEMP,
    POINTCODES_MAX_TEMP,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class IRCommand:
    """Represents a single IR command with its encoded data."""
    
    name: str
    code: str
    raw_data: Optional[str] = None
    timestamp: Optional[str] = None
    validated: bool = False
    
    def __post_init__(self):
        """Post-initialization validation and processing."""
        if self.timestamp is None:
            self.timestamp = dt_util.utcnow().isoformat()
        
        # Validate Base64 encoding
        self.validated = self._validate_base64()
    
    def _validate_base64(self) -> bool:
        """Validate that the code is valid Base64 encoding."""
        try:
            # Attempt to decode the Base64 string
            decoded = base64.b64decode(self.code, validate=True)
            return len(decoded) > 0
        except Exception as e:
            _LOGGER.warning("Invalid Base64 IR code for %s: %s", self.name, str(e))
            return False
    
    def get_decoded_data(self) -> Optional[bytes]:
        """Get the decoded IR data as bytes."""
        if not self.validated:
            return None
        
        try:
            return base64.b64decode(self.code)
        except Exception as e:
            _LOGGER.error("Failed to decode IR data for %s: %s", self.name, str(e))
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary representation."""
        return {
            "name": self.name,
            "code": self.code,
            "raw_data": self.raw_data,
            "timestamp": self.timestamp,
            "validated": self.validated,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IRCommand:
        """Create IRCommand from dictionary."""
        return cls(
            name=data["name"],
            code=data["code"],
            raw_data=data.get("raw_data"),
            timestamp=data.get("timestamp"),
            validated=data.get("validated", False),
        )


@dataclass
class IRCodeSet:
    """Represents a complete set of IR codes for a device."""
    
    device_id: str
    device_name: str
    device_type: str = "air_conditioner"
    manufacturer: str = "MOES"
    model: str = "UFO-R11"
    
    # Power commands
    power: Dict[str, IRCommand] = field(default_factory=dict)
    
    # Temperature commands (17-30°C)
    temperature: Dict[str, IRCommand] = field(default_factory=dict)
    
    # Mode commands
    mode: Dict[str, IRCommand] = field(default_factory=dict)
    
    # Fan speed commands
    fan_speed: Dict[str, IRCommand] = field(default_factory=dict)
    
    # Swing commands
    swing: Dict[str, IRCommand] = field(default_factory=dict)
    
    # Custom/learned commands
    custom: Dict[str, IRCommand] = field(default_factory=dict)
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization setup."""
        if self.created_at is None:
            self.created_at = dt_util.utcnow().isoformat()
        self.updated_at = dt_util.utcnow().isoformat()
    
    def add_command(self, category: str, key: str, command: IRCommand) -> bool:
        """Add a command to the specified category."""
        try:
            category_dict = getattr(self, category, None)
            if category_dict is None:
                _LOGGER.error("Invalid category: %s", category)
                return False
            
            category_dict[key] = command
            self.updated_at = dt_util.utcnow().isoformat()
            _LOGGER.debug("Added command %s to category %s for device %s", 
                         command.name, category, self.device_id)
            return True
        except Exception as e:
            _LOGGER.error("Failed to add command %s: %s", command.name, str(e))
            return False
    
    def get_command(self, category: str, key: str) -> Optional[IRCommand]:
        """Get a command from the specified category."""
        try:
            category_dict = getattr(self, category, None)
            if category_dict is None:
                return None
            return category_dict.get(key)
        except Exception as e:
            _LOGGER.error("Failed to get command %s from %s: %s", key, category, str(e))
            return None
    
    def remove_command(self, category: str, key: str) -> bool:
        """Remove a command from the specified category."""
        try:
            category_dict = getattr(self, category, None)
            if category_dict is None or key not in category_dict:
                return False
            
            del category_dict[key]
            self.updated_at = dt_util.utcnow().isoformat()
            return True
        except Exception as e:
            _LOGGER.error("Failed to remove command %s from %s: %s", key, category, str(e))
            return False
    
    def get_all_commands(self) -> Dict[str, Dict[str, IRCommand]]:
        """Get all commands organized by category."""
        return {
            "power": self.power,
            "temperature": self.temperature,
            "mode": self.mode,
            "fan_speed": self.fan_speed,
            "swing": self.swing,
            "custom": self.custom,
        }
    
    def get_command_count(self) -> int:
        """Get total number of commands in this code set."""
        return sum(len(commands) for commands in self.get_all_commands().values())
    
    def validate_commands(self) -> Dict[str, List[str]]:
        """Validate all commands and return validation results."""
        results = {
            "valid": [],
            "invalid": [],
            "missing": [],
        }
        
        for category, commands in self.get_all_commands().items():
            for key, command in commands.items():
                command_id = f"{category}.{key}"
                if command.validated:
                    results["valid"].append(command_id)
                else:
                    results["invalid"].append(command_id)
        
        # Check for missing essential commands
        essential_commands = [
            ("power", "on"),
            ("power", "off"),
            ("mode", "cool"),
            ("fan_speed", "auto"),
        ]
        
        for category, key in essential_commands:
            if not self.get_command(category, key):
                results["missing"].append(f"{category}.{key}")
        
        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert code set to dictionary representation."""
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "power": {k: v.to_dict() for k, v in self.power.items()},
            "temperature": {k: v.to_dict() for k, v in self.temperature.items()},
            "mode": {k: v.to_dict() for k, v in self.mode.items()},
            "fan_speed": {k: v.to_dict() for k, v in self.fan_speed.items()},
            "swing": {k: v.to_dict() for k, v in self.swing.items()},
            "custom": {k: v.to_dict() for k, v in self.custom.items()},
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> IRCodeSet:
        """Create IRCodeSet from dictionary."""
        code_set = cls(
            device_id=data["device_id"],
            device_name=data["device_name"],
            device_type=data.get("device_type", "air_conditioner"),
            manufacturer=data.get("manufacturer", "MOES"),
            model=data.get("model", "UFO-R11"),
            created_at=data.get("created_at"),
        )
        
        # Load commands for each category
        for category in ["power", "temperature", "mode", "fan_speed", "swing", "custom"]:
            if category in data:
                category_dict = getattr(code_set, category)
                for key, command_data in data[category].items():
                    category_dict[key] = IRCommand.from_dict(command_data)
        
        code_set.updated_at = data.get("updated_at")
        return code_set


class IRCodeManager:
    """Manages IR code sets for multiple devices."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the IR code manager."""
        self.hass = hass
        self._code_sets: Dict[str, IRCodeSet] = {}
        self._storage_path = Path(hass.config.config_dir) / "custom_components" / DOMAIN / "data"
        self._storage_path.mkdir(parents=True, exist_ok=True)
    
    async def async_load_device(self, device_id: str) -> Optional[IRCodeSet]:
        """Load IR code set for a device."""
        if device_id in self._code_sets:
            return self._code_sets[device_id]
        
        # Try to load from storage
        storage_file = self._storage_path / f"{device_id}.json"
        if storage_file.exists():
            try:
                _LOGGER.debug("DEBUG: About to perform NON-BLOCKING async file read on: %s", storage_file)
                _LOGGER.info("DEBUG: Using aiofiles for non-blocking IR codes file read!")
                async with aiofiles.open(storage_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                _LOGGER.debug("DEBUG: File read completed successfully")
                code_set = IRCodeSet.from_dict(data)
                self._code_sets[device_id] = code_set
                _LOGGER.info("Loaded IR code set for device %s with %d commands", 
                           device_id, code_set.get_command_count())
                return code_set
            except Exception as e:
                _LOGGER.error("Failed to load IR codes for device %s: %s", device_id, str(e))
        
        return None
    
    async def async_save_device(self, device_id: str) -> bool:
        """Save IR code set for a device."""
        if device_id not in self._code_sets:
            _LOGGER.warning("No code set found for device %s", device_id)
            return False
        
        try:
            storage_file = self._storage_path / f"{device_id}.json"
            code_set = self._code_sets[device_id]
            
            _LOGGER.debug("DEBUG: About to perform NON-BLOCKING async file write to: %s", storage_file)
            _LOGGER.info("DEBUG: Using aiofiles for non-blocking IR codes file write!")
            async with aiofiles.open(storage_file, 'w', encoding='utf-8') as f:
                content = json.dumps(code_set.to_dict(), indent=2, ensure_ascii=False)
                await f.write(content)
            _LOGGER.debug("DEBUG: File write completed successfully")
            
            _LOGGER.info("Saved IR code set for device %s", device_id)
            return True
        except Exception as e:
            _LOGGER.error("Failed to save IR codes for device %s: %s", device_id, str(e))
            return False
    
    def get_device_codes(self, device_id: str) -> Optional[IRCodeSet]:
        """Get IR code set for a device."""
        return self._code_sets.get(device_id)
    
    def add_device_codes(self, code_set: IRCodeSet) -> bool:
        """Add or update IR code set for a device."""
        try:
            self._code_sets[code_set.device_id] = code_set
            _LOGGER.info("Added IR code set for device %s", code_set.device_id)
            return True
        except Exception as e:
            _LOGGER.error("Failed to add code set for device %s: %s", code_set.device_id, str(e))
            return False
    
    def remove_device_codes(self, device_id: str) -> bool:
        """Remove IR code set for a device."""
        if device_id in self._code_sets:
            del self._code_sets[device_id]
            
            # Also remove storage file
            storage_file = self._storage_path / f"{device_id}.json"
            if storage_file.exists():
                try:
                    storage_file.unlink()
                except Exception as e:
                    _LOGGER.warning("Failed to remove storage file for device %s: %s", device_id, str(e))
            
            _LOGGER.info("Removed IR code set for device %s", device_id)
            return True
        return False
    
    def get_all_devices(self) -> List[str]:
        """Get list of all device IDs with code sets."""
        return list(self._code_sets.keys())
    
    def get_device_summary(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get summary information for a device."""
        code_set = self._code_sets.get(device_id)
        if not code_set:
            return None
        
        validation = code_set.validate_commands()
        return {
            "device_id": device_id,
            "device_name": code_set.device_name,
            "device_type": code_set.device_type,
            "manufacturer": code_set.manufacturer,
            "model": code_set.model,
            "total_commands": code_set.get_command_count(),
            "valid_commands": len(validation["valid"]),
            "invalid_commands": len(validation["invalid"]),
            "missing_commands": len(validation["missing"]),
            "created_at": code_set.created_at,
            "updated_at": code_set.updated_at,
        }