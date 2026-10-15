"""DataUpdateCoordinator for the Davantis integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DavantisApiClient, DavantisAuthError, DavantisConnectionError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class DavantisCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls the appliance for relay state, keyed by relay id (as str)."""

    def __init__(
        self, hass: HomeAssistant, client: DavantisApiClient, scan_interval: int
    ) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch the current relays and index them by id."""
        try:
            relays = await self.client.async_get_relays()
        except DavantisAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except DavantisConnectionError as err:
            raise UpdateFailed(str(err)) from err
        return {str(relay["id"]): relay for relay in relays if "id" in relay}
