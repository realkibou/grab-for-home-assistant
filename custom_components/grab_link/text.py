"""Text platform for the Grab Link Tracking integration."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextEntityDescription, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import NoShareUrlError, extract_share_url
from .const import DOMAIN
from .coordinator import GrabCoordinator
from .entity import GrabEntity

SHARE_MESSAGE_DESCRIPTION = TextEntityDescription(
    key="share_message",
    translation_key="share_message",
    icon="mdi:link-variant",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Grab Link text entity from a config entry."""
    coordinator: GrabCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [GrabShareMessageText(coordinator, entry, SHARE_MESSAGE_DESCRIPTION)]
    )


class GrabShareMessageText(GrabEntity, TextEntity):
    """Text entity that holds the Grab share message or link."""

    entity_description: TextEntityDescription
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = 2048

    @property
    def available(self) -> bool:
        """Always stay available so a broken link can be corrected."""
        return True

    @property
    def native_value(self) -> str | None:
        """Return the currently tracked share message."""
        return self.coordinator.share_message or None

    async def async_set_value(self, value: str) -> None:
        """Store a new Grab share message and start tracking it."""
        message = value.strip()

        if message:
            try:
                extract_share_url(message)
            except NoShareUrlError as err:
                raise HomeAssistantError(
                    "No Grab share link (https://app.grab.com/s/...) found in the message"
                ) from err

        await self.coordinator.async_update_share_message(message)
