"""Config flow for the myAI integration."""
from __future__ import annotations

import asyncio

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_BASE_URL,
    CONF_MODEL,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="myAI"): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Required(CONF_MODEL, default=DEFAULT_MODEL): str,
    }
)


async def _test_connection(hass, base_url: str, api_key: str, model: str) -> str | None:
    """Test the API connection. Return None on success, else an error key."""
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


class MyAIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for myAI."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # One entry per base URL + model combination.
            unique_id = f"{user_input[CONF_BASE_URL]}::{user_input[CONF_MODEL]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            error = await _test_connection(
                self.hass,
                user_input[CONF_BASE_URL],
                user_input[CONF_API_KEY],
                user_input[CONF_MODEL],
            )
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
