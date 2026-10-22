"""Config flow for the myAI integration."""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_BASE_URL,
    CONF_HA_CONTROL,
    CONF_MAX_HISTORY,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_SYSTEM_PROMPT,
    CONF_TEMPERATURE,
    DEFAULT_BASE_URL,
    DEFAULT_HA_CONTROL,
    DEFAULT_MAX_HISTORY,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_TEMPERATURE,
    DOMAIN,
)

# URLs are kept out of the translation strings (hassfest requirement) and
# injected at runtime via description placeholders instead.
URL_PLACEHOLDERS = {
    "api_url": "https://myai.swisscom.ch/settings/api",
    "faq_url": "https://myai.swisscom.ch/faq#myai-subscriptions",
}

# API keys are shown as a masked password field instead of plain text.
API_KEY_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="myAI"): str,
        vol.Required(CONF_API_KEY): API_KEY_SELECTOR,
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)


def _model_selector(
    models: list[str] | None,
    current: str | None = None,
    allow_custom: bool = False,
) -> Any:
    """Return a model dropdown, or a plain text field if no list is available.

    The current model is always kept in the list, even if the API no longer
    returns it. allow_custom lets the user type a model that is not listed.
    """
    if not models:
        return str
    options = list(models)
    if current and current not in options:
        options.insert(0, current)
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            mode=SelectSelectorMode.DROPDOWN,
            custom_value=allow_custom,
            sort=False,
        )
    )


async def _validate_credentials(hass, base_url: str, api_key: str) -> str | None:
    """Validate API credentials by calling /models. Return None on success, else an error key."""
    session = async_get_clientsession(hass)
    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 401:
                return "invalid_auth"
            if resp.status >= 400:
                return "cannot_connect"
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return "cannot_connect"


async def _test_connection(hass, base_url: str, api_key: str, model: str) -> str | None:
    """Test the API connection with a specific model. Return None on success, else an error key."""
    session = async_get_clientsession(hass)
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
    }
    try:
        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 401:
                return "invalid_auth"
            if resp.status >= 400:
                return "cannot_connect"
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return "cannot_connect"


async def _fetch_models(hass, base_url: str, api_key: str) -> list[str] | None:
    """Fetch available models from the /models endpoint. Returns None on failure."""
    session = async_get_clientsession(hass)
    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                return None
            result = await resp.json()
            models = [m["id"] for m in result.get("data", []) if "id" in m]
            return sorted(models) if models else None
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, TypeError):
        return None


class MyAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for myAI."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._user_input: dict[str, Any] = {}
        self._available_models: list[str] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MyAIOptionsFlow:
        """Get the options flow for this handler."""
        return MyAIOptionsFlow()

    async def async_step_user(self, user_input=None):
        """Handle the initial step — credentials and base URL with validation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate credentials before proceeding.
            error = await _validate_credentials(
                self.hass, user_input[CONF_BASE_URL], user_input[CONF_API_KEY]
            )
            if error:
                errors["base"] = error
            else:
                # Credentials valid – try to fetch models from the API.
                models = await _fetch_models(
                    self.hass, user_input[CONF_BASE_URL], user_input[CONF_API_KEY]
                )

                # Store input and proceed to model selection.
                self._user_input = user_input
                self._available_models = models
                return await self.async_step_model()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders=URL_PLACEHOLDERS,
        )

    async def async_step_model(self, user_input=None):
        """Handle model selection step — dropdown if models available, text input otherwise."""
        errors: dict[str, str] = {}

        if user_input is not None:
            merged = {**self._user_input, CONF_MODEL: user_input[CONF_MODEL]}

            error = await _test_connection(
                self.hass,
                merged[CONF_BASE_URL],
                merged[CONF_API_KEY],
                merged[CONF_MODEL],
            )
            if error:
                errors["base"] = error
            else:
                # No unique ID: model, API key and base URL can all change, so
                # there is no stable natural identifier. Allowing multiple
                # entries matches the documented behaviour (different model or
                # API key) and keeps reconfigure unblocked.
                return self.async_create_entry(
                    title=merged[CONF_NAME],
                    data=merged,
                    options={CONF_HA_CONTROL: user_input.get(CONF_HA_CONTROL, DEFAULT_HA_CONTROL)},
                )

        # Build schema: dropdown if models were fetched, text input otherwise.
        models = self._available_models
        default = (
            models[0] if models and DEFAULT_MODEL not in models else DEFAULT_MODEL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL, default=default): _model_selector(models),
                vol.Optional(CONF_HA_CONTROL, default=DEFAULT_HA_CONTROL): bool,
            }
        )

        return self.async_show_form(
            step_id="model",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        assert entry is not None

        if user_input is not None:
            error = await _test_connection(
                self.hass,
                user_input[CONF_BASE_URL],
                user_input[CONF_API_KEY],
                user_input[CONF_MODEL],
            )
            if error:
                errors["base"] = error
            else:
                # The entry is identified by its entry_id (from the context),
                # so no unique ID is needed. This lets the user freely change
                # the model, API key or base URL during reconfigure.
                # The model is also stored in options (which take precedence at
                # runtime), so update it there too or the change has no effect.
                return self.async_update_reload_and_abort(
                    entry,
                    title=user_input[CONF_NAME],
                    data=user_input,
                    options={**entry.options, CONF_MODEL: user_input[CONF_MODEL]},
                )

        # The model in use: options take precedence over data at runtime.
        current_model = entry.options.get(
            CONF_MODEL, entry.data.get(CONF_MODEL, DEFAULT_MODEL)
        )
        # Fetch models with the current credentials. Custom values stay
        # allowed, because the user may switch to a key with other models;
        # the connection test on submit validates the combination.
        models = await _fetch_models(
            self.hass,
            entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            entry.data.get(CONF_API_KEY, ""),
        )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=entry.data.get(CONF_NAME, "myAI")): str,
                vol.Required(
                    CONF_API_KEY, default=entry.data.get(CONF_API_KEY, "")
                ): API_KEY_SELECTOR,
                vol.Required(
                    CONF_BASE_URL,
                    default=entry.data.get(CONF_BASE_URL, DEFAULT_BASE_URL),
                ): str,
                vol.Required(CONF_MODEL, default=current_model): _model_selector(
                    models, current_model, allow_custom=True
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )


class MyAIOptionsFlow(config_entries.OptionsFlow):
    """Handle options for myAI."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            # Separate credentials from options: move API key to data, keep the rest as options.
            new_options = dict(user_input)
            new_api_key = new_options.pop(CONF_API_KEY, None)
            if new_api_key:
                new_data = dict(self.config_entry.data)
                new_data[CONF_API_KEY] = new_api_key
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
            return self.async_create_entry(title="", data=new_options)

        options = self.config_entry.options
        data = self.config_entry.data

        # Fetch available models from the API.
        current_model = options.get(CONF_MODEL, data.get(CONF_MODEL, DEFAULT_MODEL))
        available_models = await _fetch_models(
            self.hass, data.get(CONF_BASE_URL, DEFAULT_BASE_URL), data.get(CONF_API_KEY, "")
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_API_KEY,
                    default=data.get(CONF_API_KEY, ""),
                ): API_KEY_SELECTOR,
                vol.Optional(
                    CONF_MODEL,
                    default=current_model,
                ): _model_selector(available_models, current_model),
                vol.Optional(
                    CONF_SYSTEM_PROMPT,
                    default=options.get(CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT),
                ): TextSelector(
                    TextSelectorConfig(multiline=True, type=TextSelectorType.TEXT)
                ),
                vol.Optional(
                    CONF_MAX_TOKENS,
                    default=options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS),
                ): NumberSelector(
                    NumberSelectorConfig(min=0, max=128000, step=1, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_TEMPERATURE,
                    default=options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                ): NumberSelector(
                    NumberSelectorConfig(min=0.0, max=2.0, step=0.1, mode=NumberSelectorMode.SLIDER)
                ),
                vol.Optional(
                    CONF_MAX_HISTORY,
                    default=options.get(CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY),
                ): NumberSelector(
                    NumberSelectorConfig(min=2, max=100, step=1, mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(
                    CONF_HA_CONTROL,
                    default=options.get(CONF_HA_CONTROL, DEFAULT_HA_CONTROL),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
