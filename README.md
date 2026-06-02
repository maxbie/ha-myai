<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/myai/brand/dark_logo.png">
    <img src="custom_components/myai/brand/logo.png" alt="myAI" width="320">
  </picture>
</p>

# myAI – Home Assistant Custom Integration

A custom integration for **Swisscom myAI** in Home Assistant.
It provides a **Conversation agent** (for Voice Preview and automations), an **AI Task entity**
(for one-shot generation with structured output), and **token usage sensors** — all configured
through the UI.

This integration is purpose-built for the **myAI platform by Swisscom**.

## Features

- Built specifically for the **Swisscom myAI** platform
- **Conversation agent** — use as a voice assistant with full device control
- **AI Task entity** — one-shot `ai_task.generate_data` with structured output (JSON schema)
- **Token usage sensors** — track prompt, completion, and total tokens (long-term statistics)
- Multiple instances (different models / API keys)
- **Options flow** — change model, API key, system prompt, temperature, and more without re-adding
- **Reconfigure** — update base URL and credentials from the integration page
- **Model dropdown** — auto-fetches available models from the myAI API during setup
- **Custom system prompt** — set a persona or instructions per instance
- **Max tokens & temperature** — tune verbosity and creativity
- **Conversation history limit** — cap turns to stay within token budgets (default: 20)
- **Home Assistant device control** — toggle on/off per instance (function calling / tools)
- **Retry with backoff** — automatic retry on transient 5xx errors or timeouts
- **Diagnostics** — export config (API key redacted) and usage for bug reports
- Fully configured through the Home Assistant UI – no YAML required

## Requirements

- Home Assistant **2025.8** or newer
- A **Swisscom myAI** account with API access — see the
  [myAI subscriptions FAQ](https://myai.swisscom.ch/faq#myai-subscriptions)

> **Note:** API access requires a myAI Pro plan from Swisscom. Without an active
> subscription the connection test during setup will fail with an
> authentication error.

## Installation

### Via HACS (recommended)

1. In Home Assistant, open **HACS**.
2. Open the three-dot menu (top right) → **Custom repositories**.
3. Add the repository URL `https://github.com/maxbie/ha-myai` and choose type **Integration**.
4. Search for **myAI** in HACS, install it, then **restart Home Assistant**.

### Manual

1. Copy the folder `custom_components/myai/` into `/config/custom_components/myai/`.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → myAI**.
2. Enter a name and your Swisscom myAI API key.
   - The base URL is pre-configured to `https://code.myai.swisscom.ch/v1` — no changes needed.
   - The integration fetches available models from your myAI account and presents them in a dropdown.
   - The default model is `qwen3.5-397b-a17b`.

### Multiple models

Add the integration multiple times. Each instance can use a different model or API key.

### Options

After setup, click **Configure** on the integration card to adjust:

| Option        | Description                                              | Default              |
| ---------------| ----------------------------------------------------------| ----------------------|
| API key       | Update your Swisscom myAI API key                        | *(from setup)*       |
| Model ID      | Switch to a different model available on myAI            | `qwen3.5-397b-a17b` |
| System prompt | Custom instructions prepended to every conversation      | *(built-in default)* |
| Max tokens    | Limit response length (0 = no limit)                     | `0`                  |
| Temperature   | Creativity (0.0 – 2.0)                                   | `1.0`                |
| Max history   | Conversation turns to keep in context                    | `20`                 |
| HA control    | Enable device control via voice (tools/function calling) | `on`                 |

### Reconfigure

To change the base URL or name without deleting the entry, use the three-dot menu on the
integration card → **Reconfigure**.

## Usage

### Voice assistant (Conversation agent)

1. Go to **Settings → Voice assistants**.
2. Create or edit an assistant and select your myAI instance as the **Conversation agent**.
3. Use it in Voice Preview, the Assist dialog, or any automation that calls `conversation.process`.

With **HA control** enabled, the agent can turn on lights, lock doors, check sensor states,
and more — using the same intents and tools as the built-in assistant. The agent supports
multi-turn tool calling (up to 10 iterations per request) for complex tasks.

### AI Task (generate data)

Use `ai_task.generate_data` in automations, scripts, or the Developer Tools to run one-shot
prompts without conversation context:

```yaml
action: ai_task.generate_data
data:
  task_name: Joke
  instructions: "Tell me a joke"
  entity_id: ai_task.myai_qwen3_5
response_variable: myai_response
```

The generated text is available at `myai_response.data`.

### Structured output

Provide a `structure` to receive parsed, typed data instead of free text. The integration
sends a JSON schema via the API's `response_format` parameter:

```yaml
action: ai_task.generate_data
data:
  task_name: Weather summary
  instructions: "Summarize today's weather: sunny, high of 24°C."
  entity_id: ai_task.myai_qwen3_5
  structure:
    summary:
      description: "Short one-sentence summary"
      required: true
      selector:
        text:
    temperature:
      description: "High temperature in Celsius"
      selector:
        number:
response_variable: myai_response
```

The result is available as parsed data, e.g. `myai_response.data.summary`.

### Token usage sensors

Each instance exposes three sensors:

- `sensor.myai_<name>_total_tokens`
- `sensor.myai_<name>_prompt_tokens`
- `sensor.myai_<name>_completion_tokens`

These use `TOTAL_INCREASING` state class, so they work with the Energy dashboard and
long-term statistics. Values reset on HA restart.

## Diagnostics

Go to the integration page → three-dot menu → **Download diagnostics** to get a JSON
export of your configuration (API key redacted) and current token usage. Attach this
to bug reports.

## Upgrading from 1.x

Version 2.0.0 added the conversation agent, sensors, options flow, and more.
Existing 1.x configurations will continue to work — the new platforms are added
automatically on restart. No manual migration needed.

## Changelog

### 2.0.0

- **AI Task entity** — new `ai_task.generate_data` platform with structured output
  (JSON schema via `response_format`).
- Conversation agent with multi-turn tool calling and HA device control.
- Shared API helper with centralized retry logic and token tracking.
- Options flow, reconfigure flow, model dropdown.
- Token usage sensors with long-term statistics.
- Custom system prompt, temperature, max tokens, history limit.
- Retry with backoff on transient errors.
- Diagnostics export.

## License

MIT
