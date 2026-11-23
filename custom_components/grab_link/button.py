"""Button platform for the Grab Link Tracking integration."""

from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import GrabCoordinator
from .entity import GrabEntity
from .text import SHARE_MESSAGE_DESCRIPTION

CONFIRM_SHARE_MESSAGE_DESCRIPTION = ButtonEntityDescription(
    key="confirm_share_message",
    translation_key="confirm_share_message",
    icon="mdi:check-bold",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Grab Link buttons from a config entry."""
    coordinator: GrabCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            GrabConfirmShareMessageButton(
                coordinator, entry, CONFIRM_SHARE_MESSAGE_DESCRIPTION
            )
        ]
    )


class GrabConfirmShareMessageButton(GrabEntity, ButtonEntity):
    """Apply the value entered in the share-message text field.

    Home Assistant commits a text entity only when the field loses focus or
    Enter is pressed. Clicking this button blurs the field and then applies the
    committed value, so pasting a link and clicking Confirm is enough.
    """

    entity_description: ButtonEntityDescription

    @property
    def available(self) -> bool:
        """Always stay available so a broken link can be replaced."""
        return True

    async def async_press(self) -> None:
        """Apply the current share-message text entity value."""
        # The click first blurs the text field; wait for that service call.
        await asyncio.sleep(0.3)

        entity_id = er.async_get(self.hass).async_get_entity_id(
            "text",
            DOMAIN,
            f"{self.coordinator.entry.entry_id}_{SHARE_MESSAGE_DESCRIPTION.key}",
        )

        value = ""
        if entity_id is not None:
            state = self.hass.states.get(entity_id)
            if state is not None and state.state not in ("unknown", "unavailable"):
                value = state.state

        await self.coordinator.async_update_share_message(value)
