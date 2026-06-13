"""Constants for the LLM Watchdog integration."""

from __future__ import annotations

import json
from pathlib import Path

DOMAIN = "llm_watchdog"
DEFAULT_SCAN_INTERVAL = 5
MIN_SCAN_INTERVAL = 1
DEFAULT_TIMEOUT = 10

PROVIDERS: dict[str, dict[str, object]] = json.loads(
    (Path(__file__).parent / "providers.json").read_text(encoding="utf-8")
)

STATUS_HEALTHY = "healthy"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"
STATUS_UNKNOWN = "unknown"
STATUS_NOT_CONFIGURED = "not_configured"

CONF_PROVIDERS = "providers"
CONF_API_KEYS = "api_keys"
CONF_SCAN_INTERVAL = "scan_interval"
