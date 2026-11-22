"""Data update coordinator for the Grab Link Tracking integration."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    BookingDetailsError,
    GrabApiError,
    GrabClient,
    NoShareUrlError,
    ResolveError,
)
from .const import (
    CONF_CLEAR_AFTER_CANCELLED,
    CONF_CLEAR_AFTER_COMPLETED,
    CONF_SCAN_INTERVAL,
    CONF_SHARE_MESSAGE,
    DEFAULT_CLEAR_AFTER_CANCELLED,
    DEFAULT_CLEAR_AFTER_COMPLETED,
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
        self.share_message: str = entry.data.get(CONF_SHARE_MESSAGE, "")
        self.booking_id: str | None = None
        self.share_url: str | None = None
        self.last_poll: datetime | None = None
        self.last_error: str | None = None
        self.clear_after_completed: int = entry.options.get(
            CONF_CLEAR_AFTER_COMPLETED, DEFAULT_CLEAR_AFTER_COMPLETED
        )
        self.clear_after_cancelled: int = entry.options.get(
            CONF_CLEAR_AFTER_CANCELLED, DEFAULT_CLEAR_AFTER_CANCELLED
        )
        self.clear_scheduled_for: datetime | None = None
        self._clear_unsub: CALLBACK_TYPE | None = None
        self._clear_kind: str | None = None

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def async_update_share_message(self, message: str) -> None:
        """Set a new share message, persist it and refresh immediately."""
        message = message.strip()

        if (
            message == self.share_message
            and self.entry.data.get(CONF_SHARE_MESSAGE, "") == message
        ):
            await self.async_request_refresh()
            return

        self._apply_share_message(message)
        self.hass.config_entries.async_update_entry(
            self.entry,
            data={**self.entry.data, CONF_SHARE_MESSAGE: message},
        )
        await self.async_request_refresh()

    async def async_apply_entry_message(self) -> None:
        """Re-read the share message from the config entry and refresh."""
        message = self.entry.data.get(CONF_SHARE_MESSAGE, "")
        if message == self.share_message:
            return
        self._apply_share_message(message)
        await self.async_request_refresh()

    def _apply_share_message(self, message: str) -> None:
        """Apply a message and forget the resolved booking."""
        self._cancel_auto_clear()
        self.share_message = message
        self.booking_id = None
        self.share_url = None
        self.last_poll = None
        self.last_error = None

    def cancel_auto_clear(self) -> None:
        """Cancel a pending automatic share-link clear."""
        self._cancel_auto_clear()

    def _cancel_auto_clear(self) -> None:
        """Cancel a pending automatic share-link clear."""
        if self._clear_unsub is not None:
            self._clear_unsub()
            self._clear_unsub = None
        self._clear_kind = None
        self.clear_scheduled_for = None

    def _schedule_auto_clear(self, booking_state: Any) -> None:
        """Schedule clearing the share link after a terminal order state."""
        state = str(booking_state or "").upper()

        if "COMPLETED" in state:
            kind = "completed"
            delay = self.clear_after_completed
        elif "CANCEL" in state:
            kind = "cancelled"
            delay = self.clear_after_cancelled
        else:
            self._cancel_auto_clear()
            return

        if delay <= 0:
            self._cancel_auto_clear()
            return

        # Keep a running timer for the same terminal state so the countdown
        # starts when the state was first observed.
        if self._clear_kind == kind and self._clear_unsub is not None:
            return

        self._cancel_auto_clear()
        self._clear_kind = kind
        self.clear_scheduled_for = dt_util.utcnow() + timedelta(seconds=delay)
        self._clear_unsub = async_call_later(
            self.hass, delay, self._async_auto_clear
        )
        LOGGER.debug(
            "Scheduled clearing the Grab share link in %s s after %s",
            delay,
            kind,
        )

    async def _async_auto_clear(self, _now: datetime) -> None:
        """Clear the share link after the configured delay."""
        self._clear_unsub = None
        self._clear_kind = None
        self.clear_scheduled_for = None
        LOGGER.info("Clearing the Grab share link after the order finished")
        await self.async_update_share_message("")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest booking details."""
        if not self.share_message:
            self._cancel_auto_clear()
            self.last_error = None
            return {}

        try:
            if self.booking_id is None:
                resolved = await self.client.resolve_share_message(self.share_message)
                self.booking_id = resolved.booking_id
                self.share_url = resolved.share_url
            raw = await self.client.get_booking_details(self.booking_id)
        except NoShareUrlError as err:
            self.last_error = "No Grab share link found in the message"
            raise UpdateFailed(self.last_error) from err
        except ResolveError as err:
            self.last_error = f"Could not resolve the share link: {err}"
            raise UpdateFailed(self.last_error) from err
        except BookingDetailsError as err:
            self.last_error = f"Grab API error: {err}"
            raise UpdateFailed(self.last_error) from err
        except GrabApiError as err:
            self.last_error = str(err)
            raise UpdateFailed(self.last_error) from err
        except Exception as err:  # noqa: BLE001 - record and let HA log it
            self.last_error = f"Unexpected error: {err}"
            raise

        data = normalize_booking_details(raw)
        data["share_url"] = self.share_url
        data["booking_id"] = self.booking_id
        self.last_poll = dt_util.utcnow()
        self.last_error = None
        self._schedule_auto_clear(data.get("booking_state"))
        return data
