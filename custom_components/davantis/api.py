"""Async client for a local Davantis appliance.

Reverse-engineered from the official Android app (com.cirici.davantis 2.6.33).
In the app's "local mode" the CustomInterceptor rewrites the cloud API URLs to
talk straight to the on-site appliance:

    POST   {base}/oauth/token            password / refresh_token grant
    GET    {base}/relays                 list relay outputs
    PATCH  {base}/relays/{id}            set a relay output

The token endpoint accepts form-encoded parameters; the relay PATCH takes a
JSON body of {"status": "true"|"false", "id": "<id>"}.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import CLIENT_ID, CLIENT_SECRET

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)


class DavantisError(Exception):
    """Base error for the Davantis client."""


class DavantisAuthError(DavantisError):
    """Raised when login or token refresh is rejected by the appliance."""


class DavantisConnectionError(DavantisError):
    """Raised when the appliance cannot be reached."""


class DavantisApiClient:
    """Minimal async client for a Davantis appliance in local mode."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        *,
        use_ssl: bool = False,
    ) -> None:
        """Initialise the client."""
        scheme = "https" if use_ssl else "http"
        self._base = f"{scheme}://{host}:{port}"
        self._username = username
        self._password = password
        self._session = session
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    async def async_login(self) -> None:
        """Obtain a fresh token pair with the password grant."""
        await self._token_request(
            {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
            }
        )

    async def async_refresh(self) -> None:
        """Refresh the access token, falling back to a full login."""
        if not self._refresh_token:
            await self.async_login()
            return
        try:
            await self._token_request(
                {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                }
            )
        except DavantisAuthError:
            # Refresh token expired/invalid: fall back to a full login.
            await self.async_login()

    async def _token_request(self, data: dict[str, str]) -> None:
        """POST to the token endpoint (form-encoded) and store the tokens."""
        try:
            async with self._session.post(
                f"{self._base}/oauth/token", data=data, timeout=REQUEST_TIMEOUT
            ) as resp:
                if resp.status in (400, 401, 403):
                    raise DavantisAuthError(
                        f"Authentication failed (HTTP {resp.status})"
                    )
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise DavantisConnectionError(str(err)) from err

        token = payload.get("access_token")
        if not token:
            raise DavantisAuthError("No access_token in token response")
        self._access_token = token
        self._refresh_token = payload.get("refresh_token") or self._refresh_token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        _retry: bool = True,
    ) -> Any:
        """Perform an authenticated request, refreshing once on a 401."""
        if self._access_token is None:
            await self.async_login()
        headers = {"Authorization": f"Bearer {self._access_token}"}
        try:
            async with self._session.request(
                method,
                f"{self._base}{path}",
                json=json,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status == 401 and _retry:
                    await self.async_refresh()
                    return await self._request(method, path, json=json, _retry=False)
                if resp.status == 401:
                    raise DavantisAuthError("Unauthorized after token refresh")
                resp.raise_for_status()
                if resp.content_length == 0:
                    return None
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise DavantisConnectionError(str(err)) from err

    async def async_get_relays(self) -> list[dict[str, Any]]:
        """Return the list of relay outputs."""
        data = await self._request("GET", "/relays")
        return data or []

    async def async_set_relay(self, relay_id: Any, turn_on: bool) -> None:
        """Set a relay output on or off."""
        body = {"status": "true" if turn_on else "false", "id": str(relay_id)}
        await self._request("PATCH", f"/relays/{relay_id}", json=body)
