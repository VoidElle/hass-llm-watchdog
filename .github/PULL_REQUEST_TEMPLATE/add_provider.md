## Add provider: <Provider Name>

### Provider details

| Field | Value |
|---|---|
| Provider ID (snake_case) | `my_provider` |
| Display name | My Provider |
| Status page URL | `https://status.myprovider.com/api/v2/status.json` (or `none`) |
| Active probe URL | `https://api.myprovider.com/v1/models` |
| Auth type | Bearer / query param / custom header |

### providers.json entry

```json
"my_provider": {
  "name": "My Provider",
  "statuspage_url": "https://status.myprovider.com/api/v2/status.json",
  "active_check": {
    "url": "https://api.myprovider.com/v1/models",
    "auth_header": "Authorization",
    "auth_format": "Bearer {key}"
  }
}
```

### Checklist

- [ ] Entry added to `providers.json`
- [ ] Active probe uses a free/metadata endpoint (no generation calls)
- [ ] `translations/en.json` updated with the new API key label (config + options steps)
- [ ] `translations/it.json` updated with the Italian API key label (config + options steps)
- [ ] Manually verified the status page URL returns a valid Statuspage.io v2 JSON response (if applicable)
- [ ] Manually verified the active probe returns HTTP 200 with a valid key
