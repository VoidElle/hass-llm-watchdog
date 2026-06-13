"""Config flow for LLM Watchdog."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_KEYS,
    CONF_PROVIDERS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    PROVIDERS,
)

try:
    from homeassistant.helpers import selector
except ImportError:  # pragma: no cover
    selector = None


def _provider_options() -> list[dict[str, str]]:
    return [
        {"value": provider_id, "label": str(provider["name"])}
        for provider_id, provider in PROVIDERS.items()
    ]


def _providers_schema(default: list[str]) -> vol.Schema:
    if selector is not None:
        return vol.Schema(
            {
                vol.Required(CONF_PROVIDERS, default=default): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_provider_options(),
                        multiple=True,
                    )
                )
            }
        )
    return vol.Schema(
        {
            vol.Required(CONF_PROVIDERS, default=default): vol.All(
                [vol.In(list(PROVIDERS.keys()))],
                vol.Length(min=1),
            )
        }
    )


def _api_keys_schema(
    selected_providers: list[str],
    defaults: Mapping[str, str] | None = None,
) -> vol.Schema:
    defaults = defaults or {}
    schema: dict[Any, Any] = {}
    for provider_id in selected_providers:
        schema[vol.Optional(provider_id, default=defaults.get(provider_id, ""))] = str
    return vol.Schema(schema)


def _scan_interval_schema(default: int) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_SCAN_INTERVAL, default=default): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL),
            )
        }
    )


class LLMWatchdogConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LLM Watchdog."""

    VERSION = 1

    def __init__(self) -> None:
        self._selected_providers = list(PROVIDERS.keys())
        self._api_keys: dict[str, str] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Select providers to monitor."""
        if user_input is not None:
            self._selected_providers = user_input[CONF_PROVIDERS]
            return await self.async_step_api_keys()

        return self.async_show_form(
            step_id="user",
            data_schema=_providers_schema(self._selected_providers),
        )

    async def async_step_api_keys(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect optional API keys for active checks."""
        if user_input is not None:
            self._api_keys = {
                provider_id: api_key
                for provider_id, api_key in user_input.items()
                if api_key
            }
            return await self.async_step_scan_interval()

        return self.async_show_form(
            step_id="api_keys",
            data_schema=_api_keys_schema(self._selected_providers, self._api_keys),
        )

    async def async_step_scan_interval(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect the polling interval."""
        if user_input is not None:
            return self.async_create_entry(
                title="LLM Watchdog",
                data={
                    CONF_PROVIDERS: self._selected_providers,
                    CONF_API_KEYS: self._api_keys,
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                },
            )

        return self.async_show_form(
            step_id="scan_interval",
            data_schema=_scan_interval_schema(DEFAULT_SCAN_INTERVAL),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "LLMWatchdogOptionsFlow":
        """Return the options flow handler."""
        return LLMWatchdogOptionsFlow(config_entry)


class LLMWatchdogOptionsFlow(config_entries.OptionsFlow):
    """Handle LLM Watchdog options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._selected_providers = list(
            config_entry.options.get(
                CONF_PROVIDERS,
                config_entry.data.get(CONF_PROVIDERS, list(PROVIDERS.keys())),
            )
        )
        self._api_keys = {
            **config_entry.data.get(CONF_API_KEYS, {}),
            **config_entry.options.get(CONF_API_KEYS, {}),
        }
        self._scan_interval = int(
            config_entry.options.get(
                CONF_SCAN_INTERVAL,
                config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Select providers to monitor."""
        if user_input is not None:
            self._selected_providers = user_input[CONF_PROVIDERS]
            self._api_keys = {
                provider_id: api_key
                for provider_id, api_key in self._api_keys.items()
                if provider_id in self._selected_providers
            }
            return await self.async_step_api_keys()

        return self.async_show_form(
            step_id="init",
            data_schema=_providers_schema(self._selected_providers),
        )

    async def async_step_api_keys(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect optional API keys for active checks."""
        if user_input is not None:
            self._api_keys = {
                provider_id: api_key
                for provider_id, api_key in user_input.items()
                if api_key
            }
            return await self.async_step_scan_interval()

        return self.async_show_form(
            step_id="api_keys",
            data_schema=_api_keys_schema(self._selected_providers, self._api_keys),
        )

    async def async_step_scan_interval(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Collect the polling interval."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_PROVIDERS: self._selected_providers,
                    CONF_API_KEYS: self._api_keys,
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                },
            )

        return self.async_show_form(
            step_id="scan_interval",
            data_schema=_scan_interval_schema(self._scan_interval),
        )
