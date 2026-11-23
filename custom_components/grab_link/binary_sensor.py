"""Binary sensor platform for the Grab Link Tracking integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_APPROACH_WINDOW,
    DEFAULT_APPROACH_WINDOW,
    DOMAIN,
)
from .coordinator import GrabCoordinator
from .entity import GrabEntity


@dataclass(frozen=True, kw_only=True)
class GrabBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Grab Link binary sensor."""

    is_on_fn: Callable[[dict[str, Any], int], bool | None]


def _driver_approaching(data: dict[str, Any], window: int) -> bool | None:
    """Return whether the driver is due to arrive within the window."""
    eta = data.get("route_eta_unix")
    if not eta:
        return None
    seconds = eta - dt_util.utcnow().timestamp()
    if seconds <= 0:
        return False
    return seconds <= window


BINARY_SENSOR_DESCRIPTIONS: tuple[GrabBinarySensorEntityDescription, ...] = (
    GrabBinarySensorEntityDescription(
        key="driver_approaching",
        translation_key="driver_approaching",
        device_class=BinarySensorDeviceClass.PRESENCE,
        icon="mdi:moped-outline",
        is_on_fn=_driver_approaching,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grab Link binary sensors from a config entry."""
    coordinator: GrabCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        GrabBinarySensor(coordinator, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class GrabBinarySensor(GrabEntity, BinarySensorEntity):
    """Representation of a Grab Link binary sensor."""

    entity_description: GrabBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the current binary sensor state."""
        window = self.coordinator.entry.options.get(
            CONF_APPROACH_WINDOW, DEFAULT_APPROACH_WINDOW
        )
        return self.entity_description.is_on_fn(self.coordinator.data, window)
