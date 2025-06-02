"""HTTP API endpoints for UFO-R11 SmartIR frontend communication."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict

from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    ATTR_DEVICE_ID,
    ATTR_COMMAND_NAME,
    ATTR_TIMEOUT,
    ATTR_OUTPUT_PATH,
    ATTR_IR_CODE,
    SERVICE_LEARN_IR_CODE,
    SERVICE_EXPORT_SMARTIR,
    SERVICE_IMPORT_CODES,
    SERVICE_TEST_COMMAND,
)

_LOGGER = logging.getLogger(__name__)


class UFORView(HomeAssistantView):
    """Base view for UFO-R11 API endpoints."""

    url = "/api/ufo_r11_smartir"
    name = "api:ufo_r11_smartir"
    requires_auth = True

    def __init__(self, hass: HomeAssistant):
        """Initialize the view."""
        self.hass = hass

    def _get_coordinator(self, device_id: str):
        """Get coordinator for device ID."""
        for entry_id, coordinator in self.hass.data.get(DOMAIN, {}).items():
            if coordinator.device_id == device_id:
                return coordinator
        return None

    def _get_device_manager(self, device_id: str):
        """Get device manager for device ID."""
        coordinator = self._get_coordinator(device_id)
        if coordinator:
            return coordinator.device_manager
        return None


class DevicesListView(UFORView):
    """View to list all UFO-R11 devices."""

    url = "/api/ufo_r11_smartir/devices"
    name = "api:ufo_r11_smartir:devices"

    async def get(self, request: web.Request) -> web.Response:
        """Get list of all devices."""
        try:
            devices = []
            for entry_id, coordinator in self.hass.data.get(DOMAIN, {}).items():
                device_data = {
                    "device_id": coordinator.device_id,
                    "device_name": coordinator.device_name,
                    "mqtt_topic": coordinator.mqtt_topic,
                    "available": coordinator.data.get("available", False),
                    "last_seen": coordinator.data.get("last_seen"),
                }
                
                # Get device manager info
                if coordinator.device_manager:
                    summary = coordinator.device_manager._ir_manager.get_device_summary(coordinator.device_id)
                    if summary:
                        device_data.update(summary)
                
                devices.append(device_data)
            
            return web.json_response({"devices": devices})
            
        except Exception as e:
            _LOGGER.error("Error getting devices list: %s", e)
            return web.json_response({"error": str(e)}, status=500)


class DeviceInfoView(UFORView):
    """View to get device information."""

    url = "/api/ufo_r11_smartir/device/{device_id}"
    name = "api:ufo_r11_smartir:device_info"

    async def get(self, request: web.Request) -> web.Response:
        """Get device information."""
        try:
            device_id = request.match_info["device_id"]
            coordinator = self._get_coordinator(device_id)
            
            if not coordinator:
                return web.json_response({"error": "Device not found"}, status=404)
            
            device_info = {
                "device_id": coordinator.device_id,
                "device_name": coordinator.device_name,
                "mqtt_topic": coordinator.mqtt_topic,
                "available": coordinator.data.get("available", False),
                "last_seen": coordinator.data.get("last_seen"),
            }
            
            # Get detailed device manager info
            if coordinator.device_manager:
                summary = coordinator.device_manager._ir_manager.get_device_summary(device_id)
                if summary:
                    device_info.update(summary)
                
                # Get learning status
                learning_status = coordinator.device_manager.get_learning_status(device_id)
                if learning_status:
                    device_info["learning_status"] = learning_status
                
                # Get available commands
                code_set = await coordinator.device_manager.async_get_device_codes(device_id)
                if code_set:
                    device_info["commands"] = code_set.get_all_commands()
            
            return web.json_response(device_info)
            
        except Exception as e:
            _LOGGER.error("Error getting device info for %s: %s", device_id, e)
            return web.json_response({"error": str(e)}, status=500)


class LearnCommandView(UFORView):
    """View to start IR command learning."""

    url = "/api/ufo_r11_smartir/learn"
    name = "api:ufo_r11_smartir:learn"

    async def post(self, request: web.Request) -> web.Response:
        """Start learning IR command."""
        try:
            data = await request.json()
            device_id = data.get(ATTR_DEVICE_ID)
            command_name = data.get(ATTR_COMMAND_NAME)
            timeout = data.get(ATTR_TIMEOUT, 30)
            
            if not device_id or not command_name:
                return web.json_response(
                    {"error": "device_id and command_name are required"}, 
                    status=400
                )
            
            # Call the service
            await self.hass.services.async_call(
                DOMAIN,
                SERVICE_LEARN_IR_CODE,
                {
                    ATTR_DEVICE_ID: device_id,
                    ATTR_COMMAND_NAME: command_name,
                    ATTR_TIMEOUT: timeout,
                },
                blocking=True,
            )
            
            return web.json_response({"success": True, "message": "Learning started"})
            
        except Exception as e:
            _LOGGER.error("Error starting IR learning: %s", e)
            return web.json_response({"error": str(e)}, status=500)


class TestCommandView(UFORView):
    """View to test IR command."""

    url = "/api/ufo_r11_smartir/test"
    name = "api:ufo_r11_smartir:test"

    async def post(self, request: web.Request) -> web.Response:
        """Test IR command."""
        try:
            data = await request.json()
            device_id = data.get(ATTR_DEVICE_ID)
            ir_code = data.get(ATTR_IR_CODE)
            
            if not device_id or not ir_code:
                return web.json_response(
                    {"error": "device_id and ir_code are required"}, 
                    status=400
                )
            
            # Call the service
            await self.hass.services.async_call(
                DOMAIN,
                SERVICE_TEST_COMMAND,
                {
                    ATTR_DEVICE_ID: device_id,
                    ATTR_IR_CODE: ir_code,
                },
                blocking=True,
            )
            
            return web.json_response({"success": True, "message": "Command sent"})
            
        except Exception as e:
            _LOGGER.error("Error testing IR command: %s", e)
            return web.json_response({"error": str(e)}, status=500)


class ExportSmartIRView(UFORView):
    """View to export SmartIR configuration."""

    url = "/api/ufo_r11_smartir/export"
    name = "api:ufo_r11_smartir:export"

    async def post(self, request: web.Request) -> web.Response:
        """Export SmartIR configuration."""
        try:
            data = await request.json()
            device_id = data.get(ATTR_DEVICE_ID)
            output_path = data.get(ATTR_OUTPUT_PATH)
            
            if not device_id:
                return web.json_response(
                    {"error": "device_id is required"}, 
                    status=400
                )
            
            # Call the service
            await self.hass.services.async_call(
                DOMAIN,
                SERVICE_EXPORT_SMARTIR,
                {
                    ATTR_DEVICE_ID: device_id,
                    ATTR_OUTPUT_PATH: output_path,
                },
                blocking=True,
            )
            
            return web.json_response({"success": True, "message": "Export completed"})
            
        except Exception as e:
            _LOGGER.error("Error exporting SmartIR config: %s", e)
            return web.json_response({"error": str(e)}, status=500)


class ImportCodesView(UFORView):
    """View to import IR codes."""

    url = "/api/ufo_r11_smartir/import"
    name = "api:ufo_r11_smartir:import"

    async def post(self, request: web.Request) -> web.Response:
        """Import IR codes from file."""
        try:
            data = await request.json()
            device_id = data.get(ATTR_DEVICE_ID)
            file_path = data.get("file_path")
            
            if not device_id or not file_path:
                return web.json_response(
                    {"error": "device_id and file_path are required"}, 
                    status=400
                )
            
            # Call the service
            await self.hass.services.async_call(
                DOMAIN,
                SERVICE_IMPORT_CODES,
                {
                    ATTR_DEVICE_ID: device_id,
                    "file_path": file_path,
                },
                blocking=True,
            )
            
            return web.json_response({"success": True, "message": "Import completed"})
            
        except Exception as e:
            _LOGGER.error("Error importing IR codes: %s", e)
            return web.json_response({"error": str(e)}, status=500)


# WebSocket API for real-time updates
@websocket_api.require_admin
@websocket_api.websocket_command({"type": "ufo_r11_smartir/subscribe"})
@callback
def websocket_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: Dict[str, Any],
) -> None:
    """Subscribe to UFO-R11 SmartIR updates."""
    
    @callback
    def device_update_listener(event):
        """Forward device updates to WebSocket."""
        if event.event_type == f"{DOMAIN}_device_update":
            connection.send_message(
                websocket_api.event_message(
                    msg["id"],
                    {
                        "type": "device_update",
                        "data": event.data,
                    },
                )
            )
    
    @callback
    def learning_update_listener(event):
        """Forward learning updates to WebSocket."""
        if event.event_type == f"{DOMAIN}_learning_update":
            connection.send_message(
                websocket_api.event_message(
                    msg["id"],
                    {
                        "type": "learning_update",
                        "data": event.data,
                    },
                )
            )
    
    # Listen for device and learning updates
    connection.subscriptions[msg["id"]] = [
        hass.bus.async_listen(f"{DOMAIN}_device_update", device_update_listener),
        hass.bus.async_listen(f"{DOMAIN}_learning_update", learning_update_listener),
    ]
    
    connection.send_message(websocket_api.result_message(msg["id"]))


@websocket_api.require_admin
@websocket_api.websocket_command({"type": "ufo_r11_smartir/get_devices"})
@callback
def websocket_get_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: Dict[str, Any],
) -> None:
    """Get devices via WebSocket."""
    try:
        devices = []
        for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
            device_data = {
                "device_id": coordinator.device_id,
                "device_name": coordinator.device_name,
                "mqtt_topic": coordinator.mqtt_topic,
                "available": coordinator.data.get("available", False),
                "last_seen": coordinator.data.get("last_seen"),
            }
            
            # Get device manager info
            if coordinator.device_manager:
                summary = coordinator.device_manager._ir_manager.get_device_summary(coordinator.device_id)
                if summary:
                    device_data.update(summary)
            
            devices.append(device_data)
        
        connection.send_message(
            websocket_api.result_message(msg["id"], {"devices": devices})
        )
    except Exception as e:
        connection.send_message(
            websocket_api.error_message(msg["id"], "get_devices_error", str(e))
        )


async def async_setup_api(hass: HomeAssistant) -> None:
    """Set up the API endpoints."""
    # Register HTTP views
    hass.http.register_view(DevicesListView(hass))
    hass.http.register_view(DeviceInfoView(hass))
    hass.http.register_view(LearnCommandView(hass))
    hass.http.register_view(TestCommandView(hass))
    hass.http.register_view(ExportSmartIRView(hass))
    hass.http.register_view(ImportCodesView(hass))
    
    # Register WebSocket commands
    websocket_api.async_register_command(hass, websocket_subscribe)
    websocket_api.async_register_command(hass, websocket_get_devices)
    
    _LOGGER.info("UFO-R11 SmartIR API endpoints registered")