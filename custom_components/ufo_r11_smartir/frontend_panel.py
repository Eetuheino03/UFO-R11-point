"""Frontend panel registration for UFO-R11 SmartIR integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from inspect import iscoroutinefunction

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register the UFO-R11 SmartIR frontend panel."""
    try:
        # Get the path to our www directory
        www_path = Path(__file__).parent / "www"
        
        # Register the static files directory
        if hasattr(hass.http, "async_register_static_paths"):
            try:
                await hass.http.async_register_static_paths([
                    StaticPathConfig(
                        f"/api/{DOMAIN}/static",
                        str(www_path),
                        True,
                    )
                ])
                _LOGGER.debug("Registered static path via async_register_static_paths")
            except Exception as e_reg:
                _LOGGER.warning(
                    "async_register_static_paths failed: %s. Falling back to register_static_path",
                    e_reg,
                )
                hass.http.register_static_path(
                    f"/api/{DOMAIN}/static",
                    str(www_path),
                    cache_headers=True,
                )
        else:
            hass.http.register_static_path(
                f"/api/{DOMAIN}/static",
                str(www_path),
                cache_headers=True,
            )
        
        # Register the frontend panel
        panel_registered_successfully = False
        
        # Register using the built-in 'custom' panel mechanism
        if hasattr(frontend, "async_register_built_in_panel") and frontend.async_register_built_in_panel:
            _LOGGER.debug("Attempting to register panel using async_register_built_in_panel")
            try:
                register_fn = frontend.async_register_built_in_panel
                if iscoroutinefunction(register_fn):
                    await register_fn(
                        hass,
                        component_name="custom",
                        sidebar_title="UFO-R11 SmartIR",
                        sidebar_icon="mdi:remote",
                        frontend_url_path=DOMAIN,
                        config={
                            "_panel_custom": {
                                "name": f"panel-custom-{DOMAIN.replace('_', '-')}",
                                "js_url": f"/api/{DOMAIN}/static/ufo-r11-panel.js",
                                "css_url": f"/api/{DOMAIN}/static/ufo-r11-styles.css",
                            },
                        },
                        require_admin=False,
                    )
                else:
                    register_fn(
                        hass,
                        component_name="custom",
                        sidebar_title="UFO-R11 SmartIR",
                        sidebar_icon="mdi:remote",
                        frontend_url_path=DOMAIN,
                        config={
                            "_panel_custom": {
                                "name": f"panel-custom-{DOMAIN.replace('_', '-')}",
                                "js_url": f"/api/{DOMAIN}/static/ufo-r11-panel.js",
                                "css_url": f"/api/{DOMAIN}/static/ufo-r11-styles.css",
                            },
                        },
                        require_admin=False,
                    )
                panel_registered_successfully = True
                _LOGGER.info("Panel registered using async_register_built_in_panel")
            except Exception as e_builtin:
                _LOGGER.warning("async_register_built_in_panel failed: %s", e_builtin)
        
        # If the older method was not available, was None, or failed, try the newer method
        if not panel_registered_successfully and hasattr(panel_custom, "async_register_panel"):
            _LOGGER.debug("Attempting to register panel using panel_custom.async_register_panel")
            try:
                register_custom = panel_custom.async_register_panel
                if iscoroutinefunction(register_custom):
                    await register_custom(
                        hass,
                        frontend_url_path=DOMAIN,
                        webcomponent_name=f"panel-custom-{DOMAIN.replace('_', '-')}",
                        sidebar_title="UFO-R11 SmartIR",
                        sidebar_icon="mdi:remote",
                        module_url=f"/api/{DOMAIN}/static/ufo-r11-panel.js",
                        embed_iframe=True,
                        require_admin=False,
                    )
                else:
                    register_custom(
                        hass,
                        frontend_url_path=DOMAIN,
                        webcomponent_name=f"panel-custom-{DOMAIN.replace('_', '-')}",
                        sidebar_title="UFO-R11 SmartIR",
                        sidebar_icon="mdi:remote",
                        module_url=f"/api/{DOMAIN}/static/ufo-r11-panel.js",
                        embed_iframe=True,
                        require_admin=False,
                    )
                panel_registered_successfully = True
                _LOGGER.info("Panel registered using panel_custom.async_register_panel")
            except Exception as e_panel:
                _LOGGER.error("panel_custom.async_register_panel failed: %s", e_panel)
        
        if panel_registered_successfully:
            _LOGGER.info("UFO-R11 SmartIR frontend panel registered successfully")
        else:
            # This 'else' is reached if neither method was available (was None) or both failed
            _LOGGER.error(
                "Failed to register frontend panel. Neither async_register_built_in_panel "
                "nor panel_custom.async_register_panel succeeded. "
                "Check Home Assistant version compatibility and frontend component status. "
                "Review previous logs for specific errors from registration attempts."
            )
            raise RuntimeError(
                "Could not register frontend panel using available methods. See logs for details."
            )
        
    except Exception as e:
        _LOGGER.error("Failed to register UFO-R11 SmartIR frontend panel: %s", e)
        raise


async def async_setup_frontend_panel(hass: HomeAssistant) -> None:
    """Set up the UFO-R11 SmartIR frontend panel."""
    # Check if panel setup has already been successfully completed
    if hass.data.get(DOMAIN, {}).get("frontend_panel_registered", False):
        _LOGGER.debug(
            "UFO-R11 SmartIR frontend panel '%s' already marked as registered. Skipping setup.",
            DOMAIN
        )
        return

    try:
        # Register the frontend panel
        await async_register_panel(hass)
        
        # Store panel setup state to indicate successful registration
        hass.data.setdefault(DOMAIN, {})["frontend_panel_registered"] = True
        
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

