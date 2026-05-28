<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/myai/brand/dark_logo.png">
    <img src="custom_components/myai/brand/logo.png" alt="myAI" width="320">
  </picture>
</p>

# myAI – Home Assistant Custom Integration

A lean custom integration that connects any **OpenAI-compatible API** to Home Assistant.
It registers an **AI Task entity** that can be used with the `ai_task.generate_data` action,
including **structured output**.

## Features

- Works with any OpenAI-compatible `/chat/completions` endpoint
- Multiple instances (different models / API keys / endpoints)
- Structured output via the `structure` parameter (returned as parsed data)
- Fully configured through the Home Assistant UI – no YAML required

## Requirements

- Home Assistant **2025.8** or newer (AI Task entity + structured output)
- An OpenAI-compatible API endpoint and API key
- An active **myAI Pro** subscription with API access — see the
  [myAI subscriptions FAQ](https://myai.swisscom.ch/faq#myai-subscriptions)

> **Note:** API access is part of the paid myAI Pro plan. Without an active
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
2. Enter a name, API key, base URL and model ID.
   - The base URL must point to the API root that exposes `/chat/completions`
     (e.g. `https://code.myai.swisscom.ch/v1`).

### Multiple models

Add the integration multiple times. Each instance has its own API key, base URL and model ID.

## Usage

In an automation, script, or the Developer Tools:

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

Provide a `structure` to receive parsed, typed data instead of free text:

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

## Attachments

Image/file attachments are **not supported**. The configured model is treated as text-only,
so Home Assistant will show
*"AI Task entity … does not support attachments"* if the **Attachments** option is used.
This is the standard Home Assistant behavior for text-only entities. Supporting attachments
would require a vision-capable model and multimodal request handling.

## License

MIT
