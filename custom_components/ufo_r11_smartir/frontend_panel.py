"""Frontend panel registration for UFO-R11 SmartIR integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the UFO-R11 SmartIR frontend panel."""
    try:
        # Get the path to our www directory
        www_path = Path(__file__).parent / "www"
        
        # Register the static files directory
        hass.http.register_static_path(
            f"/api/{DOMAIN}/static",
            str(www_path),
            cache_headers=True
        )
        
        # Register the frontend panel
        await frontend.async_register_built_in_panel(
            hass,
            component_name=DOMAIN,
            sidebar_title="UFO-R11 SmartIR",
            sidebar_icon="mdi:remote",
            frontend_url_path=DOMAIN,
            config={
                "js_url": f"/api/{DOMAIN}/static/ufo-r11-panel.js",
                "css_url": f"/api/{DOMAIN}/static/ufo-r11-styles.css",
            },
        )
        
        _LOGGER.info("UFO-R11 SmartIR frontend panel registered successfully")
        
    except Exception as e:
        _LOGGER.error("Failed to register UFO-R11 SmartIR frontend panel: %s", e)
        raise


async def async_setup_frontend_panel(hass: HomeAssistant) -> None:
    """Set up the UFO-R11 SmartIR frontend panel."""
    try:
        # Register the frontend panel
        await async_register_panel(hass)
        
        # Store panel setup state for potential cleanup
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["frontend_panel_registered"] = True
        
        _LOGGER.info("UFO-R11 SmartIR frontend panel setup completed")
        
    except Exception as e:
        _LOGGER.error("Failed to setup UFO-R11 SmartIR frontend panel: %s", e)
        raise


async def async_unregister_panel(hass: HomeAssistant) -> None:
    """Unregister the UFO-R11 SmartIR frontend panel."""
    try:
        # Remove the panel
        if DOMAIN in hass.data.get("frontend_panels", {}):
            hass.data["frontend_panels"].pop(DOMAIN, None)
            _LOGGER.info("UFO-R11 SmartIR frontend panel unregistered")
    except Exception as e:
        _LOGGER.error("Failed to unregister UFO-R11 SmartIR frontend panel: %s", e)