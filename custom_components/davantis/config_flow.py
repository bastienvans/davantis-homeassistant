"""Config flow for the Davantis integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DavantisApiClient, DavantisAuthError, DavantisConnectionError
from .const import DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


class DavantisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Davantis."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: collect connection details and validate."""
        errors: dict[str, str] = {}
        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            client = DavantisApiClient(
                user_input[CONF_HOST],
                user_input[CONF_PORT],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                async_get_clientsession(self.hass),
            )
            try:
                await client.async_login()
                await client.async_get_relays()
            except DavantisAuthError:
                errors["base"] = "invalid_auth"
            except DavantisConnectionError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=f"Davantis ({user_input[CONF_HOST]})", data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
