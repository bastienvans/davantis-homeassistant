# Davantis for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration for
[Davantis](https://www.davantis.com/) perimeter-protection systems.

It talks **directly to your appliance on the local network** (no cloud
dependency) and exposes each relay output as a Home Assistant **switch** — so a
relay wired to your garden lights, a gate, a siren, etc. can be toggled from
dashboards, automations, scripts and voice assistants.

> **Unofficial.** This project is not affiliated with or endorsed by Davantis.
> It was built by reverse-engineering the behaviour of the official Android app
> against a user's own system, for interoperability with hardware they own. Use
> it at your own risk.

## Features

- 🔌 Local polling — no internet round-trip, keeps working if your WAN is down
- 💡 Each relay output becomes a `switch` entity (lights/water/sound/panic get
  a matching icon automatically)
- ⚙️ Simple UI config flow (host, port, username, password)
- 🔄 Automatic token refresh

### Planned

- Inputs as `binary_sensor` entities (door/PIR state)
- Cameras as `camera` entities (snapshot / MJPEG / stream)
- Alarms as events
- Optional cloud mode (`api.davantis.com`) for off-site access

## Requirements

- Home Assistant 2024.1.0 or newer
- A Davantis appliance reachable on your LAN
- Your Davantis app username and password

## Installation (HACS)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**.
2. Add `https://github.com/bastienvans/davantis-homeassistant` with category
   **Integration**.
3. Install **Davantis**, then restart Home Assistant.

<details>
<summary>Manual installation</summary>

Copy `custom_components/davantis/` into your Home Assistant `config/custom_components/`
directory and restart.
</details>

## Configuration

**Settings → Devices & Services → Add Integration → Davantis**, then enter:

| Field | Example | Notes |
|-------|---------|-------|
| Host | `192.168.1.50` | Your appliance's LAN IP |
| Port | `21000` | Appliance port |
| Username | `admin` | Your Davantis app login |
| Password | `••••••••` | Stored by Home Assistant, never by this repo |
| Polling interval | `10` | Seconds between state refreshes |

Each relay then appears as a switch named after its alias in the appliance
(for example **light**).

## How it works

In the official app's "local mode", requests are sent straight to the
appliance. This integration uses the same three endpoints:

| Call | Endpoint | Body |
|------|----------|------|
| Login / refresh | `POST /oauth/token` | OAuth2 password / refresh grant (form-encoded) |
| List relays | `GET /relays` | — |
| Set a relay | `PATCH /relays/{id}` | `{"status": "true"\|"false", "id": "<id>"}` |

The OAuth2 **client** id/secret are the ones shipped in the public app binary
and are identical for every install; they are not user secrets. Your own
username and password are entered in the config flow and stored only by Home
Assistant.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

`tools/smoke_test.py` exercises a real appliance from your LAN:

```bash
python tools/smoke_test.py --host 192.168.1.50 --port 21000 --username admin
# add "--relay <id> --on" / "--off" to toggle a relay
```

## License

[MIT](LICENSE)
