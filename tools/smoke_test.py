#!/usr/bin/env python3
"""Standalone smoke test against a real Davantis appliance on your LAN.

This does NOT import Home Assistant; it just exercises the same three endpoints
the integration uses, so you can confirm connectivity and credentials before
(or instead of) setting the integration up in HA.

Examples:
    python tools/smoke_test.py --host 192.168.1.50 --port 21000 --username admin
    python tools/smoke_test.py --host 192.168.1.50 --username admin --relay 3 --on
    python tools/smoke_test.py --host 192.168.1.50 --username admin --relay 3 --off

The password is read from the DAVANTIS_PASSWORD environment variable, or
prompted for interactively (never echoed). Nothing is written to disk.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys

import aiohttp

# Same OAuth client identity the official app ships with (public, per-build).
CLIENT_ID = "1_3njtj8n8iji8cg8ck4kwsoco0wscswwwsgwwgwkgoo44c4044s"
CLIENT_SECRET = "cpagow9b548o8g8ck0o0cs0ooscwccko44so8wwcws8s0swow"


async def run(args: argparse.Namespace, password: str) -> int:
    base = f"http://{args.host}:{args.port}"
    async with aiohttp.ClientSession() as session:
        # 1) Login (form-encoded password grant).
        async with session.post(
            f"{base}/oauth/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": args.username,
                "password": password,
            },
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                print(f"LOGIN FAILED: HTTP {resp.status}: {await resp.text()}")
                return 1
            token = (await resp.json(content_type=None))["access_token"]
        print("login OK")
        headers = {"Authorization": f"Bearer {token}"}

        # 2) List relays.
        async with session.get(f"{base}/relays", headers=headers) as resp:
            resp.raise_for_status()
            relays = await resp.json(content_type=None)
        print(f"relays ({len(relays)}):")
        for r in relays:
            print(f"  id={r.get('id')}  alias={r.get('alias')!r}  status={r.get('status')}")

        # 3) Optionally toggle one.
        if args.relay is not None and (args.on or args.off):
            state = "true" if args.on else "false"
            async with session.patch(
                f"{base}/relays/{args.relay}",
                json={"status": state, "id": str(args.relay)},
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                print(f"relay {args.relay} set status={state} (HTTP {resp.status})")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", required=True)
    p.add_argument("--port", type=int, default=21000)
    p.add_argument("--username", required=True)
    p.add_argument("--relay", help="relay id to toggle")
    p.add_argument("--on", action="store_true", help="turn the relay on")
    p.add_argument("--off", action="store_true", help="turn the relay off")
    args = p.parse_args()

    password = os.environ.get("DAVANTIS_PASSWORD") or getpass.getpass("Davantis password: ")
    try:
        return asyncio.run(run(args, password))
    except aiohttp.ClientError as err:
        print(f"CONNECTION ERROR: {err}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
