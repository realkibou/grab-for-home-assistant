"""Client for the Grab share-location API."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
import re
from typing import Any
from urllib.parse import unquote

import aiohttp

from .const import (
    API_BOOKING_DETAILS_URL,
    API_HEADERS,
    API_TIMEOUT,
    LOGGER,
    RESOLVE_TIMEOUT,
    SHARE_ORDER_LINK_PARAM,
    SHORT_URL_PATTERN,
)


class GrabApiError(Exception):
    """Base exception for Grab API errors."""


class NoShareUrlError(GrabApiError):
    """Raised when no Grab share link is present in the message."""


class ResolveError(GrabApiError):
    """Raised when the Grab share link could not be resolved."""


class BookingDetailsError(GrabApiError):
    """Raised when booking details could not be fetched."""


@dataclass(frozen=True, slots=True)
class ResolvedShare:
    """A resolved Grab share link."""

    share_url: str
    booking_id: str


def extract_share_url(message: str) -> str:
    """Extract the first Grab short URL from arbitrary text."""
    if not (match := SHORT_URL_PATTERN.search(message)):
        raise NoShareUrlError("No Grab share link found in the message")
    return match.group(0)


def extract_booking_id(location: str) -> str:
    """Extract the booking id from a redirect location header."""
    match = re.search(rf"[?&]{SHARE_ORDER_LINK_PARAM}=([^&]+)", location)
    if not match:
        raise ResolveError("Share URL redirect did not contain a booking id")
    return unquote(match.group(1))


class GrabClient:
    """Minimal async client for Grab share links."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the client with a shared aiohttp session."""
        self._session = session

    async def resolve_share_message(self, message: str) -> ResolvedShare:
        """Resolve a share message into a share URL and booking id."""
        share_url = extract_share_url(message)

        try:
            async with self._session.get(
                share_url,
                headers=API_HEADERS,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=RESOLVE_TIMEOUT),
            ) as response:
                location = response.headers.get("Location")
        except (TimeoutError, aiohttp.ClientError) as err:
            raise ResolveError(f"Request to {share_url} failed") from err

        if not location:
            raise ResolveError("Share URL did not return a redirect")

        booking_id = extract_booking_id(location)
        LOGGER.debug("Resolved %s to booking id %s", share_url, booking_id)
        return ResolvedShare(share_url=share_url, booking_id=booking_id)

    async def get_booking_details(self, booking_id: str) -> dict[str, Any]:
        """Fetch booking details for a booking id."""
        url = API_BOOKING_DETAILS_URL.format(booking_id=booking_id)
        try:
            async with self._session.get(
                url,
                headers=API_HEADERS,
                timeout=aiohttp.ClientTimeout(total=API_TIMEOUT),
            ) as response:
                if response.status != HTTPStatus.OK:
                    raise BookingDetailsError(
                        f"Grab API returned HTTP {response.status}"
                    )
                data = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError) as err:
            raise BookingDetailsError("Request to the Grab API failed") from err

        if not isinstance(data, dict):
            raise BookingDetailsError("Grab API returned unexpected data")

        return data
