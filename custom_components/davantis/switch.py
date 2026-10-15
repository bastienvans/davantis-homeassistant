"""Switch platform for Davantis relay outputs."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, RELAY_ICONS
from .coordinator import DavantisCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Davantis relay switches, adding new relays as they appear."""
    coordinator: DavantisCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()

    @callback
    def _add_new_relays() -> None:
        new = [rid for rid in coordinator.data if rid not in known]
        if not new:
            return
        known.update(new)
        async_add_entities(
            DavantisRelaySwitch(coordinator, entry, rid) for rid in new
        )

    _add_new_relays()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_relays))


class DavantisRelaySwitch(CoordinatorEntity[DavantisCoordinator], SwitchEntity):
    """A single Davantis relay output exposed as a switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DavantisCoordinator,
        entry: ConfigEntry,
        relay_id: str,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self._relay_id = relay_id
        self._attr_unique_id = f"{entry.entry_id}_relay_{relay_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Davantis",
            model="Perimeter appliance",
        )

    @property
    def _relay(self) -> dict[str, Any]:
        """Return this relay's latest data from the coordinator."""
        return self.coordinator.data.get(self._relay_id, {})

    @property
    def available(self) -> bool:
        """Return True if the relay is still present in the latest poll."""
        return super().available and self._relay_id in self.coordinator.data

    @property
    def name(self) -> str:
        """Return the relay alias, falling back to its id."""
        alias = self._relay.get("alias")
        return alias if alias else f"Relay {self._relay_id}"

    @property
    def icon(self) -> str | None:
        """Return an icon based on the relay alias."""
        alias = str(self._relay.get("alias") or "").lower()
        return RELAY_ICONS.get(alias)

    @property
    def is_on(self) -> bool:
        """Return True if the relay is active."""
        return bool(self._relay.get("status"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the relay on."""
        await self.coordinator.client.async_set_relay(self._relay_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the relay off."""
        await self.coordinator.client.async_set_relay(self._relay_id, False)
        await self.coordinator.async_request_refresh()
