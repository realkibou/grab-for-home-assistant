"""Constants for the Grab Link Tracking integration."""

from __future__ import annotations

import logging
import re
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "grab_link"
LOGGER: Final = logging.getLogger(__package__)

# Config entry data
CONF_SHARE_MESSAGE: Final = "share_message"

# Config entry options
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_APPROACH_WINDOW: Final = "approach_window"
CONF_CLEAR_AFTER_COMPLETED: Final = "clear_after_completed"
CONF_CLEAR_AFTER_CANCELLED: Final = "clear_after_cancelled"

DEFAULT_SCAN_INTERVAL: Final = 30
DEFAULT_APPROACH_WINDOW: Final = 300
DEFAULT_CLEAR_AFTER_COMPLETED: Final = 0
DEFAULT_CLEAR_AFTER_CANCELLED: Final = 0
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 3600
MIN_APPROACH_WINDOW: Final = 30
MAX_APPROACH_WINDOW: Final = 1800
MIN_CLEAR_DELAY: Final = 0
MAX_CLEAR_DELAY: Final = 86400

# Services
SERVICE_SET_SHARE_MESSAGE: Final = "set_share_message"
SERVICE_CLEAR_SHARE_MESSAGE: Final = "clear_share_message"
ATTR_MESSAGE: Final = "message"

# Grab share links
SHORT_URL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"https://app\.grab\.com/s/[A-Za-z0-9_-]+", re.IGNORECASE
)
SHARE_ORDER_LINK_PARAM: Final = "shareOrderLink"

RESOLVE_TIMEOUT: Final = 15
API_TIMEOUT: Final = 15

API_BOOKING_DETAILS_URL: Final = (
    "https://api.grab.com/api/v1/safety/sharemyride/{booking_id}"
    "/bookingdetails?fullData=false"
)

API_HEADERS: Final[dict[str, str]] = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "origin": "https://sharelocation.grab.com",
    "user-agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
    ),
}

# Dashboard provisioned by the integration
DASHBOARD_URL_PATH: Final = "grab"
DASHBOARD_TITLE: Final = "Grab"
DASHBOARD_ICON: Final = "mdi:moped"

PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.TEXT,
]
