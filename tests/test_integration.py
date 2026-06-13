"""Tests for the LLM Watchdog integration."""

from __future__ import annotations

from collections.abc import Mapping
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
) -> None:
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
        entry_id="test-entry",
    )
    entry.add_to_hass(hass)
    monkeypatch.setattr(
        "custom_components.llm_watchdog.async_get_clientsession",
        lambda _hass: FakeSession(responses),
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _provider_state(hass: Any):
    return hass.states.get("sensor.llm_watchdog_openai")


def _summary_state(hass: Any):
    return hass.states.get("sensor.llm_watchdog_summary")


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

    assert hass.states.get("sensor.llm_watchdog_openai") is not None
    assert hass.states.get("sensor.llm_watchdog_anthropic") is not None
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
