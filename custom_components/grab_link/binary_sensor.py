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


def _order_cancelled(data: dict[str, Any], window: int) -> bool:
    """Return whether the order has been cancelled (False when unknown)."""
    state = data.get("booking_state")
    if not state:
        return False
    return "CANCEL" in str(state).upper()


BINARY_SENSOR_DESCRIPTIONS: tuple[GrabBinarySensorEntityDescription, ...] = (
    GrabBinarySensorEntityDescription(
        key="driver_approaching",
        translation_key="driver_approaching",
        device_class=BinarySensorDeviceClass.PRESENCE,
        icon="mdi:moped-outline",
        is_on_fn=_driver_approaching,
    ),
    GrabBinarySensorEntityDescription(
        key="order_cancelled",
        translation_key="order_cancelled",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:cancel",
        is_on_fn=_order_cancelled,
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
