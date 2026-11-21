"""Provision the Grab dashboard in the Home Assistant sidebar."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import DASHBOARD_ICON, DASHBOARD_TITLE, DASHBOARD_URL_PATH, LOGGER

DASHBOARD_CONFIG: dict[str, Any] = {
    "title": DASHBOARD_TITLE,
    "views": [
        {
            "title": DASHBOARD_TITLE,
            "icon": DASHBOARD_ICON,
            "type": "sections",
            "sections": [
                {
                    "type": "grid",
                    "cards": [
                        {
                            "type": "entities",
                            "title": "Grab Link",
                            "entities": [
                                {
                                    "entity": "text.grab_link_share_message",
                                    "name": "Share Message",
                                },
                                {
                                    "entity": "sensor.grab_link_booking",
                                    "name": "Booking State",
                                },
                                {
                                    "entity": "sensor.grab_link_driver_name",
                                    "name": "Driver",
                                },
                                {
                                    "entity": "sensor.grab_link_order_from",
                                    "name": "Order From",
                                },
                                {
                                    "entity": "sensor.grab_link_order_to",
                                    "name": "Order To",
                                },
                                {
                                    "entity": "sensor.grab_link_route_eta",
                                    "name": "Route ETA",
                                },
                                {
                                    "entity": "sensor.grab_link_driver_arrival",
                                    "name": "Driver Arrival",
                                },
                                {
                                    "entity": "sensor.grab_link_message",
                                    "name": "Message",
                                },
                                {
                                    "entity": "sensor.grab_link_title",
                                    "name": "Title",
                                },
                            ],
                        },
                        {
                            "type": "entities",
                            "title": "Driver & Vehicle",
                            "entities": [
                                "sensor.grab_link_vehicle_model",
                                "sensor.grab_link_vehicle_plate",
                                "sensor.grab_link_booking_code",
                                "binary_sensor.grab_link_driver_approaching",
                            ],
                        },
                        {
                            "type": "entities",
                            "title": "Delivery",
                            "entities": [
                                "sensor.grab_link_pending_delivery",
                            ],
                        },
                    ],
                },
            ],
        },
    ],
}


async def async_ensure_dashboard(hass: HomeAssistant) -> None:
    """Create the Grab dashboard and sidebar panel if it does not exist yet."""
    try:
        from homeassistant.components import frontend
        from homeassistant.components.lovelace import dashboard as lovelace_dashboard
        from homeassistant.components.lovelace.const import (
            CONF_ALLOW_SINGLE_WORD,
            CONF_REQUIRE_ADMIN,
            CONF_SHOW_IN_SIDEBAR,
            CONF_TITLE,
            CONF_URL_PATH,
            LOVELACE_DATA,
            MODE_STORAGE,
        )
        from homeassistant.const import CONF_ICON
    except ImportError:  # pragma: no cover - lovelace is a core component
        LOGGER.warning("Lovelace is not available, skipping Grab dashboard")
        return

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        LOGGER.warning("Lovelace is not set up, skipping Grab dashboard")
        return

    if DASHBOARD_URL_PATH in lovelace_data.dashboards:
        return

    created = False
    item: dict[str, Any] | None = None

    try:
        collection = lovelace_dashboard.DashboardsCollection(hass)
        await collection.async_load()
        item = next(
            (
                dashboard_item
                for dashboard_item in collection.async_items()
                if dashboard_item.get(CONF_URL_PATH) == DASHBOARD_URL_PATH
            ),
            None,
        )
        if item is None:
            item = await collection.async_create_item(
                {
                    CONF_ALLOW_SINGLE_WORD: True,
                    CONF_ICON: DASHBOARD_ICON,
                    CONF_TITLE: DASHBOARD_TITLE,
                    CONF_URL_PATH: DASHBOARD_URL_PATH,
                    CONF_REQUIRE_ADMIN: False,
                    CONF_SHOW_IN_SIDEBAR: True,
                }
            )
            created = True
            await collection.store.async_save(
                {**collection._data_to_save()}
            )
    except Exception:
        LOGGER.exception("Could not create the Grab dashboard entry")
        return

    dashboard = lovelace_dashboard.LovelaceStorage(hass, item)
    lovelace_data.dashboards[DASHBOARD_URL_PATH] = dashboard

    if not frontend.async_panel_exists(hass, DASHBOARD_URL_PATH):
        frontend.async_register_built_in_panel(
            hass,
            "lovelace",
            frontend_url_path=DASHBOARD_URL_PATH,
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon=DASHBOARD_ICON,
            config={"mode": MODE_STORAGE},
            require_admin=False,
            show_in_sidebar=True,
        )

    if created:
        try:
            await dashboard.async_save(DASHBOARD_CONFIG)
        except Exception:
            LOGGER.exception("Could not save the Grab dashboard config")
