# Sensors

LLM Watchdog creates one sensor per configured provider plus one summary sensor.

## Provider sensors

### Entity ID format

Provider sensors default to Home Assistant slugs based on the provider name:

```text
sensor.<provider_name_slug>
```

Examples:

- `sensor.openai`
- `sensor.anthropic`
- `sensor.google_gemini`

### State values

| State | Meaning |
|---|---|
| `healthy` | Public status page is healthy and the active probe is healthy or not configured |
| `degraded` | Public status page reports a minor issue, or the active probe returns a degraded result such as HTTP 429 |
| `down` | Public status page reports a major or critical issue, or the active probe fails or times out |
| `unknown` | LLM Watchdog does not have enough reliable information to classify the provider |
| `unavailable` | The provider has no status page and no API key is configured, so Home Assistant has nothing usable to show |

### Provider attributes

| Attribute | Type | Description |
|---|---|---|
| `provider_id` | string | Internal provider key from `providers.json` |
| `provider_name` | string | Human-readable provider name |
| `passive_status` | string | Status derived from the public status page |
| `active_status` | string | Status from the API probe, or `not_configured` if no API key is set |
| `latency_ms` | integer or `null` | Active probe latency in milliseconds |
| `last_checked` | string | ISO 8601 timestamp of the most recent update |
| `message` | string | Provider message from the status page or active probe |

## Summary sensor

### Entity ID

```text
sensor.summary
```

### What it does

The summary sensor reports the **worst** state across all configured providers.

Worst-status logic:

1. If any provider is `down`, the summary is `down`.
2. Otherwise, if any provider is `degraded`, the summary is `degraded`.
3. Otherwise, if any provider is `unknown`, the summary is `unknown`.
4. Otherwise, the summary is `healthy`.

### Summary attributes

| Attribute | Type | Description |
|---|---|---|
| `providers` | object | Full per-provider result payload keyed by provider ID |
| `counts` | object | Count of providers in each combined state: `healthy`, `degraded`, `down`, `unknown` |

## When a sensor shows `unavailable`

A provider sensor becomes `unavailable` when both of these are true:

1. The provider has **no** public status page.
2. No API key is configured, so the active probe is `not_configured`.

Today that mainly affects:

- Google (Gemini)
- xAI (Grok)
- Meta/Llama

If you add an API key for one of those providers, the sensor becomes available again.

## Example: healthy OpenAI sensor

```json
{
  "entity_id": "sensor.openai",
  "state": "healthy",
  "attributes": {
    "provider_id": "openai",
    "provider_name": "OpenAI",
    "passive_status": "healthy",
    "active_status": "healthy",
    "latency_ms": 182,
    "last_checked": "2026-06-13T10:00:00+00:00",
    "message": "All Systems Operational"
  }
}
```
