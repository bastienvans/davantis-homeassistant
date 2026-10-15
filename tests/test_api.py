"""Unit tests for the Davantis API client.

These use a small fake aiohttp session rather than a mocking library, so they
stay correct across aiohttp versions and need no Home Assistant runtime.
"""

from __future__ import annotations

from typing import Any

import aiohttp
import pytest

from davantis.api import (  # loaded as a standalone package by conftest.py
    DavantisApiClient,
    DavantisAuthError,
    DavantisConnectionError,
)

BASE = "http://1.2.3.4:21000"
TOKEN_URL = f"{BASE}/oauth/token"
RELAYS_URL = f"{BASE}/relays"


class FakeResp:
    """Minimal stand-in for an aiohttp response used as an async context manager."""

    def __init__(
        self,
        status: int = 200,
        json_data: Any = None,
        *,
        content_length: int | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.status = status
        self._json = json_data
        self.content_length = content_length
        self._exc = exc

    async def __aenter__(self) -> "FakeResp":
        if self._exc is not None:
            raise self._exc
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def json(self, content_type: Any = None) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise aiohttp.ClientResponseError(None, (), status=self.status)


class FakeSession:
    """Routes requests to queued FakeResp objects and records the calls."""

    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], list[FakeResp]] = {}
        self.calls: list[dict[str, Any]] = []

    def queue(self, method: str, url: str, *resps: FakeResp) -> None:
        self.responses.setdefault((method.upper(), url), []).extend(resps)

    def _take(self, method: str, url: str) -> FakeResp:
        queue = self.responses.get((method.upper(), url))
        if not queue:
            raise AssertionError(f"no fake response queued for {method} {url}")
        return queue.pop(0)

    def post(self, url: str, **kwargs: Any) -> FakeResp:
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self._take("POST", url)

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResp:
        self.calls.append({"method": method.upper(), "url": url, **kwargs})
        return self._take(method, url)


def _client(session: FakeSession) -> DavantisApiClient:
    return DavantisApiClient("1.2.3.4", 21000, "admin", "pw", session)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_login_stores_tokens() -> None:
    session = FakeSession()
    session.queue("POST", TOKEN_URL, FakeResp(json_data={"access_token": "A", "refresh_token": "R"}))
    client = _client(session)
    await client.async_login()
    assert client._access_token == "A"
    assert client._refresh_token == "R"
    # Token request must be form-encoded (data=), never a JSON body.
    assert session.calls[0]["data"]["grant_type"] == "password"


@pytest.mark.asyncio
async def test_login_bad_credentials_raises_auth_error() -> None:
    session = FakeSession()
    session.queue("POST", TOKEN_URL, FakeResp(status=400))
    with pytest.raises(DavantisAuthError):
        await _client(session).async_login()


@pytest.mark.asyncio
async def test_login_missing_token_raises_auth_error() -> None:
    session = FakeSession()
    session.queue("POST", TOKEN_URL, FakeResp(json_data={"no": "token"}))
    with pytest.raises(DavantisAuthError):
        await _client(session).async_login()


@pytest.mark.asyncio
async def test_get_relays_returns_list() -> None:
    session = FakeSession()
    session.queue("POST", TOKEN_URL, FakeResp(json_data={"access_token": "A", "refresh_token": "R"}))
    session.queue(
        "GET",
        RELAYS_URL,
        FakeResp(json_data=[
            {"id": 3, "alias": "light", "status": False},
            {"id": 4, "alias": "gate", "status": True},
        ]),
    )
    client = _client(session)
    await client.async_login()
    relays = await client.async_get_relays()
    assert [r["alias"] for r in relays] == ["light", "gate"]


@pytest.mark.asyncio
async def test_set_relay_sends_expected_body() -> None:
    session = FakeSession()
    session.queue("POST", TOKEN_URL, FakeResp(json_data={"access_token": "A", "refresh_token": "R"}))
    session.queue("PATCH", f"{BASE}/relays/3", FakeResp(status=200, content_length=0))
    client = _client(session)
    await client.async_login()
    await client.async_set_relay(3, True)
    patch_call = next(c for c in session.calls if c["method"] == "PATCH")
    assert patch_call["json"] == {"status": "true", "id": "3"}
    assert patch_call["headers"]["Authorization"] == "Bearer A"


@pytest.mark.asyncio
async def test_set_relay_off_sends_false() -> None:
    session = FakeSession()
    session.queue("POST", TOKEN_URL, FakeResp(json_data={"access_token": "A", "refresh_token": "R"}))
    session.queue("PATCH", f"{BASE}/relays/3", FakeResp(status=200, content_length=0))
    client = _client(session)
    await client.async_login()
    await client.async_set_relay(3, False)
    patch_call = next(c for c in session.calls if c["method"] == "PATCH")
    assert patch_call["json"]["status"] == "false"


@pytest.mark.asyncio
async def test_request_refreshes_token_on_401() -> None:
    session = FakeSession()
    session.queue(
        "POST",
        TOKEN_URL,
        FakeResp(json_data={"access_token": "A", "refresh_token": "R"}),
        FakeResp(json_data={"access_token": "B", "refresh_token": "R2"}),
    )
    session.queue(
        "GET",
        RELAYS_URL,
        FakeResp(status=401),
        FakeResp(json_data=[]),
    )
    client = _client(session)
    await client.async_login()
    assert await client.async_get_relays() == []
    assert client._access_token == "B"


@pytest.mark.asyncio
async def test_connection_error_wrapped() -> None:
    session = FakeSession()
    session.queue("POST", TOKEN_URL, FakeResp(exc=aiohttp.ClientConnectionError("boom")))
    with pytest.raises(DavantisConnectionError):
        await _client(session).async_login()
