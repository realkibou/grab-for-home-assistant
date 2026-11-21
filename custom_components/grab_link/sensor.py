"""Sensor platform for the Grab Link Tracking integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GrabCoordinator
from .entity import GrabEntity
from .util import parse_timestamp_value


@dataclass(frozen=True, kw_only=True)
class GrabSensorEntityDescription(SensorEntityDescription):
    """Describes a Grab Link sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[GrabSensorEntityDescription, ...] = (
    GrabSensorEntityDescription(
        key="booking",
        translation_key="booking",
        icon="mdi:moped",
        value_fn=lambda data: data.get("booking_state") or "unknown",
    ),
    GrabSensorEntityDescription(
        key="booking_code",
        translation_key="booking_code",
        icon="mdi:barcode",
        value_fn=lambda data: data.get("booking_code"),
    ),
    GrabSensorEntityDescription(
        key="route_eta",
        translation_key="route_eta",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: parse_timestamp_value(data.get("route_eta_unix")),
    ),
    GrabSensorEntityDescription(
        key="driver_arrival",
        translation_key="driver_arrival",
        icon="mdi:clock-in",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: parse_timestamp_value(data.get("driver_arrival_utc")),
    ),
    GrabSensorEntityDescription(
        key="driver_name",
        translation_key="driver_name",
        icon="mdi:account",
        value_fn=lambda data: data.get("driver_name"),
    ),
    GrabSensorEntityDescription(
        key="order_from",
        translation_key="order_from",
        icon="mdi:map-marker",
        value_fn=lambda data: data.get("pickup"),
    ),
    GrabSensorEntityDescription(
        key="order_to",
        translation_key="order_to",
        icon="mdi:map-marker-check",
        value_fn=lambda data: data.get("dropoff"),
    ),
    GrabSensorEntityDescription(
        key="title",
        translation_key="title",
        icon="mdi:information-outline",
        value_fn=lambda data: data.get("title"),
    ),
    GrabSensorEntityDescription(
        key="message",
        translation_key="message",
        icon="mdi:message-text-outline",
        value_fn=lambda data: data.get("message"),
    ),
    GrabSensorEntityDescription(
        key="pending_delivery",
        translation_key="pending_delivery",
        icon="mdi:package-variant-closed",
        value_fn=lambda data: data.get("is_pending_delivery"),
    ),
    GrabSensorEntityDescription(
        key="vehicle_model",
        translation_key="vehicle_model",
        icon="mdi:motorbike",
        value_fn=lambda data: data.get("vehicle_model"),
    ),
    GrabSensorEntityDescription(
        key="vehicle_plate",
        translation_key="vehicle_plate",
        icon="mdi:card-text-outline",
        value_fn=lambda data: data.get("vehicle_plate"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Grab Link sensors from a config entry."""
    coordinator: GrabCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[GrabSensor] = []
    for description in SENSOR_DESCRIPTIONS:
        if description.key == "booking":
            entities.append(GrabBookingSensor(coordinator, entry, description))
        else:
            entities.append(GrabSensor(coordinator, entry, description))

    async_add_entities(entities)


class GrabSensor(GrabEntity, SensorEntity):
    """Representation of a Grab Link sensor."""

    entity_description: GrabSensorEntityDescription

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)


class GrabBookingSensor(GrabSensor):
    """The main booking sensor, exposing every detail as attributes."""

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full set of booking details as attributes."""
        return dict(self.coordinator.data)
