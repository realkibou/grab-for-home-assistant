"""Config flow for the Grab Link Tracking integration.

No credentials or links are requested at setup time: the integration adds
itself and provisions the "Grab" dashboard, where the share link is entered.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_APPROACH_WINDOW,
    CONF_SCAN_INTERVAL,
    DEFAULT_APPROACH_WINDOW,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_APPROACH_WINDOW,
    MAX_SCAN_INTERVAL,
    MIN_APPROACH_WINDOW,
    MIN_SCAN_INTERVAL,
)


class GrabConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Grab Link config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add the integration without asking for anything.

        The Grab share link is entered on the auto-created dashboard (or via
        the grab_link.set_share_message service) after setup.
        """
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Grab Link", data={})

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> GrabOptionsFlow:
        """Return the options flow so Configure stays available."""
        return GrabOptionsFlow()


class GrabOptionsFlow(config_entries.OptionsFlow):
    """Handle the Grab Link options flow."""

    @property
    def _entry(self) -> config_entries.ConfigEntry:
        """Return the config entry linked to this options flow.

        Home Assistant 2024.11 only exposes the entry id via ``handler``,
        newer versions provide ``config_entry`` directly.
        """
        entry = getattr(self, "config_entry", None)
        if entry is not None:
            return entry
        entry = self.hass.config_entries.async_get_entry(self.handler)
        if entry is None:  # pragma: no cover - the flow manager validates this
            raise config_entries.UnknownEntry(self.handler)
        return entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the polling options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Required(
                        CONF_APPROACH_WINDOW,
                        default=options.get(
                            CONF_APPROACH_WINDOW, DEFAULT_APPROACH_WINDOW
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_APPROACH_WINDOW,
                            max=MAX_APPROACH_WINDOW,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                }
            ),
        )
