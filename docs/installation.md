# Installation

LLM Watchdog requires **Home Assistant 2024.1 or newer**.

## Install with HACS (recommended)

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=VoidElle&repository=hass-llm-watchdog&category=integration)

### Manual HACS steps

1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Open the menu in the top-right corner and choose **Custom repositories**.
4. Add `https://github.com/VoidElle/hass-llm-watchdog`.
5. Select **Integration** as the category.
6. Click **Add**.
7. Search for **LLM Watchdog** in HACS.
8. Open the integration page and click **Download**.
9. Restart Home Assistant after installation.

## Manual install

1. Download or clone this repository.
2. Copy `custom_components/llm_watchdog/` into your Home Assistant `config/custom_components/` directory.
3. Verify the final path looks like `config/custom_components/llm_watchdog/manifest.json`.
4. Restart Home Assistant.
5. In Home Assistant, go to **Settings → Devices & Services → Add Integration**.
6. Search for **LLM Watchdog** and complete the configuration flow.

## Requirements

| Requirement | Notes |
|---|---|
| Home Assistant | **2024.1+** |
| Internet access | Needed to reach provider status pages and optional API endpoints |
| API keys | Optional for providers with public status pages; required for providers with no status page |
