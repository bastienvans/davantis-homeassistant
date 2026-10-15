"""The Davantis integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DavantisApiClient, DavantisAuthError, DavantisConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .coordinator import DavantisCoordinator

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Davantis from a config entry."""
    client = DavantisApiClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
        async_get_clientsession(hass),
    )
    try:
        await client.async_login()
    except DavantisAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except DavantisConnectionError as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = DavantisCoordinator(
        hass, client, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded
