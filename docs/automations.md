# Automations

Below are ready-to-paste Home Assistant automation examples.

## 1. Notify when any provider goes down

```yaml
alias: LLM Watchdog - Notify when any provider goes down
mode: single
trigger:
  - platform: state
    entity_id: sensor.summary
    to: down
action:
  - service: notify.notify
    data:
      title: LLM Watchdog alert
      message: >-
        {% set providers = state_attr('sensor.summary', 'providers') or {} %}
        {% set ns = namespace(items=[]) %}
        {% for provider_id, details in providers.items() %}
          {% if details.combined_status == 'down' %}
            {% set ns.items = ns.items + [provider_id] %}
          {% endif %}
        {% endfor %}
        One or more providers are down: {{ ns.items | join(', ') if ns.items else 'unknown' }}.
```

## 2. Notify when OpenAI degrades

```yaml
alias: LLM Watchdog - Notify when OpenAI degrades
mode: single
trigger:
  - platform: state
    entity_id: sensor.openai
    to: degraded
action:
  - service: notify.notify
    data:
      title: OpenAI degraded
      message: >-
        OpenAI is degraded.
        passive={{ state_attr('sensor.openai', 'passive_status') }},
        active={{ state_attr('sensor.openai', 'active_status') }},
        message={{ state_attr('sensor.openai', 'message') }}
```

## 3. Send a daily digest of provider statuses

```yaml
alias: LLM Watchdog - Daily status digest
mode: single
trigger:
  - platform: time
    at: "09:00:00"
action:
  - service: notify.notify
    data:
      title: Daily LLM provider status digest
      message: >-
        {% set providers = state_attr('sensor.summary', 'providers') or {} %}
        Summary: {{ states('sensor.summary') }}.
        {% for provider_id, details in providers.items() %}
          {{ provider_id }}={{ details.combined_status }}{% if not loop.last %}; {% endif %}
        {% endfor %}
```

## 4. Send a recovery notification when summary returns healthy

```yaml
alias: LLM Watchdog - Notify on recovery
mode: single
trigger:
  - platform: state
    entity_id: sensor.summary
    to: healthy
condition:
  - condition: template
    value_template: >-
      {{ trigger.from_state is not none and trigger.from_state.state in ['down', 'degraded', 'unknown'] }}
action:
  - service: notify.notify
    data:
      title: LLM Watchdog recovery
      message: All monitored providers are back to healthy.
```
