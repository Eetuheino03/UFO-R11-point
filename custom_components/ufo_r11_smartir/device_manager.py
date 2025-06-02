"""Device and IR code management utilities for UFO-R11 SmartIR integration."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .ir_codes import IRCommand, IRCodeSet, IRCodeManager
from .parser import PointCodesParser, create_pointcodes_parser
from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_CODE_SOURCE,
    CODE_SOURCE_POINTCODES,
    CODE_SOURCE_LEARN,
    CODE_SOURCE_IMPORT,
    MQTT_IR_CODE_FIELD,
    MQTT_LEARNED_CODE_FIELD,
    MQTT_TOPIC_PREFIX,
    MQTT_COMMAND_SET,
    DEVICE_TYPE_AC,
    DEVICE_TYPE_TV,
    DEVICE_TYPE_CUSTOM,
    LEARN_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class DeviceManager:
    """Manages UFO-R11 devices and their IR code sets."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the device manager."""
        self.hass = hass
        self._ir_manager = IRCodeManager(hass)
        self._parser = create_pointcodes_parser()
        self._learning_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def async_setup_device(
        self,
        device_id: str,
        device_name: str,
        device_type: str = DEVICE_TYPE_AC,
        code_source: str = CODE_SOURCE_POINTCODES,
        **kwargs
    ) -> bool:
        """Set up a new device with IR codes."""
        try:
            _LOGGER.info("Setting up device %s (%s) with source %s", device_id, device_name, code_source)
            
            # Check if device already exists
            existing_codes = await self._ir_manager.async_load_device(device_id)
            if existing_codes:
                _LOGGER.info("Device %s already has IR codes loaded", device_id)
                return True
            
            # Create code set based on source
            code_set = None
            
            if code_source == CODE_SOURCE_POINTCODES:
                code_set = await self._setup_pointcodes_device(device_id, device_name, device_type)
            elif code_source == CODE_SOURCE_LEARN:
                code_set = await self._setup_learning_device(device_id, device_name, device_type)
            elif code_source == CODE_SOURCE_IMPORT:
                # Will be handled separately via import_codes method
                code_set = IRCodeSet(
                    device_id=device_id,
                    device_name=device_name,
                    device_type=device_type,
                )
            
            if code_set:
                self._ir_manager.add_device_codes(code_set)
                await self._ir_manager.async_save_device(device_id)
                _LOGGER.info("Successfully set up device %s with %d commands", 
                           device_id, code_set.get_command_count())
                return True
            
            _LOGGER.error("Failed to set up device %s", device_id)
            return False
            
        except Exception as e:
            _LOGGER.error("Error setting up device %s: %s", device_id, str(e))
            return False
    
    async def _setup_pointcodes_device(
        self, 
        device_id: str, 
        device_name: str, 
        device_type: str
    ) -> Optional[IRCodeSet]:
        """Set up device using Point-codes dataset."""
        try:
            # Look for Point-codes file in the integration's data directory
            data_dir = Path(self.hass.config.config_dir) / "custom_components" / DOMAIN / "data"
            pointcodes_file = data_dir / "Point-codes"
            
            if not pointcodes_file.exists():
                _LOGGER.error("Point-codes file not found at %s", pointcodes_file)
                return None
            
            # Parse Point-codes file
            code_set = self._parser.parse_file(pointcodes_file, device_id, device_name)
            if code_set:
                code_set.device_type = device_type
                _LOGGER.info("Loaded %d commands from Point-codes for device %s", 
                           code_set.get_command_count(), device_id)
            
            return code_set
            
        except Exception as e:
            _LOGGER.error("Failed to setup Point-codes device %s: %s", device_id, str(e))
            return None
    
    async def _setup_learning_device(
        self, 
        device_id: str, 
        device_name: str, 
        device_type: str
    ) -> IRCodeSet:
        """Set up device for IR code learning."""
        return IRCodeSet(
            device_id=device_id,
            device_name=device_name,
            device_type=device_type,
        )
    
    async def async_get_device_info(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device information and code summary."""
        code_set = await self._ir_manager.async_load_device(device_id)
        if not code_set:
            return None
        
        return self._ir_manager.get_device_summary(device_id)
    
    async def async_get_device_codes(self, device_id: str) -> Optional[IRCodeSet]:
        """Get IR code set for a device."""
        return await self._ir_manager.async_load_device(device_id)
    
    async def async_send_ir_command(
        self,
        device_id: str,
        category: str,
        key: str,
        mqtt_topic: str
    ) -> bool:
        """Send IR command to UFO-R11 device via MQTT."""
        try:
            code_set = await self._ir_manager.async_load_device(device_id)
            if not code_set:
                _LOGGER.error("No code set found for device %s", device_id)
                return False
            
            command = code_set.get_command(category, key)
            if not command:
                _LOGGER.error("Command %s.%s not found for device %s", category, key, device_id)
                return False
            
            if not command.validated:
                _LOGGER.error("Command %s.%s has invalid IR code", category, key)
                return False
            
            # Prepare MQTT message
            mqtt_payload = {
                MQTT_IR_CODE_FIELD: command.code
            }
            
            # Send via MQTT
            mqtt_topic_full = f"{mqtt_topic}/{MQTT_COMMAND_SET}"
            
            _LOGGER.info("Sending IR command %s.%s to device %s via %s", 
                        category, key, device_id, mqtt_topic_full)
            
            await self.hass.services.async_call(
                "mqtt",
                "publish",
                {
                    "topic": mqtt_topic_full,
                    "payload": json.dumps(mqtt_payload),
                },
                blocking=True,
            )
            
            _LOGGER.debug("IR command sent successfully")
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to send IR command %s.%s for device %s: %s", 
                         category, key, device_id, str(e))
            return False
    
    async def async_learn_ir_command(
        self,
        device_id: str,
        command_name: str,
        category: str,
        key: str,
        mqtt_topic: str,
        timeout: int = LEARN_TIMEOUT
    ) -> bool:
        """Learn new IR command from remote control."""
        try:
            _LOGGER.info("Starting IR learning for device %s, command %s", device_id, command_name)
            
            # Check if learning session already exists
            if device_id in self._learning_sessions:
                _LOGGER.warning("Learning session already active for device %s", device_id)
                return False
            
            # Initialize learning session
            session = {
                "device_id": device_id,
                "command_name": command_name,
                "category": category,
                "key": key,
                "mqtt_topic": mqtt_topic,
                "start_time": dt_util.utcnow(),
                "timeout": timeout,
                "status": "learning",
            }
            
            self._learning_sessions[device_id] = session
            
            # Send learning command to UFO-R11 device
            mqtt_payload = {
                "action": "learn_ir",
                "timeout": timeout,
            }
            
            mqtt_topic_full = f"{mqtt_topic}/{MQTT_COMMAND_SET}"
            
            await self.hass.services.async_call(
                "mqtt",
                "publish",
                {
                    "topic": mqtt_topic_full,
                    "payload": json.dumps(mqtt_payload),
                },
                blocking=True,
            )
            
            _LOGGER.info("Learning command sent to device %s, waiting for IR signal...", device_id)
            
            # Set up timeout
            async def learning_timeout():
                await asyncio.sleep(timeout)
                if device_id in self._learning_sessions:
                    session = self._learning_sessions.pop(device_id)
                    _LOGGER.warning("Learning timeout for device %s, command %s", device_id, command_name)
                    
                    # Send notification
                    self.hass.components.persistent_notification.async_create(
                        f"IR code learning timeout for {command_name}. Please try again.",
                        title="UFO-R11 SmartIR",
                        notification_id=f"ufo_r11_timeout_{device_id}",
                    )
            
            # Start timeout task
            asyncio.create_task(learning_timeout())
            
            return True
            
        except Exception as e:
            # Clean up session on error
            if device_id in self._learning_sessions:
                del self._learning_sessions[device_id]
            
            _LOGGER.error("Failed to start IR learning for device %s: %s", device_id, str(e))
            return False
    
    async def async_handle_learned_code(
        self,
        device_id: str,
        learned_code: str,
        mqtt_topic: str
    ) -> bool:
        """Handle learned IR code from UFO-R11 device."""
        try:
            if device_id not in self._learning_sessions:
                _LOGGER.warning("No active learning session for device %s", device_id)
                return False
            
            session = self._learning_sessions.pop(device_id)
            
            _LOGGER.info("Received learned IR code for device %s, command %s", 
                        device_id, session["command_name"])
            
            # Load device code set
            code_set = await self._ir_manager.async_load_device(device_id)
            if not code_set:
                _LOGGER.error("No code set found for device %s", device_id)
                return False
            
            # Create new IR command
            ir_command = IRCommand(
                name=session["command_name"],
                code=learned_code,
                raw_data=f"Learned via UFO-R11 on {dt_util.utcnow().isoformat()}",
            )
            
            # Add to code set
            if code_set.add_command(session["category"], session["key"], ir_command):
                await self._ir_manager.async_save_device(device_id)
                
                _LOGGER.info("Successfully learned IR command %s for device %s", 
                           session["command_name"], device_id)
                
                # Send success notification
                self.hass.components.persistent_notification.async_create(
                    f"Successfully learned IR code for {session['command_name']}",
                    title="UFO-R11 SmartIR",
                    notification_id=f"ufo_r11_success_{device_id}",
                )
                
                return True
            else:
                _LOGGER.error("Failed to add learned command %s to device %s", 
                            session["command_name"], device_id)
                return False
            
        except Exception as e:
            _LOGGER.error("Failed to handle learned code for device %s: %s", device_id, str(e))
            return False
    
    async def async_import_codes(
        self,
        device_id: str,
        file_path: str,
        file_format: str = "pointcodes"
    ) -> bool:
        """Import IR codes from file."""
        try:
            _LOGGER.info("Importing IR codes for device %s from %s", device_id, file_path)
            
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                _LOGGER.error("Import file not found: %s", file_path)
                return False
            
            # Load existing device or create new one
            code_set = await self._ir_manager.async_load_device(device_id)
            if not code_set:
                _LOGGER.warning("No existing code set for device %s, creating new one", device_id)
                code_set = IRCodeSet(
                    device_id=device_id,
                    device_name=f"Imported_{device_id}",
                    device_type=DEVICE_TYPE_AC,
                )
            
            imported_count = 0
            
            if file_format == "pointcodes":
                # Parse as Point-codes format
                imported_set = self._parser.parse_file(file_path_obj, device_id, code_set.device_name)
                if imported_set:
                    # Merge commands from imported set
                    for category, commands in imported_set.get_all_commands().items():
                        for key, command in commands.items():
                            if code_set.add_command(category, key, command):
                                imported_count += 1
            
            elif file_format == "json":
                # Parse as JSON format
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Import based on JSON structure
                for category, commands in data.get("commands", {}).items():
                    if isinstance(commands, dict):
                        for key, code_data in commands.items():
                            if isinstance(code_data, str):
                                # Simple format: key -> code
                                command = IRCommand(
                                    name=f"{category}_{key}",
                                    code=code_data,
                                    raw_data=f"Imported from {file_path}",
                                )
                            elif isinstance(code_data, dict):
                                # Complex format: key -> {name, code, ...}
                                command = IRCommand.from_dict(code_data)
                            else:
                                continue
                            
                            if code_set.add_command(category, key, command):
                                imported_count += 1
            
            if imported_count > 0:
                self._ir_manager.add_device_codes(code_set)
                await self._ir_manager.async_save_device(device_id)
                _LOGGER.info("Successfully imported %d commands for device %s", imported_count, device_id)
                return True
            else:
                _LOGGER.warning("No commands imported for device %s", device_id)
                return False
            
        except Exception as e:
            _LOGGER.error("Failed to import codes for device %s: %s", device_id, str(e))
            return False
    
    async def async_test_command(
        self,
        device_id: str,
        ir_code: str,
        mqtt_topic: str
    ) -> bool:
        """Test IR command by sending it directly."""
        try:
            _LOGGER.info("Testing IR command for device %s", device_id)
            
            # Validate IR code format
            test_command = IRCommand(name="test", code=ir_code)
            if not test_command.validated:
                _LOGGER.error("Invalid IR code format: %s", ir_code)
                return False
            
            # Send test command
            mqtt_payload = {
                MQTT_IR_CODE_FIELD: ir_code
            }
            
            mqtt_topic_full = f"{mqtt_topic}/{MQTT_COMMAND_SET}"
            
            await self.hass.services.async_call(
                "mqtt",
                "publish",
                {
                    "topic": mqtt_topic_full,
                    "payload": json.dumps(mqtt_payload),
                },
                blocking=True,
            )
            
            _LOGGER.info("Test command sent successfully for device %s", device_id)
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to test command for device %s: %s", device_id, str(e))
            return False
    
    async def async_remove_device(self, device_id: str) -> bool:
        """Remove device and all its IR codes."""
        try:
            result = self._ir_manager.remove_device_codes(device_id)
            if result:
                _LOGGER.info("Removed device %s and all its codes", device_id)
            return result
        except Exception as e:
            _LOGGER.error("Failed to remove device %s: %s", device_id, str(e))
            return False
    
    def get_learning_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current learning session status for device."""
        return self._learning_sessions.get(device_id)
    
    def get_all_devices(self) -> List[str]:
        """Get list of all managed devices."""
        return self._ir_manager.get_all_devices()
    
    async def async_get_devices_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all devices."""
        summaries = []
        for device_id in self.get_all_devices():
            summary = self._ir_manager.get_device_summary(device_id)
            if summary:
                summaries.append(summary)
        return summaries