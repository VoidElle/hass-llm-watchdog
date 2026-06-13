"""Sensor platform for LLM Watchdog."""

from __future__ import annotations

from collections import Counter
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROVIDERS,
    DOMAIN,
    PROVIDERS,
    STATUS_DEGRADED,
    STATUS_DOWN,
    STATUS_HEALTHY,
    STATUS_UNKNOWN,
)
from .coordinator import LLMWatchdogCoordinator

STATUS_ICONS = {
    STATUS_HEALTHY: "mdi:check-circle",
    STATUS_DEGRADED: "mdi:alert",
    STATUS_DOWN: "mdi:close-circle",
    STATUS_UNKNOWN: "mdi:help-circle",
}

STATUS_OPTIONS = [STATUS_HEALTHY, STATUS_DEGRADED, STATUS_DOWN, STATUS_UNKNOWN]
STATUS_ORDER = [STATUS_DOWN, STATUS_DEGRADED, STATUS_UNKNOWN, STATUS_HEALTHY]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LLM Watchdog sensors from a config entry."""
    coordinator: LLMWatchdogCoordinator = hass.data[DOMAIN][entry.entry_id]
    enabled_providers = entry.options.get(
        CONF_PROVIDERS,
        entry.data.get(CONF_PROVIDERS, list(PROVIDERS.keys())),
    )

    entities: list[SensorEntity] = [
        LLMWatchdogProviderSensor(coordinator, provider_id)
        for provider_id in enabled_providers
        if provider_id in PROVIDERS
    ]
    entities.append(LLMWatchdogSummarySensor(coordinator))
    async_add_entities(entities)


class LLMWatchdogProviderSensor(CoordinatorEntity[LLMWatchdogCoordinator], SensorEntity):
    """Representation of a provider health sensor."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS

    def __init__(self, coordinator: LLMWatchdogCoordinator, provider_id: str) -> None:
        super().__init__(coordinator)
        self._provider_id = provider_id
        self._provider_name = str(PROVIDERS[provider_id]["name"])
        self._attr_unique_id = f"llm_watchdog_{provider_id}"
        self._attr_name = f"LLM Watchdog {self._provider_name}"

    @property
    def native_value(self) -> str:
        """Return the provider combined status."""
        return str(self._provider_data.get("combined_status", STATUS_UNKNOWN))

    @property
    def icon(self) -> str:
        """Return an icon based on the current status."""
        return STATUS_ICONS.get(self.native_value, STATUS_ICONS[STATUS_UNKNOWN])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return provider details."""
        return {
            "provider_id": self._provider_id,
            "provider_name": self._provider_name,
            "passive_status": self._provider_data.get("passive_status"),
            "active_status": self._provider_data.get("active_status"),
            "latency_ms": self._provider_data.get("latency_ms"),
            "last_checked": self._provider_data.get("last_checked"),
            "message": self._provider_data.get("message"),
        }

    @property
    def _provider_data(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._provider_id, {}) if self.coordinator.data else {}


class LLMWatchdogSummarySensor(CoordinatorEntity[LLMWatchdogCoordinator], SensorEntity):
    """Summary sensor for all providers."""

    _attr_has_entity_name = False
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS
    _attr_unique_id = "llm_watchdog_summary"
    _attr_name = "LLM Watchdog Summary"

    @property
    def native_value(self) -> str:
        """Return the worst provider state."""
        provider_states = [
            str(details.get("combined_status", STATUS_UNKNOWN))
            for details in (self.coordinator.data or {}).values()
        ]
        if not provider_states:
            return STATUS_UNKNOWN
        for status in STATUS_ORDER:
            if status in provider_states:
                return status
        return STATUS_UNKNOWN

    @property
    def icon(self) -> str:
        """Return an icon based on the summary state."""
        return STATUS_ICONS.get(self.native_value, STATUS_ICONS[STATUS_UNKNOWN])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aggregated provider details."""
        provider_data = self.coordinator.data or {}
        counts = Counter(
            str(details.get("combined_status", STATUS_UNKNOWN))
            for details in provider_data.values()
        )
        return {
            "providers": provider_data,
            "counts": {
                STATUS_HEALTHY: counts.get(STATUS_HEALTHY, 0),
                STATUS_DEGRADED: counts.get(STATUS_DEGRADED, 0),
                STATUS_DOWN: counts.get(STATUS_DOWN, 0),
                STATUS_UNKNOWN: counts.get(STATUS_UNKNOWN, 0),
            },
        }
