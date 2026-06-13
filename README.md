# LLM Watchdog

> Monitor the health of major AI/LLM providers directly from Home Assistant.

LLM Watchdog combines **passive status-page polling** (no API key required) with **optional active API probes** to give you a real-time picture of every AI provider you depend on - all as standard Home Assistant sensor entities.

---

## Supported providers

| Provider | Status page | Active probe endpoint |
|---|---|---|
| OpenAI | ✅ | `GET /v1/models` |
| Anthropic | ✅ | `GET /v1/models` |
| Google Gemini | - | `GET /v1/models?key=…` |
| Mistral | ✅ | `GET /v1/models` |
| Cohere | ✅ | `GET /v1/models` |
| Groq | ✅ | `GET /openai/v1/models` |
| Perplexity | ✅ | `GET /models` |
| Stability AI | ✅ | `GET /v1/user/account` |
| xAI (Grok) | - | `GET /v1/models` |
| Meta/Llama (Together AI) | - | `GET /v1/models` |

Active probes only call free metadata endpoints - **never** completion or generation endpoints, so there are no token costs.

---

## Installation

### Via HACS (recommended)

1. Open **HACS → Integrations** in Home Assistant.
2. Click the overflow menu (⋮) → **Custom repositories**.
3. Add `https://github.com/VoidElle/hass-llm-watchdog` as type **Integration**.
4. Find **LLM Watchdog** in the list and click **Download**.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/llm_watchdog/` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **LLM Watchdog** and follow the three-step setup:

| Step | What you choose |
|---|---|
| **1 - Providers** | Which of the 10 providers to monitor (default: all) |
| **2 - API keys** | Optional key per provider for active probing (blank = passive only) |
| **3 - Polling interval** | How often to check, in minutes (default: 5, min: 1) |

To change settings later, go to the integration entry and click **Configure**.

---

## Sensors

The integration creates one sensor per enabled provider plus a summary sensor.

### Sensor states

| State | Meaning |
|---|---|
| `healthy` | Status page is green **and** active probe succeeded (or not configured) |
| `degraded` | Status page reports a minor incident, or probe was slow / partial error |
| `down` | Status page reports a major/critical outage, or probe failed / timed out |
| `unknown` | No reliable data available yet |

### Provider sensor attributes

| Attribute | Description |
|---|---|
| `provider_id` | Internal key (e.g. `openai`) |
| `provider_name` | Display name (e.g. `OpenAI`) |
| `passive_status` | Status derived from the public status page |
| `active_status` | Status from the API probe, or `not_configured` if no key is set |
| `latency_ms` | Round-trip time of the active probe in milliseconds |
| `last_checked` | ISO 8601 timestamp of the last update |
| `message` | Human-readable description from the status page or probe |

### Summary sensor (`sensor.llm_watchdog_summary`)

Its state is the **worst** status across all monitored providers. Extra attributes:

| Attribute | Description |
|---|---|
| `providers` | Full result dict keyed by provider ID |
| `counts` | `{healthy: N, degraded: N, down: N, unknown: N}` |

---

## Example Lovelace card

```yaml
type: entities
title: LLM Watchdog
entities:
  - entity: sensor.llm_watchdog_summary
    name: Overall
  - sensor.llm_watchdog_openai
  - sensor.llm_watchdog_anthropic
  - sensor.llm_watchdog_google
  - sensor.llm_watchdog_mistral
  - sensor.llm_watchdog_groq
```

For a grid layout with status badges, use the [custom button-card](https://github.com/custom-cards/button-card):

```yaml
type: grid
columns: 3
cards:
  - type: custom:button-card
    entity: sensor.llm_watchdog_openai
    name: OpenAI
    show_state: true
  - type: custom:button-card
    entity: sensor.llm_watchdog_anthropic
    name: Anthropic
    show_state: true
```

---

## Adding a new provider

Open a pull request using the [**Add provider** template](https://github.com/VoidElle/hass-llm-watchdog/compare?template=add_provider.md). The template covers:

1. Adding the entry to `providers.json`
2. Updating `translations/en.json` and `translations/it.json` with the new API key label
3. Verifying the status page URL and active probe endpoint

The new provider will appear in the configuration flow automatically after the next restart.

---

## API cost & rate-limit note

Active probes use lightweight metadata endpoints and carry no generation cost. However, they do count as API requests and may be subject to your plan's rate limits. If you're on a strict free tier, consider leaving the API key blank and relying on passive monitoring alone.
