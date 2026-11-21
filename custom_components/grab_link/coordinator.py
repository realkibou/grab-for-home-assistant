"""Data update coordinator for the Grab Link Tracking integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    BookingDetailsError,
    GrabApiError,
    GrabClient,
    NoShareUrlError,
    ResolveError,
)
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SHARE_MESSAGE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)


def normalize_booking_details(raw: dict[str, Any]) -> dict[str, Any]:
    """Map the Grab API payload into flat sensor values and attributes."""
    booking = raw.get("booking") or {}
    driver = raw.get("driver") or {}
    route = raw.get("route") or {}
    message_status = raw.get("messageStatus") or {}
    process_message = message_status.get("processMsg") or {}
    additional = raw.get("additionalOrderDetail") or {}
    pickup = booking.get("pickup") or {}
    dropoff = booking.get("dropOff") or {}

    return {
        "booking_code": booking.get("bookingCode"),
        "booking_state": booking.get("bookingState"),
        "driver_arrival_utc": booking.get("driverArrivalTime"),
        "route_eta_unix": route.get("ETA"),
        "title": message_status.get("title"),
        "message": process_message.get("message"),
        "is_pending_delivery": additional.get("isPendingDelivery"),
        "driver_name": driver.get("name"),
        "vehicle_model": driver.get("vehicleModel"),
        "vehicle_plate": driver.get("vehiclePlateNumber"),
        "pickup": pickup.get("keywords"),
        "dropoff": dropoff.get("keywords"),
    }


class GrabCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch Grab booking details on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: GrabClient,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.client = client
        self.share_message: str = entry.data[CONF_SHARE_MESSAGE]
        self.booking_id: str | None = None
        self.share_url: str | None = None

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest booking details."""
        try:
            if self.booking_id is None:
                resolved = await self.client.resolve_share_message(self.share_message)
                self.booking_id = resolved.booking_id
                self.share_url = resolved.share_url
            raw = await self.client.get_booking_details(self.booking_id)
        except NoShareUrlError as err:
            raise UpdateFailed("No Grab share link found in the message") from err
        except ResolveError as err:
            raise UpdateFailed(f"Could not resolve the share link: {err}") from err
        except BookingDetailsError as err:
            raise UpdateFailed(f"Grab API error: {err}") from err
        except GrabApiError as err:
            raise UpdateFailed(str(err)) from err

        data = normalize_booking_details(raw)
        data["share_url"] = self.share_url
        data["booking_id"] = self.booking_id
        return data
