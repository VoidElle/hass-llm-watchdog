# Troubleshooting

## Sensor stuck on `unknown`

Possible causes:

- Home Assistant has only just started and the first refresh has not completed yet.
- The provider status page could not be reached.
- The provider has no status page, so the passive side stays `unknown`.
- The active probe is healthy, but the current combine logic still keeps some no-status-page providers at `unknown`.

What to check:

1. Wait for one polling cycle.
2. Open the sensor attributes and review `passive_status`, `active_status`, and `message`.
3. Enable debug logging and inspect the integration logs.

## Active probe shows `down` but the provider status page is green

This usually means the provider's public status page does not reflect your exact API experience.

Common reasons:

- Your API key is invalid or expired.
- The provider is rate limiting your account.
- A regional or account-specific issue is happening before the status page is updated.
- The metadata endpoint is returning an error even though the core service looks healthy publicly.

## Google, xAI, or Meta/Llama shows `unavailable`

That is expected when no API key is configured.

Those providers do not have a public status page in `providers.json`, so passive monitoring alone is impossible. Add an API key in the integration options flow to enable active probing.

## Rate limit warnings in logs

If you see warnings related to HTTP 429 or provider rate limits:

- Increase the polling interval.
- Disable active probes for providers where you do not need them.
- Check the provider's free-tier and burst limits.
- Avoid very short intervals when monitoring many providers with API keys.

## Enable debug logging

Add this to your Home Assistant configuration:

```yaml
logger:
  logs:
    custom_components.llm_watchdog: debug
```

Then restart Home Assistant or reload logging so you can inspect detailed coordinator and probe messages.
