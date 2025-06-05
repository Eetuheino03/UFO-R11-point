"""The UFO-R11 SmartIR integration."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import timedelta
from typing import Any

from .ha_helpers import vol

if os.environ.get("USE_HOMEASSISTANT") == "1":
    try:
        from homeassistant.config_entries import ConfigEntry  # type: ignore
        from homeassistant.const import Platform  # type: ignore
        from homeassistant.core import HomeAssistant  # type: ignore
        from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady  # type: ignore
        from homeassistant.helpers import config_validation as cv  # type: ignore
        from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed  # type: ignore
        from homeassistant.components.http import HomeAssistantView  # type: ignore

        HA_AVAILABLE = True
    except Exception:  # pragma: no cover - allow running without Home Assistant
        HA_AVAILABLE = False
else:
    HA_AVAILABLE = False
if not HA_AVAILABLE:

    class HomeAssistant:  # type: ignore
        pass

    class ConfigEntry:  # type: ignore
        pass

    class Platform(str):  # type: ignore
        CLIMATE = "climate"

    class ConfigEntryError(Exception):
        pass

    class ConfigEntryNotReady(Exception):
        pass

    class DataUpdateCoordinator:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

        async def async_config_entry_first_refresh(self) -> None:
            return None

    class UpdateFailed(Exception):
        pass

    class HomeAssistantView:  # type: ignore
        pass

    class cv:  # type: ignore
        string = lambda x: x
        positive_int = int

    from .ha_helpers import vol

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_MQTT_TOPIC,
    CONF_DEVICE_TYPE,
    CONF_CODE_SOURCE,
    UPDATE_INTERVAL,
    SERVICE_LEARN_IR_CODE,
    SERVICE_EXPORT_SMARTIR,
    SERVICE_IMPORT_CODES,
    SERVICE_TEST_COMMAND,
    ATTR_DEVICE_ID,
    ATTR_COMMAND_NAME,
    ATTR_TIMEOUT,
    ATTR_OUTPUT_PATH,
    ATTR_IR_CODE,
    CODE_SOURCE_POINTCODES,
    DEVICE_TYPE_AC,
)

if HA_AVAILABLE:
    from .device_manager import DeviceManager
    from .smartir_generator import SmartIRGenerator
    from .api import async_setup_api
    from .frontend_panel import async_setup_frontend_panel, async_unregister_panel
    from .discovery import UFODeviceDiscovery

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE]

# Service schemas
LEARN_IR_CODE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_COMMAND_NAME): cv.string,
        vol.Optional(ATTR_TIMEOUT, default=30): cv.positive_int,
    }
)

EXPORT_SMARTIR_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_OUTPUT_PATH): cv.string,
    }
)

IMPORT_CODES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required("file_path"): cv.string,
    }
)

TEST_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_IR_CODE): cv.string,
    }
)


class UFODataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the UFO-R11 device."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_id: str,
        device_name: str,
        mqtt_topic: str,
    ) -> None:
        """Initialize."""
        self.device_id = device_id
        self.device_name = device_name
        self.mqtt_topic = mqtt_topic
        self.device_data = {}
        self.device_manager: DeviceManager | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_setup_device_manager(self) -> None:
        """Set up the device manager with IR code processing."""
        try:
            self.device_manager = DeviceManager(self.hass)

            # Setup device from Point-codes if configured for Point-codes source
            pointcodes_path = self.hass.config.path(
                f"custom_components/{DOMAIN}/data/Point-codes"
            )

            await self.device_manager.async_setup_device(
                device_id=self.device_id,
                device_name=self.device_name,
                device_type=DEVICE_TYPE_AC,
                code_source=CODE_SOURCE_POINTCODES,
            )

            _LOGGER.info(
                "Device manager initialized for device %s with Point-codes",
                self.device_id,
            )

        except Exception as err:
            _LOGGER.error(
                "Failed to setup device manager for %s: %s", self.device_id, err
            )
            raise ConfigEntryError(f"Failed to setup device manager: {err}") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            # Check device availability via MQTT
            # This is a placeholder for actual device status checking
            _LOGGER.debug("DEBUG: Attempting to get current UTC time")
            try:
                # Try modern HA datetime utility
                from homeassistant.util import dt as dt_util

                current_time = dt_util.utcnow()
                _LOGGER.debug("DEBUG: Successfully got time using dt_util.utcnow()")
            except AttributeError as dt_err:
                _LOGGER.error("DEBUG: dt_util.utcnow() failed: %s", dt_err)
                # Fallback to standard datetime
                from datetime import datetime, timezone

                current_time = datetime.now(timezone.utc)
                _LOGGER.debug("DEBUG: Using fallback datetime.now(timezone.utc)")

            return {
                "available": True,
                "last_seen": current_time,
                "device_id": self.device_id,
                "device_name": self.device_name,
                "topic": self.mqtt_topic,
                "device_manager": self.device_manager,
            }
        except Exception as exception:
            _LOGGER.error("DEBUG: Exception in _async_update_data: %s", exception)
            raise UpdateFailed(exception) from exception


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UFO-R11 SmartIR from a config entry."""
    _LOGGER.debug("Setting up UFO-R11 SmartIR integration")

    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data.get(CONF_DEVICE_NAME, device_id)
    mqtt_topic = entry.data[CONF_MQTT_TOPIC]

    # Verify MQTT integration is loaded
    if "mqtt" not in hass.config.components:
        _LOGGER.error("MQTT integration not found")
        raise ConfigEntryNotReady("MQTT integration is required")

    # Initialize the coordinator
    coordinator = UFODataUpdateCoordinator(hass, device_id, device_name, mqtt_topic)

    # Setup device manager with IR code processing
    await coordinator.async_setup_device_manager()

    # Fetch initial data so we have data when entities are added
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Setup API endpoints
    await async_setup_api(hass)

    # Setup frontend panel
    await async_setup_frontend_panel(hass)

    # Setup device discovery (only once for the first entry)
    discovery_key = f"{DOMAIN}_discovery"
    if discovery_key not in hass.data:
        discovery = UFODeviceDiscovery(hass)
        hass.data[discovery_key] = discovery

        # Start discovery with option to enable/disable
        discovery_enabled = entry.options.get("enable_discovery", True)
        if discovery_enabled:
            await discovery.async_start_discovery()
            _LOGGER.info("UFO-R11 device discovery enabled")
        else:
            _LOGGER.info("UFO-R11 device discovery disabled via options")

    # Forward the setup to the platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading UFO-R11 SmartIR integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)

        # Clean up frontend panel
        try:
            await async_unregister_panel(hass)
        except Exception as e:
            _LOGGER.warning("Failed to unregister frontend panel during unload: %s", e)

        # Clean up discovery service if this was the last entry
        remaining_entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        if not remaining_entries:
            discovery_key = f"{DOMAIN}_discovery"
            if discovery_key in hass.data:
                discovery = hass.data.pop(discovery_key)
                await discovery.async_stop_discovery()
                _LOGGER.info("UFO-R11 device discovery stopped")

    return unload_ok


async def _async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for the integration."""

    def _get_device_manager(device_id: str) -> DeviceManager | None:
        """Get device manager for the specified device."""
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            if coordinator.device_id == device_id:
                return coordinator.device_manager
        return None

    async def async_learn_ir_code(call) -> None:
        """Handle learn IR code service call."""
        device_id = call.data[ATTR_DEVICE_ID]
        command_name = call.data[ATTR_COMMAND_NAME]
        timeout = call.data[ATTR_TIMEOUT]

        _LOGGER.info(
            "Learning IR code for device %s, command %s with timeout %d",
            device_id,
            command_name,
            timeout,
        )

        device_manager = _get_device_manager(device_id)
        if not device_manager:
            _LOGGER.error("Device manager not found for device %s", device_id)
            hass.components.persistent_notification.async_create(
                f"Device {device_id} not found or not properly configured",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )
            return

        try:
            # Start learning session
            mqtt_topic = None
            for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
                if coordinator.device_id == device_id:
                    mqtt_topic = coordinator.mqtt_topic
                    break

            if not mqtt_topic:
                raise Exception("MQTT topic not found for device")

            await device_manager.async_learn_ir_command(
                device_id=device_id,
                command_name=command_name,
                category="custom",
                key=command_name.lower().replace(" ", "_"),
                mqtt_topic=mqtt_topic,
                timeout=timeout,
            )

            hass.components.persistent_notification.async_create(
                f"IR code learning started for {command_name}. Point your remote at the UFO-R11 device and press the button within {timeout} seconds.",
                title="UFO-R11 SmartIR",
                notification_id=f"ufo_r11_learning_{device_id}",
            )

        except Exception as err:
            _LOGGER.error("Failed to start learning session: %s", err)
            hass.components.persistent_notification.async_create(
                f"Failed to start learning for {command_name}: {err}",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )

    async def async_export_smartir(call) -> None:
        """Handle export SmartIR service call."""
        device_id = call.data[ATTR_DEVICE_ID]
        output_path = call.data.get(ATTR_OUTPUT_PATH)

        _LOGGER.info("Exporting SmartIR configuration for device %s", device_id)

        device_manager = _get_device_manager(device_id)
        if not device_manager:
            _LOGGER.error("Device manager not found for device %s", device_id)
            hass.components.persistent_notification.async_create(
                f"Device {device_id} not found or not properly configured",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )
            return

        try:
            # Export SmartIR configuration using SmartIRGenerator
            from .smartir_generator import SmartIRGenerator

            generator = SmartIRGenerator(hass)

            # Get device codes
            code_set = await device_manager.async_get_device_codes(device_id)
            if not code_set:
                raise Exception("No IR codes found for device")

            export_path = await generator.async_export_smartir_config(
                code_set=code_set, output_path=output_path
            )

            hass.components.persistent_notification.async_create(
                f"SmartIR configuration exported successfully to: {export_path}",
                title="UFO-R11 SmartIR",
                notification_id=f"ufo_r11_export_{device_id}",
            )

        except Exception as err:
            _LOGGER.error("Failed to export SmartIR config: %s", err)
            hass.components.persistent_notification.async_create(
                f"Failed to export SmartIR configuration: {err}",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )

    async def async_import_codes(call) -> None:
        """Handle import codes service call."""
        device_id = call.data[ATTR_DEVICE_ID]
        file_path = call.data["file_path"]

        _LOGGER.info("Importing IR codes for device %s from %s", device_id, file_path)

        device_manager = _get_device_manager(device_id)
        if not device_manager:
            _LOGGER.error("Device manager not found for device %s", device_id)
            hass.components.persistent_notification.async_create(
                f"Device {device_id} not found or not properly configured",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )
            return

        try:
            # Import IR codes from file
            success = await device_manager.async_import_codes(
                device_id=device_id, file_path=file_path, file_format="pointcodes"
            )

            if success:
                # Get count of commands for notification
                code_set = await device_manager.async_get_device_codes(device_id)
                count = code_set.get_command_count() if code_set else 0
            else:
                raise Exception("Failed to import codes")

            hass.components.persistent_notification.async_create(
                f"Successfully imported {count} IR codes from {file_path}",
                title="UFO-R11 SmartIR",
                notification_id=f"ufo_r11_import_{device_id}",
            )

        except Exception as err:
            _LOGGER.error("Failed to import IR codes: %s", err)
            hass.components.persistent_notification.async_create(
                f"Failed to import IR codes from {file_path}: {err}",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )

    async def async_test_command(call) -> None:
        """Handle test command service call."""
        device_id = call.data[ATTR_DEVICE_ID]
        ir_code = call.data[ATTR_IR_CODE]

        _LOGGER.info("Testing IR command for device %s", device_id)

        device_manager = _get_device_manager(device_id)
        if not device_manager:
            _LOGGER.error("Device manager not found for device %s", device_id)
            hass.components.persistent_notification.async_create(
                f"Device {device_id} not found or not properly configured",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )
            return

        try:
            # Send test IR command
            mqtt_topic = None
            for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
                if coordinator.device_id == device_id:
                    mqtt_topic = coordinator.mqtt_topic
                    break

            if not mqtt_topic:
                raise Exception("MQTT topic not found for device")

            success = await device_manager.async_test_command(
                device_id=device_id, ir_code=ir_code, mqtt_topic=mqtt_topic
            )

            if success:
                hass.components.persistent_notification.async_create(
                    f"IR command sent successfully to device {device_id}",
                    title="UFO-R11 SmartIR",
                    notification_id=f"ufo_r11_test_{device_id}",
                )
            else:
                hass.components.persistent_notification.async_create(
                    f"Failed to send IR command to device {device_id}",
                    title="UFO-R11 SmartIR Error",
                    notification_id=f"ufo_r11_error_{device_id}",
                )

        except Exception as err:
            _LOGGER.error("Failed to test IR command: %s", err)
            hass.components.persistent_notification.async_create(
                f"Failed to test IR command: {err}",
                title="UFO-R11 SmartIR Error",
                notification_id=f"ufo_r11_error_{device_id}",
            )

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_LEARN_IR_CODE,
        async_learn_ir_code,
        schema=LEARN_IR_CODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_EXPORT_SMARTIR,
        async_export_smartir,
        schema=EXPORT_SMARTIR_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_CODES,
        async_import_codes,
        schema=IMPORT_CODES_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_TEST_COMMAND,
        async_test_command,
        schema=TEST_COMMAND_SCHEMA,
    )
