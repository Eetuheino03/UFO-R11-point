"""Config flow for UFO-R11 SmartIR integration."""

from __future__ import annotations

import logging
from typing import Any

from .ha_helpers import vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_MQTT_TOPIC,
    CONF_DEVICE_TYPE,
    CONF_CODE_SOURCE,
    CONF_TEMPLATE,
    DEVICE_TYPES,
    DEVICE_TYPE_AC,
    CODE_SOURCES,
    CODE_SOURCE_POINTCODES,
    ERROR_DEVICE_NOT_FOUND,
    ERROR_MQTT_CONNECTION,
    ERROR_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_DEVICE_NAME): cv.string,
        vol.Required(CONF_MQTT_TOPIC): cv.string,
    }
)

STEP_DEVICE_TYPE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_TYPE, default=DEVICE_TYPE_AC): vol.In(DEVICE_TYPES),
    }
)

STEP_CODE_SOURCE_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CODE_SOURCE, default=CODE_SOURCE_POINTCODES): vol.In(
            CODE_SOURCES
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    device_id = data[CONF_DEVICE_ID]
    mqtt_topic = data[CONF_MQTT_TOPIC]

    # Validate MQTT connection and device availability
    if "mqtt" not in hass.config.components:
        raise CannotConnect("MQTT integration not found")

    # TODO: Add actual device validation logic
    # This would involve:
    # 1. Check if MQTT broker is reachable
    # 2. Verify UFO-R11 device exists at specified topic
    # 3. Test basic communication with device

    # For now, just basic validation
    if not device_id or not mqtt_topic:
        raise InvalidDevice("Device ID and MQTT topic are required")

    # Return info that you want to store in the config entry
    return {
        "title": data[CONF_DEVICE_NAME],
        "device_id": device_id,
        "mqtt_topic": mqtt_topic,
    }


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UFO-R11 SmartIR."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.discovery_info: dict[str, Any] = {}
        self.device_config: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                # Check if device is already configured
                await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
                self._abort_if_unique_id_configured()

                # Store the basic device info
                self.device_config.update(user_input)
                self.device_config["title"] = info["title"]

                # Move to device type selection
                return await self.async_step_device_type()

            except CannotConnect:
                errors["base"] = ERROR_MQTT_CONNECTION
            except InvalidDevice:
                errors["base"] = ERROR_DEVICE_NOT_FOUND
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = ERROR_UNKNOWN

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "example_device_id": "0x00158d00012345ab",
                "example_topic": "zigbee2mqtt/UFO-R11-Device",
            },
        )

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device type selection step."""
        if user_input is not None:
            self.device_config.update(user_input)
            return await self.async_step_code_source()

        return self.async_show_form(
            step_id="device_type",
            data_schema=STEP_DEVICE_TYPE_DATA_SCHEMA,
            description_placeholders={
                "device_name": self.device_config.get(CONF_DEVICE_NAME, "Unknown"),
            },
        )

    async def async_step_code_source(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle IR code source selection step."""
        if user_input is not None:
            self.device_config.update(user_input)
            return await self.async_step_test_device()

        return self.async_show_form(
            step_id="code_source",
            data_schema=STEP_CODE_SOURCE_DATA_SCHEMA,
            description_placeholders={
                "device_type": self.device_config.get(CONF_DEVICE_TYPE, "unknown"),
            },
        )

    async def async_step_test_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle device testing step."""
        if user_input is not None:
            if user_input.get("test_result") == "success":
                # Create the config entry
                return self.async_create_entry(
                    title=self.device_config["title"],
                    data=self.device_config,
                )
            else:
                # Return to code source selection if test failed
                return await self.async_step_code_source()

        # TODO: Implement actual device testing
        # This would involve:
        # 1. Load appropriate IR codes based on device type and source
        # 2. Send test commands to the device
        # 3. Provide user interface for confirming device response

        # For now, show a simple test form
        test_schema = vol.Schema(
            {
                vol.Required("test_result", default="success"): vol.In(
                    ["success", "retry"]
                ),
            }
        )

        return self.async_show_form(
            step_id="test_device",
            data_schema=test_schema,
            description_placeholders={
                "device_name": self.device_config.get(CONF_DEVICE_NAME, "Unknown"),
                "device_type": self.device_config.get(CONF_DEVICE_TYPE, "unknown"),
                "code_source": self.device_config.get(CONF_CODE_SOURCE, "unknown"),
            },
        )

    async def async_step_discovery(self, discovery_info: dict[str, Any]) -> FlowResult:
        """Handle discovery of UFO-R11 devices."""
        _LOGGER.info("Processing discovered UFO-R11 device: %s", discovery_info)

        # Store discovery info for later use
        self.discovery_info = discovery_info

        device_id = discovery_info.get("device_id")
        if device_id:
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            # Pre-populate form with discovered information
            device_name = discovery_info.get("name", f"UFO-R11 {device_id[-8:]}")
            mqtt_topic = discovery_info.get("topic")  # MQTT specific
            host = discovery_info.get("host")  # Zeroconf/SSDP specific
            port = discovery_info.get("port")  # Zeroconf/SSDP specific
            discovery_source = discovery_info.get("discovery_source", "unknown")

            self.device_config.update(
                {
                    CONF_DEVICE_ID: device_id,
                    CONF_DEVICE_NAME: device_name,
                    CONF_DEVICE_TYPE: discovery_info.get("device_type", DEVICE_TYPE_AC),
                    CONF_CODE_SOURCE: discovery_info.get(
                        "code_source", CODE_SOURCE_POINTCODES
                    ),
                    # Store discovery source and related network info
                    "discovery_source": discovery_source,
                    "host": host,
                    "port": port,
                }
            )

            # MQTT topic is still primary for this integration's current device comms
            # If not an MQTT discovery, we might need a placeholder or adapt further.
            # For now, if it's not MQTT, we'll construct a potential default or leave it empty
            # and rely on the user to confirm/provide if needed, or adapt the integration
            # to use host/port directly if that's the new communication method.
            # Assuming MQTT is still the core communication method for IR commands.
            if mqtt_topic:
                self.device_config[CONF_MQTT_TOPIC] = mqtt_topic
            elif (
                host
            ):  # If discovered via network, create a placeholder topic or decide strategy
                # This part depends on how non-MQTT devices would be controlled.
                # If they still use MQTT via a bridge, this topic might be derivable.
                # If they use direct IP communication, CONF_MQTT_TOPIC might become optional/irrelevant.
                # For now, let's assume a default pattern if it's a network discovery
                # that might still be bridged to MQTT by some other means, or user needs to fill it.
                self.device_config[CONF_MQTT_TOPIC] = (
                    f"{discovery_info.get(CONF_MQTT_TOPIC, f'ufo_r11/{device_id}')}"
                )
            else:  # Fallback if no topic and no host
                self.device_config[CONF_MQTT_TOPIC] = f"zigbee2mqtt/{device_id}"

            # Show discovery confirmation form
            return await self.async_step_discovery_confirm()

        # Fall back to manual configuration
        return await self.async_step_user()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery of UFO-R11 device."""
        if user_input is not None:
            if user_input.get("confirm_discovery"):
                # Create config entry directly from discovered data
                return self.async_create_entry(
                    title=self.device_config[CONF_DEVICE_NAME],
                    data=self.device_config,
                )
            else:
                # User declined, allow manual configuration
                return await self.async_step_user()

        # Show confirmation form
        discovery_schema = vol.Schema(
            {
                vol.Required("confirm_discovery", default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=discovery_schema,
            description_placeholders={
                "device_name": self.device_config.get(CONF_DEVICE_NAME, "Unknown"),
                "device_id": self.device_config.get(CONF_DEVICE_ID, "Unknown"),
                "mqtt_topic": self.device_config.get(
                    CONF_MQTT_TOPIC, "N/A if direct IP"
                ),
                "host": self.device_config.get("host", "N/A"),
                "port": self.device_config.get("port", "N/A"),
                "discovery_source": self.device_config.get(
                    "discovery_source", "Unknown"
                ),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for UFO-R11 SmartIR."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        _LOGGER.debug("DEBUG: Initializing OptionsFlowHandler with modern HA pattern")
        _LOGGER.info("DEBUG: Using modern Home Assistant inheritance pattern!")
        super().__init__()
        _LOGGER.debug("DEBUG: OptionsFlow initialized successfully")

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    "update_interval",
                    default=self.config_entry.options.get("update_interval", 30),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                vol.Optional(
                    "enable_learning",
                    default=self.config_entry.options.get("enable_learning", True),
                ): bool,
                vol.Optional(
                    "enable_discovery",
                    default=self.config_entry.options.get("enable_discovery", True),
                ): bool,
                vol.Optional(
                    "auto_export",
                    default=self.config_entry.options.get("auto_export", False),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidDevice(HomeAssistantError):
    """Error to indicate there is invalid device information."""
