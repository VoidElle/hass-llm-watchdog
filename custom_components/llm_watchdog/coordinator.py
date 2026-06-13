"""Coordinator for LLM Watchdog."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_API_KEYS,
    CONF_PROVIDERS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    PROVIDERS,
    STATUS_DEGRADED,
    STATUS_DOWN,
    STATUS_HEALTHY,
    STATUS_NOT_CONFIGURED,
    STATUS_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)
ACTIVE_SLOW_THRESHOLD_MS = 5000

PASSIVE_INDICATOR_MAP = {
    "none": STATUS_HEALTHY,
    "minor": STATUS_DEGRADED,
    "major": STATUS_DOWN,
    "critical": STATUS_DOWN,
}


class LLMWatchdogCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Coordinate API and status page checks for configured providers."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        session: ClientSession,
    ) -> None:
        interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=interval),
        )
        self.entry = entry
        self.session = session

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data for all enabled providers."""
        enabled_providers = self.entry.options.get(
            CONF_PROVIDERS,
            self.entry.data.get(CONF_PROVIDERS, list(PROVIDERS.keys())),
        )
        api_keys = {
            **self.entry.data.get(CONF_API_KEYS, {}),
            **self.entry.options.get(CONF_API_KEYS, {}),
        }

        tasks = {
            provider_id: self._check_provider(provider_id, api_keys.get(provider_id))
            for provider_id in enabled_providers
            if provider_id in PROVIDERS
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        data: dict[str, dict[str, Any]] = {}
        now = datetime.now(timezone.utc).isoformat()
        for provider_id, result in zip(tasks, results, strict=False):
            if isinstance(result, Exception):
                _LOGGER.warning("Provider %s check failed: %s", provider_id, result)
                data[provider_id] = {
                    "passive_status": STATUS_UNKNOWN,
                    "active_status": STATUS_UNKNOWN,
                    "combined_status": STATUS_UNKNOWN,
                    "latency_ms": None,
                    "message": str(result),
                    "last_checked": now,
                }
                continue
            data[provider_id] = result

        return data

    async def _check_provider(
        self,
        provider_id: str,
        api_key: str | None,
    ) -> dict[str, Any]:
        """Check a single provider without letting failures escape."""
        passive_result, active_result = await asyncio.gather(
            self._async_passive_check(provider_id),
            self._async_active_check(provider_id, api_key),
            return_exceptions=True,
        )

        passive_status = STATUS_UNKNOWN
        passive_message = ""
        if isinstance(passive_result, Exception):
            _LOGGER.warning("Passive check failed for %s: %s", provider_id, passive_result)
        else:
            passive_status = passive_result["status"]
            passive_message = passive_result["message"]

        active_status = STATUS_UNKNOWN
        active_message = ""
        latency_ms: int | None = None
        if isinstance(active_result, Exception):
            _LOGGER.warning("Active check failed for %s: %s", provider_id, active_result)
            active_status = STATUS_DOWN if api_key else STATUS_NOT_CONFIGURED
        else:
            active_status = active_result["status"]
            active_message = active_result["message"]
            latency_ms = active_result["latency_ms"]

        combined_status = self._combine_statuses(passive_status, active_status)
        message_parts = [part for part in (passive_message, active_message) if part]

        return {
            "passive_status": passive_status,
            "active_status": active_status,
            "combined_status": combined_status,
            "latency_ms": latency_ms,
            "message": " | ".join(message_parts),
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }

    async def _async_passive_check(self, provider_id: str) -> dict[str, str]:
        """Check a provider's public status page."""
        provider = PROVIDERS[provider_id]
        statuspage_url = provider.get("statuspage_url")
        if not isinstance(statuspage_url, str):
            return {"status": STATUS_UNKNOWN, "message": ""}

        async with asyncio.timeout(DEFAULT_TIMEOUT):
            async with self.session.get(statuspage_url) as response:
                if response.status != 200:
                    return {
                        "status": STATUS_UNKNOWN,
                        "message": f"Passive check returned HTTP {response.status}",
                    }
                payload = await response.json()

        indicator = payload.get("status", {}).get("indicator", "")
        description = payload.get("status", {}).get("description", "")
        return {
            "status": PASSIVE_INDICATOR_MAP.get(indicator, STATUS_UNKNOWN),
            "message": description,
        }

    async def _async_active_check(
        self,
        provider_id: str,
        api_key: str | None,
    ) -> dict[str, Any]:
        """Perform an authenticated active health check when configured."""
        provider = PROVIDERS[provider_id]
        active_check = provider.get("active_check")
        if not isinstance(active_check, dict) or not api_key:
            return {
                "status": STATUS_NOT_CONFIGURED,
                "message": "Active check not configured",
                "latency_ms": None,
            }

        headers: dict[str, str] = {}
        params: dict[str, str] = {}
        auth_header = active_check.get("auth_header")
        auth_format = active_check.get("auth_format")
        auth_query_param = active_check.get("auth_query_param")
        extra_headers = active_check.get("extra_headers", {})
        url = active_check["url"]

        if isinstance(auth_header, str) and isinstance(auth_format, str):
            headers[auth_header] = auth_format.format(key=api_key)
        elif isinstance(auth_query_param, str):
            params[auth_query_param] = api_key

        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items()})

        loop = asyncio.get_running_loop()
        start = loop.time()
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with self.session.get(url, headers=headers, params=params) as response:
                    latency_ms = round((loop.time() - start) * 1000)
                    if response.status == 200 and latency_ms <= ACTIVE_SLOW_THRESHOLD_MS:
                        return {
                            "status": STATUS_HEALTHY,
                            "message": "",
                            "latency_ms": latency_ms,
                        }
                    if response.status in (200, 206, 429, 503):
                        return {
                            "status": STATUS_DEGRADED,
                            "message": f"Active check returned HTTP {response.status}",
                            "latency_ms": latency_ms,
                        }
                    return {
                        "status": STATUS_DOWN,
                        "message": f"Active check returned HTTP {response.status}",
                        "latency_ms": latency_ms,
                    }
        except asyncio.TimeoutError:
            return {
                "status": STATUS_DOWN,
                "message": "Active check timed out",
                "latency_ms": None,
            }
        except Exception as err:
            return {
                "status": STATUS_DOWN,
                "message": str(err),
                "latency_ms": None,
            }

    def _combine_statuses(self, passive_status: str, active_status: str) -> str:
        """Combine passive and active results into one sensor state."""
        if passive_status == STATUS_HEALTHY and active_status in (
            STATUS_HEALTHY,
            STATUS_NOT_CONFIGURED,
        ):
            return STATUS_HEALTHY
        if passive_status == STATUS_DEGRADED or active_status == STATUS_DEGRADED:
            return STATUS_DEGRADED
        if passive_status == STATUS_DOWN or active_status == STATUS_DOWN:
            return STATUS_DOWN
        if passive_status == STATUS_UNKNOWN and active_status in (
            STATUS_UNKNOWN,
            STATUS_NOT_CONFIGURED,
            STATUS_HEALTHY,
        ):
            return STATUS_UNKNOWN
        return STATUS_UNKNOWN
