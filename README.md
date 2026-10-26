<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/maxbie/ha-myai/main/brand/dark_logo.png">
    <img src="https://raw.githubusercontent.com/maxbie/ha-myai/main/brand/logo.png" alt="myAI" width="320">
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
- **Conversation agent** — use as a voice assistant, with optional Home Assistant device control
- **AI Task entity** — one-shot `ai_task.generate_data` with structured output (JSON schema)
- **Token usage sensors** — track prompt, completion, and total tokens (long-term statistics)
- Multiple instances (different models / API keys)
- **Options flow** — change model, API key, system prompt, temperature, and more without re-adding
- **Reconfigure** — update name, API key, base URL, and model from the integration page
- **Model selection** — dropdown with the models available on your myAI account (setup, options, and reconfigure)
- **Custom system prompt** — set a persona or instructions per instance
- **Max tokens & temperature** — tune verbosity and creativity
- **Conversation history limit** — cap turns to stay within token budgets (default: 20)
- **Home Assistant device control** — opt-in per instance (function calling / tools), off by default
- **Automatic retry** — retries once on transient 5xx errors or timeouts
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

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=maxbie&repository=ha-myai&category=integration)

1. In Home Assistant, open **HACS**.
2. Search for **myAI** and open it.
3. Click **Download**, then **restart Home Assistant**.

### Manual

1. Copy the folder `custom_components/myai/` into `/config/custom_components/myai/`.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration → myAI**.
2. Enter a **Name** for this instance (e.g. `myAI Qwen 3.5`).
3. Enter your **API key** — generate one in your
   [myAI API settings](https://myai.swisscom.ch/settings/api).
4. Leave the **Base URL** as is — it's pre-configured to
   `https://code.myai.swisscom.ch/v1`.
5. Submit. If the key or URL is wrong, the error appears here and you can correct it.
6. Choose your **model** from the list (defaults to `qwen3.5-397b-a17b`).
   If the list can't be retrieved, type the **Model ID** manually instead.
   Optionally enable **Home Assistant device control** (off by default).
7. Submit again. The instance is created.

### Multiple models

Add the integration multiple times. Each instance can use a different model or API key.

### Options

After setup, click **Configure** on the integration card to adjust:

| Option        | Description                                              | Default              |
| ------------- | -------------------------------------------------------- | -------------------- |
| API key       | Update your Swisscom myAI API key                        | *(from setup)*       |
| Model ID      | Switch to a different model available on myAI            | `qwen3.5-397b-a17b`  |
| System prompt | Custom instructions for the conversation agent           | *(built-in default)* |
| Max tokens    | Limit response length (0 = no limit)                     | `0`                  |
| Temperature   | Creativity (0.0 – 2.0)                                   | `1.0`                |
| Max history   | Conversation turns the agent keeps in context            | `20`                 |
| HA control    | Enable device control via voice (tools/function calling) | `off`                |

### Reconfigure

To change the name, API key, base URL, or model without deleting the entry, use the
three-dot menu on the integration card → **Reconfigure**.

## Usage

### Voice assistant (Conversation agent)

1. Go to **Settings → Voice assistants**.
2. Create or edit an assistant and select your myAI instance as the **Conversation agent**.
3. Use it in Voice Preview, the Assist dialog, or any automation that calls `conversation.process`.

With **HA control** enabled, the agent can turn on lights, lock doors, check sensor states,
and more — using the same intents and tools as the built-in assistant. The agent supports
multi-turn tool calling (up to 10 iterations per request) for complex tasks. Device control
is **off by default**; enable it in the options if you want the agent to act on your home.

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

- `sensor.<name>_total_tokens`
- `sensor.<name>_prompt_tokens`
- `sensor.<name>_completion_tokens`

`<name>` is the instance name in lowercase with underscores, e.g. `myai_qwen_3_5`.

These use the `TOTAL_INCREASING` state class, so they work with long-term statistics.
Values reset on Home Assistant restart.

## Attachments

Image and file attachments are **not currently supported**. The myAI models exposed today
are treated as text-only, so Home Assistant will show *"AI Task entity … does not support
attachments"* if the **Attachments** option is used — this is the standard behavior for
text-only entities.

Vision support is gated on the model: once vision-capable models become available on the
myAI platform (and the integration forwards images to them), attachments can be enabled.
Until then, send your prompt as text.

## Diagnostics

Go to the integration page → three-dot menu → **Download diagnostics** to get a JSON
export of your configuration (API key redacted) and current token usage — attach this
to bug reports.

## Upgrading from 1.x

Version 2.0.0 added the conversation agent, sensors, options flow, and more.
Existing 1.x configurations will continue to work — the new platforms are added
automatically on restart. No manual migration needed.

## Changelog

### 2.0.12

- Reconfigure now offers the available models in a dropdown and preselects the model currently in use.
- Model selection in setup and options uses a dropdown instead of a radio list.
- API key fields are masked.

### 2.0.11

- Reconfigure now lets you change the model, API key, or base URL — model changes take effect immediately.
- Multiple instances with the same model but different API keys are now allowed.
- Added a confirmation message after a successful reconfigure (en, de, fr, it).

### 2.0.10

- Fix intent recognition on newer Home Assistant versions by converting probatio
  tool schemas with the matching converter, while retaining legacy schema support.
- Apply the same schema compatibility fix to AI Task structured output.
- Return and log API errors in Assist instead of losing the response.
- Report empty model responses explicitly.

### 2.0.8

- API key validation now happens in step 1 (before model selection) — invalid keys
  show an error immediately instead of letting users get stuck.
- Model selection in Options flow now fetches available models from API.
- Brand assets restored for HACS validation.

### 2.0.0

- **AI Task entity** — new `ai_task.generate_data` platform with structured output
  (JSON schema via `response_format`).
- Conversation agent with multi-turn tool calling and optional HA device control.
- Shared API helper with centralized retry logic and token tracking.
- Options flow, reconfigure flow, model selection.
- Token usage sensors with long-term statistics.
- Custom system prompt, temperature, max tokens, history limit.
- Automatic retry on transient errors.
- Diagnostics export.

## Contributing

Thanks to [@Bhafner2](https://github.com/Bhafner2) for contributions to this project.

## License

MIT
