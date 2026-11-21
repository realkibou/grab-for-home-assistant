"""The Grab Link Tracking integration."""

from __future__ import annotations

from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import GrabClient, NoShareUrlError, extract_share_url
from .const import (
    ATTR_MESSAGE,
    CONF_SCAN_INTERVAL,
    CONF_SHARE_MESSAGE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_SHARE_MESSAGE,
)
from .coordinator import GrabCoordinator
from .dashboard import async_ensure_dashboard

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_SCHEMA = vol.Schema({vol.Required(ATTR_MESSAGE): cv.string})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Grab Link Tracking integration."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SHARE_MESSAGE,
        _async_set_share_message,
        schema=SERVICE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Grab Link Tracking from a config entry."""
    client = GrabClient(async_get_clientsession(hass))
    coordinator = GrabCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))

    await async_ensure_dashboard(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    hass.data[DOMAIN].pop(entry.entry_id)
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply config entry data/options changes to the running coordinator."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None:
        return

    if entry.data.get(CONF_SHARE_MESSAGE, "") != coordinator.share_message:
        await coordinator.async_apply_entry_message()

    scan_interval = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    if coordinator.update_interval != scan_interval:
        await hass.config_entries.async_reload(entry.entry_id)


async def _async_set_share_message(call: ServiceCall) -> None:
    """Update the tracked Grab share message for the targeted entries."""
    hass = call.hass
    message = call.data[ATTR_MESSAGE].strip()

    try:
        extract_share_url(message)
    except NoShareUrlError as err:
        raise HomeAssistantError(
            "No Grab share link (https://app.grab.com/s/...) found in the message"
        ) from err

    coordinators = list(hass.data.get(DOMAIN, {}).values())

    entry_ids = await service.async_extract_config_entry_ids(call)
    if entry_ids:
        coordinators = [
            coordinator
            for coordinator in coordinators
            if coordinator.entry.entry_id in entry_ids
        ]
        if not coordinators:
            raise HomeAssistantError(
                "No loaded Grab Link Tracking entry matched the target"
            )

    if not coordinators:
        raise HomeAssistantError("Grab Link Tracking is not set up")

    for coordinator in coordinators:
        await coordinator.async_update_share_message(message)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, object]:
    """Return diagnostics for a config entry."""
    coordinator: GrabCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = dict(coordinator.data or {})
    if "share_url" in data:
        data["share_url"] = "**REDACTED**"
    if "booking_id" in data:
        data["booking_id"] = "**REDACTED**"

    return {
        "share_message_configured": bool(entry.data.get(CONF_SHARE_MESSAGE)),
        "options": dict(entry.options),
        "coordinator_data": data,
        "last_update_success": coordinator.last_update_success,
        "last_poll": (
            coordinator.last_poll.isoformat()
            if coordinator.last_poll is not None
            else None
        ),
        "last_error": coordinator.last_error,
    }
