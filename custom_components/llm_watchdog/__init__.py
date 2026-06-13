"""The LLM Watchdog integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .coordinator import LLMWatchdogCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up LLM Watchdog from a config entry."""
    session = async_get_clientsession(hass)
    coordinator = LLMWatchdogCoordinator(hass, entry, session)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        shutdown = getattr(coordinator, "async_shutdown", None)
        if callable(shutdown):
            await shutdown()
    return unload_ok
