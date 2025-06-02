"""MQTT-based device discovery for UFO-R11 SmartIR integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util
from homeassistant.components import mqtt

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_MQTT_TOPIC,
    CONF_DEVICE_TYPE,
    CONF_CODE_SOURCE,
    DEVICE_TYPE_AC,
    CODE_SOURCE_POINTCODES,
    MQTT_TOPIC_PREFIX,
    MANUFACTURER,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)

# Discovery constants
DISCOVERY_TOPIC = f"{MQTT_TOPIC_PREFIX}/bridge/devices"
DEVICE_AVAILABILITY_TOPIC = f"{MQTT_TOPIC_PREFIX}/+/availability"
DEVICE_STATUS_TOPIC = f"{MQTT_TOPIC_PREFIX}/+"

# UFO-R11 device identification patterns
UFO_R11_PATTERNS = [
    "UFO-R11",
    "MOES UFO-R11",
    "0x",  # Zigbee device IDs typically start with 0x
]

# Attributes that indicate IR capability
IR_CAPABILITY_ATTRIBUTES = [
    "ir_code_to_send",
    "learned_ir_code",
    "ir_learning_mode",
    "infrared",
]


class UFODeviceDiscovery:
    """Handles automatic discovery of UFO-R11 devices via MQTT."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the discovery service."""
        self.hass = hass
        self._discovered_devices: Dict[str, Dict[str, Any]] = {}
        self._discovery_enabled = True
        self._subscribers: List[Callable] = []
        self._discovery_lock = asyncio.Lock()
        
    async def async_start_discovery(self) -> bool:
        """Start MQTT-based device discovery."""
        try:
            if "mqtt" not in self.hass.config.components:
                _LOGGER.error("MQTT integration not available for device discovery")
                return False
            
            _LOGGER.info("Starting UFO-R11 device discovery")
            
            # Subscribe to Zigbee2MQTT bridge messages for device announcements
            await mqtt.async_subscribe(
                self.hass,
                DISCOVERY_TOPIC,
                self._handle_bridge_devices_message,
                0
            )
            
            # Subscribe to device availability messages
            await mqtt.async_subscribe(
                self.hass,
                DEVICE_AVAILABILITY_TOPIC,
                self._handle_device_availability,
                0
            )
            
            # Subscribe to general device status messages
            await mqtt.async_subscribe(
                self.hass,
                DEVICE_STATUS_TOPIC,
                self._handle_device_status,
                0
            )
            
            # Request current device list from Zigbee2MQTT
            await self._request_device_list()
            
            _LOGGER.info("UFO-R11 device discovery started successfully")
            return True
            
        except Exception as e:
            _LOGGER.error("Failed to start device discovery: %s", str(e))
            return False
    
    async def async_stop_discovery(self) -> None:
        """Stop device discovery."""
        self._discovery_enabled = False
        _LOGGER.info("UFO-R11 device discovery stopped")
    
    async def _request_device_list(self) -> None:
        """Request current device list from Zigbee2MQTT bridge."""
        try:
            bridge_request_topic = f"{MQTT_TOPIC_PREFIX}/bridge/request/devices"
            await mqtt.async_publish(
                self.hass,
                bridge_request_topic,
                "",
                0,
                False
            )
            _LOGGER.debug("Requested device list from Zigbee2MQTT bridge")
        except Exception as e:
            _LOGGER.warning("Failed to request device list: %s", str(e))
    
    @callback
    def _handle_bridge_devices_message(self, message) -> None:
        """Handle Zigbee2MQTT bridge devices message."""
        if not self._discovery_enabled:
            return
        
        try:
            payload = json.loads(message.payload)
            _LOGGER.debug("Received bridge devices message: %s", payload)
            
            if isinstance(payload, list):
                # This is a device list
                self.hass.async_create_task(self._process_device_list(payload))
            elif isinstance(payload, dict) and "type" in payload:
                # This might be a single device announcement
                if payload.get("type") == "device_announced":
                    device_info = payload.get("data", {})
                    self.hass.async_create_task(self._process_single_device(device_info))
                    
        except (json.JSONDecodeError, Exception) as e:
            _LOGGER.debug("Failed to parse bridge devices message: %s", str(e))
    
    @callback
    def _handle_device_availability(self, message) -> None:
        """Handle device availability messages."""
        if not self._discovery_enabled:
            return
        
        try:
            # Extract device topic from message topic
            topic_parts = message.topic.split("/")
            if len(topic_parts) >= 2:
                device_topic = topic_parts[1]
                availability = message.payload.decode('utf-8')
                
                _LOGGER.debug("Device %s availability: %s", device_topic, availability)
                
                if availability == "online":
                    # Device came online, check if it's a UFO-R11
                    self.hass.async_create_task(self._check_device_capabilities(device_topic))
                    
        except Exception as e:
            _LOGGER.debug("Failed to handle availability message: %s", str(e))
    
    @callback
    def _handle_device_status(self, message) -> None:
        """Handle general device status messages."""
        if not self._discovery_enabled:
            return
        
        try:
            # Extract device topic from message topic
            topic_parts = message.topic.split("/")
            if len(topic_parts) >= 2:
                device_topic = topic_parts[1]
                
                # Skip bridge and other system topics
                if device_topic in ["bridge", "config"]:
                    return
                
                payload = json.loads(message.payload)
                _LOGGER.debug("Device status update for %s: %s", device_topic, payload)
                
                # Check if this device has IR capabilities
                if self._has_ir_capabilities(payload):
                    device_info = {
                        "friendly_name": device_topic,
                        "ieee_address": device_topic,
                        "definition": {
                            "model": "UFO-R11",
                            "vendor": "MOES"
                        },
                        "status": payload
                    }
                    self.hass.async_create_task(self._process_single_device(device_info))
                    
        except (json.JSONDecodeError, Exception) as e:
            _LOGGER.debug("Failed to handle device status message: %s", str(e))
    
    def _has_ir_capabilities(self, payload: Dict[str, Any]) -> bool:
        """Check if device payload indicates IR capabilities."""
        if not isinstance(payload, dict):
            return False
        
        # Check for IR-related attributes
        for attr in IR_CAPABILITY_ATTRIBUTES:
            if attr in payload:
                return True
        
        # Check for device model in payload
        if "device" in payload:
            device_info = payload["device"]
            if isinstance(device_info, dict):
                model = device_info.get("model", "")
                if any(pattern in str(model).upper() for pattern in ["UFO-R11", "MOES"]):
                    return True
        
        return False
    
    async def _process_device_list(self, devices: List[Dict[str, Any]]) -> None:
        """Process a list of devices from Zigbee2MQTT."""
        async with self._discovery_lock:
            _LOGGER.debug("Processing device list with %d devices", len(devices))
            
            for device in devices:
                if self._is_ufo_r11_device(device):
                    await self._process_single_device(device)
    
    async def _process_single_device(self, device_info: Dict[str, Any]) -> None:
        """Process a single device for UFO-R11 discovery."""
        async with self._discovery_lock:
            if not self._is_ufo_r11_device(device_info):
                return
            
            device_id = self._extract_device_id(device_info)
            friendly_name = device_info.get("friendly_name", device_id)
            
            if not device_id:
                _LOGGER.debug("No valid device ID found in device info")
                return
            
            # Check if device is already discovered or configured
            if await self._is_device_already_configured(device_id):
                _LOGGER.debug("Device %s already configured, skipping", device_id)
                return
            
            if device_id in self._discovered_devices:
                _LOGGER.debug("Device %s already discovered, updating info", device_id)
                self._discovered_devices[device_id].update({
                    "last_seen": dt_util.utcnow(),
                    "device_info": device_info
                })
                return
            
            # New UFO-R11 device discovered
            discovery_data = {
                "device_id": device_id,
                "name": friendly_name,
                "topic": f"{MQTT_TOPIC_PREFIX}/{friendly_name}",
                "device_type": DEVICE_TYPE_AC,
                "code_source": CODE_SOURCE_POINTCODES,
                "discovered_at": dt_util.utcnow(),
                "last_seen": dt_util.utcnow(),
                "device_info": device_info,
                "manufacturer": MANUFACTURER,
                "model": MODEL,
            }
            
            self._discovered_devices[device_id] = discovery_data
            
            _LOGGER.info("Discovered new UFO-R11 device: %s (%s)", friendly_name, device_id)
            
            # Notify discovery
            await self._notify_device_discovered(discovery_data)
    
    def _is_ufo_r11_device(self, device_info: Dict[str, Any]) -> bool:
        """Check if device is a UFO-R11 based on available information."""
        if not isinstance(device_info, dict):
            return False
        
        # Check device definition
        definition = device_info.get("definition", {})
        if isinstance(definition, dict):
            model = definition.get("model", "")
            vendor = definition.get("vendor", "")
            
            if "UFO-R11" in str(model) or "MOES" in str(vendor):
                return True
        
        # Check friendly name patterns
        friendly_name = device_info.get("friendly_name", "")
        if any(pattern in str(friendly_name).upper() for pattern in UFO_R11_PATTERNS):
            return True
        
        # Check for IR capabilities in device status
        if "status" in device_info:
            return self._has_ir_capabilities(device_info["status"])
        
        # Check IEEE address pattern (Zigbee devices)
        ieee_address = device_info.get("ieee_address", "")
        if ieee_address and ieee_address.startswith("0x") and len(ieee_address) == 18:
            # Additional checks could be added here for known UFO-R11 OUI patterns
            return self._has_ir_capabilities(device_info)
        
        return False
    
    def _extract_device_id(self, device_info: Dict[str, Any]) -> Optional[str]:
        """Extract device ID from device info."""
        # Prefer IEEE address if available
        ieee_address = device_info.get("ieee_address")
        if ieee_address:
            return ieee_address
        
        # Fall back to friendly name
        friendly_name = device_info.get("friendly_name")
        if friendly_name:
            return friendly_name
        
        return None
    
    async def _is_device_already_configured(self, device_id: str) -> bool:
        """Check if device is already configured in Home Assistant."""
        # Check existing config entries
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get(CONF_DEVICE_ID) == device_id:
                return True
        
        return False
    
    async def _check_device_capabilities(self, device_topic: str) -> None:
        """Request device capabilities to verify it's a UFO-R11."""
        try:
            # Send a get command to retrieve device attributes
            get_topic = f"{MQTT_TOPIC_PREFIX}/{device_topic}/get"
            await mqtt.async_publish(
                self.hass,
                get_topic,
                json.dumps({"state": ""}),
                0,
                False
            )
            _LOGGER.debug("Requested capabilities for device %s", device_topic)
        except Exception as e:
            _LOGGER.debug("Failed to request capabilities for %s: %s", device_topic, str(e))
    
    async def _notify_device_discovered(self, discovery_data: Dict[str, Any]) -> None:
        """Notify about discovered device."""
        try:
            # Send discovery notification to config flow
            await discovery.async_load_platform(
                self.hass,
                "config_flow",
                DOMAIN,
                discovery_data,
                {}
            )
            
            # Create persistent notification for user
            self.hass.components.persistent_notification.async_create(
                f"New UFO-R11 device discovered: {discovery_data['name']}\n"
                f"Device ID: {discovery_data['device_id']}\n"
                f"Click to configure it automatically.",
                title="UFO-R11 Device Discovery",
                notification_id=f"ufo_r11_discovery_{discovery_data['device_id']}",
            )
            
            _LOGGER.info("Notified discovery of device %s", discovery_data['device_id'])
            
        except Exception as e:
            _LOGGER.error("Failed to notify device discovery: %s", str(e))
    
    def get_discovered_devices(self) -> Dict[str, Dict[str, Any]]:
        """Get all discovered devices."""
        return self._discovered_devices.copy()
    
    def clear_discovered_device(self, device_id: str) -> bool:
        """Clear a discovered device (after it's been configured)."""
        if device_id in self._discovered_devices:
            del self._discovered_devices[device_id]
            _LOGGER.debug("Cleared discovered device %s", device_id)
            return True
        return False
    
    async def async_get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a discovered device."""
        if device_id not in self._discovered_devices:
            return None
        
        device_data = self._discovered_devices[device_id]
        
        # Check if device is still available
        last_seen = device_data.get("last_seen")
        if last_seen:
            time_diff = dt_util.utcnow() - last_seen
            if time_diff > timedelta(minutes=10):
                device_data["status"] = "offline"
            else:
                device_data["status"] = "online"
        
        return device_data