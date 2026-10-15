"""Constants for the Davantis integration."""

from __future__ import annotations

DOMAIN = "davantis"

# OAuth2 client credentials shipped inside the official Davantis Android app
# (com.cirici.davantis, res/values/strings.xml). These are not secrets: they
# are identical for every install and are only the OAuth *client* identity,
# not a user credential. The user's own username/password are entered at
# runtime via the config flow and are never stored in this repository.
CLIENT_ID = "1_3njtj8n8iji8cg8ck4kwsoco0wscswwwsgwwgwkgoo44c4044s"
CLIENT_SECRET = "cpagow9b548o8g8ck0o0cs0ooscwccko44so8wwcws8s0swow"

DEFAULT_PORT = 21000
DEFAULT_SCAN_INTERVAL = 10  # seconds; the official app polls every 5s

# Relay aliases the app recognises, mapped to a Material Design Icon so the
# switch shows a sensible glyph in the Home Assistant UI.
RELAY_ICONS = {
    "light": "mdi:lightbulb",
    "water": "mdi:water",
    "sound": "mdi:volume-high",
    "panic": "mdi:alarm-light",
}
