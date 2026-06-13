"""Tests for the LLM Watchdog integration."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import timedelta
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.llm_watchdog.const import (
    CONF_API_KEYS,
    CONF_PROVIDERS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    STATUS_DEGRADED,
    STATUS_DOWN,
    STATUS_HEALTHY,
    STATUS_NOT_CONFIGURED,
    STATUS_UNKNOWN,
)

pytestmark = pytest.mark.asyncio


class FakeResponse:
    """Fake aiohttp response."""

    def __init__(self, status: int, payload: Mapping[str, Any] | None = None) -> None:
        self.status = status
        self._payload = payload or {}

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False

    async def json(self) -> Mapping[str, Any]:
        return self._payload


class FakeRequestContext:
    """Fake aiohttp request context manager."""

    def __init__(
        self,
        status: int | None = None,
        payload: Mapping[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._status = status
        self._payload = payload
        self._error = error

    async def __aenter__(self) -> FakeResponse:
        if self._error is not None:
            raise self._error
        return FakeResponse(self._status or 200, self._payload)

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        return False


class FakeSession:
    """Fake aiohttp client session."""

    def __init__(self, responses: Mapping[str, Any]) -> None:
        self._responses = responses

    def get(
        self,
        url: str,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> FakeRequestContext:
        del headers, params
        result = self._responses[url]
        if isinstance(result, Exception):
            return FakeRequestContext(error=result)
        return FakeRequestContext(status=result["status"], payload=result.get("payload"))


async def _setup_integration(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
    responses: Mapping[str, Any],
    api_key: str | None = "test-key",
    providers: list[str] | None = None,
    options: Mapping[str, Any] | None = None,
) -> MockConfigEntry:
    providers = providers or ["openai"]
    api_keys = {provider_id: api_key for provider_id in providers} if api_key else {}
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="LLM Watchdog",
        data={
            CONF_PROVIDERS: providers,
            CONF_API_KEYS: api_keys,
            CONF_SCAN_INTERVAL: 5,
        },
        options=dict(options or {}),
        entry_id="test-entry",
    )
    entry.add_to_hass(hass)
    monkeypatch.setattr(
        "custom_components.llm_watchdog.async_get_clientsession",
        lambda _hass: FakeSession(responses),
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _provider_state(hass: Any, provider_id: str = "openai") -> Any:
    for state in hass.states.async_all("sensor"):
        if state.attributes.get("provider_id") == provider_id:
            return state
    return None


def _summary_state(hass: Any) -> Any:
    for state in hass.states.async_all("sensor"):
        if state.attributes.get("friendly_name") == "Summary":
            return state
    return None


async def test_sensors_created_for_each_configured_provider(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
        "https://status.anthropic.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.anthropic.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(
        hass,
        monkeypatch,
        responses,
        providers=["openai", "anthropic"],
    )

    assert _provider_state(hass, "openai") is not None
    assert _provider_state(hass, "anthropic") is not None
    assert _summary_state(hass) is not None


async def test_healthy_combination(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    summary = _summary_state(hass)
    assert provider is not None
    assert summary is not None
    assert provider.state == STATUS_HEALTHY
    assert provider.attributes["passive_status"] == STATUS_HEALTHY
    assert provider.attributes["active_status"] == STATUS_HEALTHY
    assert summary.state == STATUS_HEALTHY
    assert summary.attributes["counts"][STATUS_HEALTHY] == 1


async def test_degraded_combination(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "minor", "description": "Minor service outage"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_DEGRADED
    assert provider.attributes["passive_status"] == STATUS_DEGRADED
    assert provider.attributes["active_status"] == STATUS_HEALTHY


async def test_down_combination(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "major", "description": "Major outage"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_DOWN
    assert provider.attributes["passive_status"] == STATUS_DOWN


async def test_unknown_when_statuspage_unreachable(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": RuntimeError("status page unreachable"),
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_UNKNOWN
    assert provider.attributes["passive_status"] == STATUS_UNKNOWN
    assert provider.attributes["active_status"] == STATUS_HEALTHY


async def test_not_configured_skips_active_check(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        }
    }

    await _setup_integration(hass, monkeypatch, responses, api_key=None)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_HEALTHY
    assert provider.attributes["passive_status"] == STATUS_HEALTHY
    assert provider.attributes["active_status"] == STATUS_NOT_CONFIGURED


async def test_active_probe_429_returns_degraded(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.openai.com/v1/models": {"status": 429, "payload": {"error": "rate limited"}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_DEGRADED
    assert provider.attributes["active_status"] == STATUS_DEGRADED


async def test_active_probe_timeout_returns_down(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.openai.com/v1/models": asyncio.TimeoutError(),
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_DOWN
    assert provider.attributes["active_status"] == STATUS_DOWN


async def test_active_probe_500_returns_down(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.openai.com/v1/models": {"status": 500, "payload": {"error": "server error"}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_DOWN
    assert provider.attributes["active_status"] == STATUS_DOWN


async def test_passive_critical_returns_down(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "critical", "description": "Critical outage"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_DOWN
    assert provider.attributes["passive_status"] == STATUS_DOWN


async def test_summary_worst_status_is_down_when_one_provider_down(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
        "https://status.anthropic.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "major", "description": "Major outage"}},
        },
        "https://api.anthropic.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(
        hass,
        monkeypatch,
        responses,
        providers=["openai", "anthropic"],
    )

    summary = _summary_state(hass)
    assert summary is not None
    assert summary.state == STATUS_DOWN


async def test_summary_healthy_when_all_healthy(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
        "https://status.anthropic.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        },
        "https://api.anthropic.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(
        hass,
        monkeypatch,
        responses,
        providers=["openai", "anthropic"],
    )

    summary = _summary_state(hass)
    assert summary is not None
    assert summary.state == STATUS_HEALTHY
    assert summary.attributes["counts"][STATUS_HEALTHY] == 2


async def test_no_statuspage_provider_unavailable_without_api_key(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _setup_integration(
        hass,
        monkeypatch,
        responses={},
        api_key=None,
        providers=["google"],
    )

    assert _provider_state(hass, "google") is None


async def test_no_statuspage_provider_active_when_api_key_provided(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        "https://generativelanguage.googleapis.com/v1/models": {
            "status": 200,
            "payload": {"models": []},
        }
    }

    await _setup_integration(
        hass,
        monkeypatch,
        responses=responses,
        providers=["google"],
    )

    provider = _provider_state(hass, "google")
    assert provider is not None
    assert provider.state == STATUS_UNKNOWN
    assert provider.attributes["passive_status"] == STATUS_UNKNOWN
    assert provider.attributes["active_status"] == STATUS_HEALTHY


async def test_passive_down_overrides_active_healthy(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "major", "description": "Major outage"}},
        },
        "https://api.openai.com/v1/models": {"status": 200, "payload": {"data": []}},
    }

    await _setup_integration(hass, monkeypatch, responses)

    provider = _provider_state(hass)
    assert provider is not None
    assert provider.state == STATUS_DOWN
    assert provider.attributes["passive_status"] == STATUS_DOWN
    assert provider.attributes["active_status"] == STATUS_HEALTHY


async def test_coordinator_uses_options_scan_interval(
    hass: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        "https://status.openai.com/api/v2/status.json": {
            "status": 200,
            "payload": {"status": {"indicator": "none", "description": "All Systems Operational"}},
        }
    }

    entry = await _setup_integration(
        hass,
        monkeypatch,
        responses,
        api_key=None,
        options={CONF_SCAN_INTERVAL: 10},
    )

    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.update_interval == timedelta(minutes=10)
