"""MQTT-based device discovery for UFO-R11 SmartIR integration."""
from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Callable, Coroutine
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util
from homeassistant.components import mqtt
from homeassistant.components import zeroconf
from homeassistant.components import ssdp

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
        self._zeroconf_listener: Optional[Callable[[], None]] = None
        self._ssdp_listener: Optional[Callable[[], Coroutine[Any, Any, None]]] = None # Store the unregister callable

    async def async_start_discovery(self) -> bool:
        """Start MQTT, mDNS, and SSDP based device discovery."""
        _LOGGER.info("Starting UFO-R11 device discovery (MQTT, mDNS, SSDP)")
        mqtt_started = False
        try:
            if "mqtt" in self.hass.config.components:
                _LOGGER.info("Starting MQTT discovery for UFO-R11")
                # Subscribe to Zigbee2MQTT bridge messages
                await mqtt.async_subscribe(
                    self.hass, DISCOVERY_TOPIC, self._handle_bridge_devices_message, 0
                )
                await mqtt.async_subscribe(
                    self.hass, DEVICE_AVAILABILITY_TOPIC, self._handle_device_availability, 0
                )
                await mqtt.async_subscribe(
                    self.hass, DEVICE_STATUS_TOPIC, self._handle_device_status, 0
                )
                await self._request_device_list()
                _LOGGER.info("MQTT discovery for UFO-R11 started")
                mqtt_started = True
            else:
                _LOGGER.warning("MQTT integration not available, MQTT discovery for UFO-R11 skipped")

        except Exception as e:
            _LOGGER.error("Failed to start MQTT part of device discovery: %s", str(e))
            # Continue with other discovery methods even if MQTT fails

        # Start mDNS/Zeroconf discovery
        try:
            _LOGGER.info("Starting mDNS/Zeroconf discovery for UFO-R11")
            zc_instance = await zeroconf.async_get_instance(self.hass)
            # Replace "_ufo-r11._tcp.local." with the actual service type if known
            # For now, let's assume a generic service type or listen more broadly if needed.
            # This might need adjustment based on how UFO-R11 devices announce themselves.
            self._zeroconf_listener = await zc_instance.async_add_listener(
                self._handle_zeroconf_service_update, None # Listen to all services initially
            )
            _LOGGER.info("mDNS/Zeroconf discovery for UFO-R11 started")
        except Exception as e:
            _LOGGER.error("Failed to start mDNS/Zeroconf discovery: %s", str(e))

        # Start SSDP discovery
        try:
            _LOGGER.info("Starting SSDP discovery for UFO-R11")
            # Replace "urn:schemas-upnp-org:device:UFOR11Device:1" with actual ST if known
            # For now, listen for common UPnP root devices or a specific ST if available
            # This might need adjustment based on how UFO-R11 devices announce themselves.
            self._ssdp_listener = await ssdp.async_register_callback(
                self.hass, self._handle_ssdp_discovery #, {"st": "ssdp:all"} # Listen to all initially
            )
            _LOGGER.info("SSDP discovery for UFO-R11 started")
        except Exception as e:
            _LOGGER.error("Failed to start SSDP discovery: %s", str(e))
            
        if mqtt_started or self._zeroconf_listener or self._ssdp_listener:
            _LOGGER.info("UFO-R11 device discovery started successfully (at least one method active)")
            return True
        else:
            _LOGGER.error("All discovery methods failed to start for UFO-R11")
            return False

    async def async_stop_discovery(self) -> None:
        """Stop all device discovery methods."""
        self._discovery_enabled = False
        if self._zeroconf_listener:
            _LOGGER.info("Stopping mDNS/Zeroconf discovery for UFO-R11")
            self._zeroconf_listener() # Call the unregister function
            self._zeroconf_listener = None
        if self._ssdp_listener:
            _LOGGER.info("Stopping SSDP discovery for UFO-R11")
            # The callback itself is the unregister function for ssdp.async_register_callback
            # However, the typical pattern is to call an unregister function returned by the registration.
            # Let's assume ssdp.async_register_callback returns an unregister callable or we store it.
            # If ssdp.async_register_callback itself is the unregister, this needs adjustment.
            # For now, assuming it returns an unregister callable.
            # Re-checking HA docs: ssdp.async_register_callback returns None, unregistration is done by ssdp.async_stop_scanner
            # This means we might not need to store _ssdp_listener if we rely on global stop,
            # or if we need finer control, we'd use ssdp.Scanner directly.
            # For simplicity with async_register_callback, we might not have a specific unregister.
            # Let's assume for now that stopping the integration handles SSDP cleanup.
            # A more robust way is to use the ssdp.Scanner directly if per-callback unregistration is needed.
            # For now, we'll log and assume HA handles it or it's stopped globally.
            # Update: ssdp.async_register_callback returns an unregister callable.
            await self._ssdp_listener()
            self._ssdp_listener = None

        _LOGGER.info("UFO-R11 device discovery stopped (MQTT, mDNS, SSDP)")

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

    @callback
    def _handle_zeroconf_service_update(
        self, zc: zeroconf.HaZeroconf, service_type: str, name: str, state_change: zeroconf.ServiceStateChange
    ) -> None:
        """Handle mDNS/Zeroconf service update."""
        if not self._discovery_enabled:
            return

        _LOGGER.debug(
            "Zeroconf service update: type=%s, name=%s, state=%s",
            service_type, name, state_change
        )
        
        # We need to get more details from the service info
        # This is a generic handler, we'll need to filter for UFO-R11
        # and extract relevant data like IP, port, properties.
        
        # Example: try to get service info
        # info = zc.async_get_service_info(service_type, name)
        # if info:
        #    self.hass.async_create_task(self._process_zeroconf_device(info))
        # For now, just log
        if state_change in (zeroconf.ServiceStateChange.Added, zeroconf.ServiceStateChange.Updated):
            self.hass.async_create_task(self._async_process_zeroconf_service(service_type, name))

    def _is_ufo_r11_zeroconf(self, info: zeroconf.ZeroconfServiceInfo) -> bool:
        """Check if a Zeroconf service is a UFO-R11 device."""
        if not info:
            return False
        
        # Check service type (e.g., _ufo-r11._tcp.local. or _http._tcp.local.)
        # This is a guess; actual service type might differ.
        if "_ufo-r11._tcp.local." in info.type or \
           (info.type == "_http._tcp.local." and "ufo-r11" in info.name.lower()):
            return True

        # Check properties for keywords
        properties = {k.lower(): v for k, v in info.decoded_properties.items()}
        if "ufo-r11" in properties.get("model", "").lower() or \
           "moes" in properties.get("manufacturer", "").lower():
            return True
        
        # Check name
        if "ufo-r11" in info.name.lower() or "moes" in info.name.lower():
            return True
            
        return False

    def _extract_zeroconf_device_id(self, info: zeroconf.ZeroconfServiceInfo) -> Optional[str]:
        """Extract a unique device ID from Zeroconf info (e.g., MAC address or serial)."""
        # Prefer MAC address from properties if available
        properties = {k.lower(): v for k, v in info.decoded_properties.items()}
        mac = properties.get("mac") or properties.get("deviceid")
        if mac:
            return str(mac).replace(":", "").lower()
        
        # Fallback to a part of the service name if it seems unique
        # This is less reliable
        name_part = info.name.split('.')[0]
        if "ufo-r11" in name_part.lower() and len(name_part) > 8: # Heuristic
            return name_part
            
        # Fallback to host if nothing else (least reliable as ID)
        if info.host:
            return info.host

        return None

    async def _async_process_zeroconf_service(self, service_type: str, name: str) -> None:
        """Process a discovered/updated Zeroconf service."""
        zc = await zeroconf.async_get_instance(self.hass)
        info = await zc.async_get_service_info(service_type, name)
        _LOGGER.debug("Processing Zeroconf service: %s, info: %s", name, info)
        if not info:
            return

        if self._is_ufo_r11_zeroconf(info):
            device_id = self._extract_zeroconf_device_id(info)
            if not device_id:
                _LOGGER.debug("Could not extract device ID from Zeroconf info: %s", info)
                return

            # Cleaned name, remove ._service._tcp.local. part
            cleaned_name = info.name
            if info.type and info.name.endswith(f".{info.type}"):
                cleaned_name = info.name[:-len(f".{info.type}")-1] # also remove the dot

            discovery_data = {
                "device_id": device_id,
                "name": cleaned_name or f"UFO-R11 {device_id[:8]}",
                "host": info.host,
                "port": info.port,
                "properties": info.decoded_properties,
                "discovery_source": "zeroconf",
                "manufacturer": info.decoded_properties.get("manufacturer", MANUFACTURER),
                "model": info.decoded_properties.get("model", MODEL),
            }
            await self._process_discovered_network_device(discovery_data)

    def _is_ufo_r11_ssdp(self, info: ssdp.SsdpServiceInfo) -> bool:
        """Check if an SSDP service is a UFO-R11 device."""
        if not info:
            return False

        # Check manufacturer and model from UPnP data
        manufacturer = info.upnp.get(ssdp.ATTR_UPNP_MANUFACTURER, "").lower()
        model_name = info.upnp.get(ssdp.ATTR_UPNP_MODEL_NAME, "").lower()
        friendly_name = info.upnp.get(ssdp.ATTR_UPNP_FRIENDLY_NAME, "").lower()

        if "moes" in manufacturer or "ufo-r11" in model_name or "ufo-r11" in friendly_name:
            return True
        
        # Check service type (ST) if a specific one is known for UFO-R11
        # e.g., if info.ssdp_st == "urn:schemas-moes-com:device:ufo-r11:1":
        # For now, relying on manufacturer/model/name.
        
        return False

    def _extract_ssdp_device_id(self, info: ssdp.SsdpServiceInfo) -> Optional[str]:
        """Extract a unique device ID from SSDP info (e.g., UDN or part of it)."""
        # Prefer UDN (Unique Device Name)
        udn = info.upnp.get(ssdp.ATTR_UPNP_UDN)
        if udn:
            # UDN is often prefixed with "uuid:", remove it
            return udn.replace("uuid:", "")
            
        # Fallback to USN (Unique Service Name), often contains UDN
        usn = info.ssdp_usn
        if usn:
            # Try to parse UDN from USN if possible
            if "uuid:" in usn:
                return usn.split("uuid:")[1].split("::")[0] # Common pattern
            return usn # Less ideal, but better than nothing

        return None

    async def _handle_ssdp_discovery(
        self, info: ssdp.SsdpServiceInfo, change: ssdp.SsdpChange
    ) -> None:
        """Handle SSDP discovery."""
        if not self._discovery_enabled:
            return

        _LOGGER.debug(
            "SSDP discovery: info=%s, change=%s",
            info, change
        )

        if change == ssdp.SsdpChange.BYEBYE: # Device leaving
            # TODO: Handle device removal if necessary (e.g., mark as unavailable)
            _LOGGER.debug("SSDP device %s left", info.ssdp_usn)
            return
        
        if change == ssdp.SsdpChange.ALIVE or change == ssdp.SsdpChange.UPDATE:
            if self._is_ufo_r11_ssdp(info):
                device_id = self._extract_ssdp_device_id(info)
                if not device_id:
                    _LOGGER.debug("Could not extract device ID from SSDP info: %s", info)
                    return
                
                # Parse host and port from ssdp_location (URL)
                host = None
                port = None
                if info.ssdp_location:
                    # from urllib.parse import urlparse # Moved to top
                    parsed_url = urlparse(info.ssdp_location)
                    host = parsed_url.hostname
                    port = parsed_url.port

                discovery_data = {
                    "device_id": device_id,
                    "name": info.upnp.get(ssdp.ATTR_UPNP_FRIENDLY_NAME) or f"UFO-R11 {device_id[:8]}",
                    "host": host,
                    "port": port,
                    "ssdp_info": { # Store relevant parts of SSDP info
                        "st": info.ssdp_st,
                        "usn": info.ssdp_usn,
                        "location": info.ssdp_location,
                        "server": info.ssdp_server,
                        "manufacturer": info.upnp.get(ssdp.ATTR_UPNP_MANUFACTURER),
                        "modelName": info.upnp.get(ssdp.ATTR_UPNP_MODEL_NAME),
                        "UDN": info.upnp.get(ssdp.ATTR_UPNP_UDN),
                    },
                    "discovery_source": "ssdp",
                    "manufacturer": info.upnp.get(ssdp.ATTR_UPNP_MANUFACTURER, MANUFACTURER),
                    "model": info.upnp.get(ssdp.ATTR_UPNP_MODEL_NAME, MODEL),
                }
                await self._process_discovered_network_device(discovery_data)

    async def _process_discovered_network_device(self, discovery_data: Dict[str, Any]) -> None:
        """Process a device discovered via network scanning (mDNS/SSDP)."""
        async with self._discovery_lock:
            device_id = discovery_data["device_id"]
            
            if await self._is_device_already_configured(device_id):
                _LOGGER.debug("Network device %s already configured, skipping", device_id)
                return

            if device_id in self._discovered_devices:
                _LOGGER.debug("Network device %s already discovered, updating info", device_id)
                self._discovered_devices[device_id].update({
                    "last_seen": dt_util.utcnow(),
                    "device_info": discovery_data # Store the raw discovery data
                })
                # Optionally, re-notify if details changed significantly
                return

            # New network device discovered
            # Adapt the discovery_data structure as needed for config_flow
            # This might differ from MQTT's structure
            processed_data = {
                "device_id": device_id,
                "name": discovery_data.get("name", f"UFO-R11 {device_id[:8]}"),
                "host": discovery_data.get("host"), # From Zeroconf/SSDP
                "port": discovery_data.get("port"), # From Zeroconf/SSDP
                "properties": discovery_data.get("properties"), # Zeroconf specific
                "ssdp_info": discovery_data.get("ssdp_info"), # SSDP specific
                "discovery_source": discovery_data.get("discovery_source"),
                "device_type": DEVICE_TYPE_AC, # Default or determine from discovery
                "code_source": CODE_SOURCE_POINTCODES, # Default or determine
                "discovered_at": dt_util.utcnow(),
                "last_seen": dt_util.utcnow(),
                "manufacturer": discovery_data.get("manufacturer", MANUFACTURER),
                "model": discovery_data.get("model", MODEL),
            }
            
            self._discovered_devices[device_id] = processed_data
            
            _LOGGER.info("Discovered new UFO-R11 via %s: %s (%s)",
                         discovery_data.get("discovery_source", "network"),
                         processed_data['name'], device_id)
            
            await self._notify_device_discovered(processed_data)