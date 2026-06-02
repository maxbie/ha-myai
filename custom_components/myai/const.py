"""Constants for the myAI integration."""

DOMAIN = "myai"

CONF_BASE_URL = "base_url"
CONF_MODEL = "model"
CONF_SYSTEM_PROMPT = "system_prompt"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_MAX_HISTORY = "max_history"
CONF_HA_CONTROL = "ha_control"

DEFAULT_BASE_URL = "https://code.myai.swisscom.ch/v1"
DEFAULT_MODEL = "qwen3.5-397b-a17b"
DEFAULT_SYSTEM_PROMPT = """You are a conversation assistant for Home Assistant.
Answer questions about the world truthfully.
Answer in plain text. Keep it short, simple and to the point.
Be concise, warm, and conversational.
When controlling devices, confirm the action short (e.g., "Done", "ok").
If a request is ambiguous, ask a short clarifying question.
If something is outside your capabilities, say so very short."""
DEFAULT_MAX_TOKENS = 0  # 0 means no limit (let the API decide)
DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_HISTORY = 20  # max conversation turns to keep
DEFAULT_HA_CONTROL = False  # Home Assistant device control is opt-in

# Retry settings
MAX_RETRIES = 1
RETRY_DELAY = 1.0  # seconds

# Dispatcher signal for token usage updates
SIGNAL_USAGE_UPDATED = f"{DOMAIN}_usage_updated_{{entry_id}}"
