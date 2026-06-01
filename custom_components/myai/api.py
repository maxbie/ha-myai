"""Shared API helper for the myAI integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_BASE_URL,
    CONF_MAX_TOKENS,
    CONF_MODEL,
    CONF_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    MAX_RETRIES,
    RETRY_DELAY,
    SIGNAL_USAGE_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=120, connect=10, sock_read=110)


def get_option(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Get a value from options, falling back to data, then default."""
    return entry.options.get(key, entry.data.get(key, default))


async def async_call_api(
    hass: HomeAssistant,
    entry: ConfigEntry,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Call the OpenAI-compatible API with retry logic and token tracking.

    Returns the parsed JSON response dict.
    Raises aiohttp.ClientError or asyncio.TimeoutError on failure.
    """
    session = async_get_clientsession(hass)
    data = entry.data

    url = data[CONF_BASE_URL].rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {data[CONF_API_KEY]}",
        "Content-Type": "application/json",
    }

    # Apply options.
    model = get_option(entry, CONF_MODEL)
    temperature = get_option(entry, CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
    max_tokens = get_option(entry, CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)

    payload.setdefault("model", model)
    if temperature != DEFAULT_TEMPERATURE:
        payload.setdefault("temperature", temperature)
    if max_tokens and int(max_tokens) > 0:
        payload.setdefault("max_tokens", int(max_tokens))

    last_error: Exception | None = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            async with session.post(
                url, headers=headers, json=payload, timeout=TIMEOUT
            ) as resp:
                if resp.status >= 500 and attempt < MAX_RETRIES:
                    # Retryable server error.
                    _LOGGER.debug(
                        "myAI API returned %s, retrying (%d/%d)",
                        resp.status,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    await asyncio.sleep(RETRY_DELAY)
                    continue

                result = await resp.json()

                # Track token usage.
                _track_usage(hass, entry, result)

                # Attach status for callers to inspect.
                result["_http_status"] = resp.status
                return result

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            last_error = err
            if attempt < MAX_RETRIES:
                _LOGGER.debug(
                    "myAI API request failed (%s), retrying (%d/%d)",
                    err,
                    attempt + 1,
                    MAX_RETRIES,
                )
                await asyncio.sleep(RETRY_DELAY)
                continue
            raise

    # Should not reach here, but just in case.
    if last_error:
        raise last_error
    raise aiohttp.ClientError("Unexpected error in API call loop")


def _track_usage(hass: HomeAssistant, entry: ConfigEntry, result: dict) -> None:
    """Track token usage from the API response."""
    usage = result.get("usage")
    if not usage:
        return

    runtime = entry.runtime_data
    if runtime is None:
        return

    for key in ("total_tokens", "prompt_tokens", "completion_tokens"):
        if key in usage:
            current = getattr(runtime, key, 0)
            setattr(runtime, key, current + usage[key])

    # Signal sensors to update via dispatcher.
    async_dispatcher_send(hass, SIGNAL_USAGE_UPDATED.format(entry_id=entry.entry_id))
