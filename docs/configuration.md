# Configuration

After installation, add **LLM Watchdog** from **Settings → Devices & Services → Add Integration**.

## Step 1: Select providers

The first step lets you choose which providers to monitor.

- If you keep every provider selected, that effectively means **all supported providers**.
- To monitor only a subset, deselect the providers you do not need.
- You can change the selection later from the integration's **Configure** button.

## Step 2: Enter API keys

API keys are optional for providers that have a public status page, because LLM Watchdog can still do passive monitoring.

### Providers that work passively without an API key

These providers have a public status page, so they still report passive health data even when the API key is left blank:

- OpenAI
- Anthropic
- Mistral
- Cohere
- Groq
- Perplexity
- Stability AI

### Providers that need an API key for any usable data

These providers have **no public status page** in `providers.json`:

- Google (Gemini)
- xAI (Grok)
- Meta/Llama

If no API key is configured for one of those providers, its sensor becomes **unavailable** in Home Assistant.

> Important: Google, xAI, and Meta/Llama have **no status page**, so they show **unavailable** in Home Assistant if no API key is configured.

## Step 3: Choose the polling interval

The last step asks for the polling interval in minutes.

- **Default:** 5 minutes
- **Minimum:** 1 minute
- **Recommendation:** use a longer interval if you enable many active probes or are close to API rate limits

## Reconfigure later with the options flow

To change providers, API keys, or the polling interval later:

1. Open **Settings → Devices & Services**.
2. Find **LLM Watchdog**.
3. Click the integration card.
4. Click **Configure**.
5. Walk through the same three steps again.

## Provider reference

| Provider | Status page available | Works without API key | Active probe endpoint |
|---|---|---|---|
| OpenAI | Yes | Yes, passive only | `GET https://api.openai.com/v1/models` |
| Anthropic | Yes | Yes, passive only | `GET https://api.anthropic.com/v1/models` |
| Google (Gemini) | No | No | `GET https://generativelanguage.googleapis.com/v1/models?key=...` |
| Mistral | Yes | Yes, passive only | `GET https://api.mistral.ai/v1/models` |
| Cohere | Yes | Yes, passive only | `GET https://api.cohere.com/v1/models` |
| Groq | Yes | Yes, passive only | `GET https://api.groq.com/openai/v1/models` |
| Perplexity | Yes | Yes, passive only | `GET https://api.perplexity.ai/models` |
| Stability AI | Yes | Yes, passive only | `GET https://api.stability.ai/v1/user/account` |
| xAI (Grok) | No | No | `GET https://api.x.ai/v1/models` |
| Meta/Llama | No | No | `GET https://api.together.xyz/v1/models` |
