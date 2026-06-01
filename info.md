## What's new in 2.1.0

**AI Task entity** — myAI now provides an `ai_task.generate_data` entity for one-shot
prompts in automations and scripts. Supports structured output via JSON schema
(`response_format`) and vision/image attachments.

**Shared API helper** — Centralized API call logic with retry, timeout handling, and
token tracking shared between the conversation agent and AI task platforms.

---

## What's new in 2.0.0

**Conversation agent** — myAI registers as a conversation agent. Use it as your
voice assistant in Voice Preview with full Home Assistant device control (turn on lights,
check sensors, lock doors, etc.). Supports multi-turn tool calling (up to 10 iterations).

**Options flow** — Change API key, model, system prompt, temperature, max tokens,
history limit, and more without deleting and re-adding the integration.

**Reconfigure** — Update base URL and name from the integration card menu.

**Model dropdown** — During setup, if the endpoint supports `/models`, you get a
dropdown instead of typing the model ID manually.

**Custom system prompt** — Set a persona or instructions per instance
(e.g. "Always respond in German").

**Token usage sensors** — Three sensors per instance tracking total, prompt, and
completion tokens. Works with long-term statistics.

**Home Assistant control toggle** — Disable device control for a pure chat agent.

**Vision / image attachments** — Forward images to multimodal models via base64 encoding.

**Retry with backoff** — Automatic retry on transient 5xx errors or timeouts.

**Diagnostics** — Download config (API key redacted) and usage for bug reports.

**Conversation history limit** — Cap turns to stay within token budgets (default: 20).
