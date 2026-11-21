"""Config flow for the Grab Link Tracking integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    BookingDetailsError,
    GrabApiError,
    GrabClient,
    NoShareUrlError,
    ResolveError,
)
from .const import (
    CONF_APPROACH_WINDOW,
    CONF_SCAN_INTERVAL,
    CONF_SHARE_MESSAGE,
    DEFAULT_APPROACH_WINDOW,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_APPROACH_WINDOW,
    MAX_SCAN_INTERVAL,
    MIN_APPROACH_WINDOW,
    MIN_SCAN_INTERVAL,
)


async def validate_share_message(hass: HomeAssistant, message: str) -> str:
    """Validate a share message and return the booking id.

    Raises a GrabApiError subclass when the message cannot be tracked.
    """
    client = GrabClient(async_get_clientsession(hass))
    resolved = await client.resolve_share_message(message)
    await client.get_booking_details(resolved.booking_id)
    return resolved.booking_id


class GrabConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Grab Link config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: paste a Grab share message or link."""
        errors: dict[str, str] = {}

        if user_input is not None:
            message = user_input[CONF_SHARE_MESSAGE].strip()
            try:
                booking_id = await validate_share_message(self.hass, message)
            except NoShareUrlError:
                errors["base"] = "no_share_url"
            except ResolveError:
                errors["base"] = "cannot_resolve"
            except BookingDetailsError:
                errors["base"] = "booking_details_failed"
            except GrabApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(booking_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Grab Link",
                    data={CONF_SHARE_MESSAGE: message},
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SHARE_MESSAGE): TextSelector(
                    TextSelectorConfig(
                        multiline=True,
                        type=TextSelectorType.TEXT,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


class GrabOptionsFlow(config_entries.OptionsFlow):
    """Handle the Grab Link options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the polling options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options

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
