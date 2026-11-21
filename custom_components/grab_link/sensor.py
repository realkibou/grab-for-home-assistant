"""Sensor platform for the Grab Link Tracking integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import GrabCoordinator
from .entity import GrabEntity
from .util import parse_timestamp_value


@dataclass(frozen=True, kw_only=True)
class GrabSensorEntityDescription(SensorEntityDescription):
    """Describes a Grab Link sensor."""

    value_fn: Callable[[GrabCoordinator], Any]
    always_available: bool = False


BOOKING_STATE_ICONS: dict[str, str] = {
    "ORDER_EXECUTING": "mdi:moped",
    "ORDER_IN_PREPARE": "mdi:chef-hat",
    "CANCELLED_MAX": "mdi:cancel",
    "COMPLETED": "mdi:check-circle",
    "FAILED": "mdi:bug",
}


def _data(coordinator: GrabCoordinator) -> dict[str, Any]:
    """Return the coordinator data or an empty dict."""
    return coordinator.data or {}


def _eta_difference(coordinator: GrabCoordinator) -> int | None:
    """Return the number of seconds between the route ETA and now."""
    eta = _data(coordinator).get("route_eta_unix")
    if eta is None:
        return None
    try:
        return int(float(eta) - dt_util.utcnow().timestamp())
    except (TypeError, ValueError):
        return None


def _debug_status(coordinator: GrabCoordinator) -> str:
    """Return a short description of the polling pipeline state."""
    if not coordinator.share_message:
        return "no_share_link"
    if coordinator.last_error:
        return "error"
    if coordinator.last_update_success:
        return "ok"
    return "unknown"


SENSOR_DESCRIPTIONS: tuple[GrabSensorEntityDescription, ...] = (
    GrabSensorEntityDescription(
        key="booking",
        translation_key="booking",
        icon="mdi:moped",
        value_fn=lambda coordinator: _data(coordinator).get("booking_state")
        or "unknown",
    ),
    GrabSensorEntityDescription(
        key="booking_code",
        translation_key="booking_code",
        icon="mdi:barcode",
        value_fn=lambda coordinator: _data(coordinator).get("booking_code"),
    ),
    GrabSensorEntityDescription(
        key="route_eta",
        translation_key="route_eta",
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: parse_timestamp_value(
            _data(coordinator).get("route_eta_unix")
        ),
    ),
    GrabSensorEntityDescription(
        key="driver_arrival",
        translation_key="driver_arrival",
        icon="mdi:clock-in",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: parse_timestamp_value(
            _data(coordinator).get("driver_arrival_utc")
        ),
    ),
    GrabSensorEntityDescription(
        key="driver_name",
        translation_key="driver_name",
        icon="mdi:account",
        value_fn=lambda coordinator: _data(coordinator).get("driver_name"),
    ),
    GrabSensorEntityDescription(
        key="order_from",
        translation_key="order_from",
        icon="mdi:map-marker",
        value_fn=lambda coordinator: _data(coordinator).get("pickup"),
    ),
    GrabSensorEntityDescription(
        key="order_to",
        translation_key="order_to",
        icon="mdi:map-marker-check",
        value_fn=lambda coordinator: _data(coordinator).get("dropoff"),
    ),
    GrabSensorEntityDescription(
        key="title",
        translation_key="title",
        icon="mdi:information-outline",
        value_fn=lambda coordinator: _data(coordinator).get("title"),
    ),
    GrabSensorEntityDescription(
        key="message",
        translation_key="message",
        icon="mdi:message-text-outline",
        value_fn=lambda coordinator: _data(coordinator).get("message"),
    ),
    GrabSensorEntityDescription(
        key="pending_delivery",
        translation_key="pending_delivery",
        icon="mdi:package-variant-closed",
        value_fn=lambda coordinator: _data(coordinator).get("is_pending_delivery"),
    ),
    GrabSensorEntityDescription(
        key="vehicle_model",
        translation_key="vehicle_model",
        icon="mdi:motorbike",
        value_fn=lambda coordinator: _data(coordinator).get("vehicle_model"),
    ),
    GrabSensorEntityDescription(
        key="vehicle_plate",
        translation_key="vehicle_plate",
        icon="mdi:card-text-outline",
        value_fn=lambda coordinator: _data(coordinator).get("vehicle_plate"),
    ),
    # --- Debug / diagnostic sensors -------------------------------------
    GrabSensorEntityDescription(
        key="last_poll",
        translation_key="last_poll",
        icon="mdi:clock-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda coordinator: coordinator.last_poll,
        always_available=True,
    ),
    GrabSensorEntityDescription(
        key="debug",
        translation_key="debug",
        icon="mdi:bug-check-outline",
        value_fn=_debug_status,
        always_available=True,
    ),
    GrabSensorEntityDescription(
        key="debug_route_eta",
        translation_key="debug_route_eta",
        icon="mdi:calendar-clock",
        value_fn=lambda coordinator: _data(coordinator).get("route_eta_unix"),
        always_available=True,
    ),
    GrabSensorEntityDescription(
        key="debug_now_timestamp",
        translation_key="debug_now_timestamp",
        icon="mdi:timer-outline",
        value_fn=lambda coordinator: int(dt_util.utcnow().timestamp()),
        always_available=True,
    ),
    GrabSensorEntityDescription(
        key="eta_difference",
        translation_key="eta_difference",
        icon="mdi:timer-sand",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement="s",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_eta_difference,
        always_available=True,
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
        elif description.key == "debug":
            entities.append(GrabDebugSensor(coordinator, entry, description))
        else:
            entities.append(GrabSensor(coordinator, entry, description))

    async_add_entities(entities)


class GrabSensor(GrabEntity, SensorEntity):
    """Representation of a Grab Link sensor."""

    entity_description: GrabSensorEntityDescription

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        if self.entity_description.always_available:
            return True
        return super().available

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator)


class GrabBookingSensor(GrabSensor):
    """The main booking sensor, exposing every detail as attributes."""

    @property
    def icon(self) -> str:
        """Return an icon matching the current order state."""
        state = str(_data(self.coordinator).get("booking_state") or "").upper()

        if state in BOOKING_STATE_ICONS:
            return BOOKING_STATE_ICONS[state]
        if "CANCEL" in state:
            return "mdi:cancel"
        if "FAIL" in state:
            return "mdi:bug"
        if "COMPLET" in state or "FINISH" in state or "DELIVER" in state:
            return "mdi:check-circle"
        if "PREPAR" in state:
            return "mdi:chef-hat"
        return "mdi:moped"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the full set of booking details as attributes."""
        return dict(_data(self.coordinator))


class GrabDebugSensor(GrabSensor):
    """Diagnostic sensor describing the state of the polling pipeline."""

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return debugging details about the last poll."""
        interval = self.coordinator.update_interval
        return {
            "booking_id": self.coordinator.booking_id,
            "share_url": self.coordinator.share_url,
            "last_poll": (
                self.coordinator.last_poll.isoformat()
                if self.coordinator.last_poll is not None
                else None
            ),
            "last_error": self.coordinator.last_error,
            "last_update_success": self.coordinator.last_update_success,
            "scan_interval": (
                int(interval.total_seconds())
                if interval is not None
                else self.coordinator.entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
        }
