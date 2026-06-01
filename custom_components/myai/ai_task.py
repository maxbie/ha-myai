"""AI Task platform for the myAI integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp
from voluptuous_openapi import convert

from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
)
from homeassistant.components.conversation import ChatLog
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import async_call_api
from .const import (
    CONF_MODEL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Home Assistant exposes a serializer that turns selector-based schemas into
# JSON schema. The exact name has varied across versions, so resolve it
# defensively; a value of None falls back to default voluptuous handling.
_SELECTOR_SERIALIZER = getattr(llm, "selector_serializer", None) or getattr(
    llm, "_selector_serializer", None
)
if _SELECTOR_SERIALIZER is None:
    _LOGGER.warning(
        "Could not resolve selector_serializer from homeassistant.helpers.llm; "
        "structured output schema conversion may not serialize selectors correctly"
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the myAI AI Task entity from a config entry."""
    async_add_entities([MyAITaskEntity(config_entry)])


class MyAITaskEntity(AITaskEntity):
    """myAI AI Task entity backed by an OpenAI-compatible API."""

    _attr_has_entity_name = False
    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the entity."""
        self._entry = config_entry
        self._attr_name = config_entry.data[CONF_NAME]
        self._attr_unique_id = config_entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Group the entity under a device in the UI."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._attr_name,
            manufacturer="myAI",
            model=self._entry.data[CONF_MODEL],
        )

    async def _async_generate_data(
        self, task: GenDataTask, chat_log
    ) -> GenDataTaskResult:
        """Call the API and return the generated data."""
        payload: dict[str, Any] = {
            "messages": [{"role": "user", "content": task.instructions}],
        }

        # Structured output: convert the HA selector schema into a JSON schema
        # and ask the model to respond strictly in that shape.
        if task.structure is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "schema": convert(
                        task.structure, custom_serializer=_SELECTOR_SERIALIZER
                    ),
                },
            }

        try:
            result = await async_call_api(self.hass, self._entry, payload)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HomeAssistantError(f"Error talking to the myAI API: {err}") from err

        status = result.get("_http_status", 200)
        if status == 401:
            raise HomeAssistantError("myAI rejected the API key (HTTP 401)")
        if status >= 400:
            raise HomeAssistantError(
                f"myAI API error (HTTP {status}): {str(result)[:200]}"
            )

        try:
            text = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as err:
            raise HomeAssistantError(
                f"Unexpected myAI response format: {result}"
            ) from err

        if not text:
            raise HomeAssistantError("myAI returned an empty response")

        if task.structure is None:
            return GenDataTaskResult(
                conversation_id=chat_log.conversation_id,
                data=text,
            )

        try:
            structured = json.loads(_strip_code_fences(text))
        except json.JSONDecodeError as err:
            raise HomeAssistantError(
                f"myAI did not return valid JSON for the requested structure: "
                f"{text[:200]}"
            ) from err

        return GenDataTaskResult(
            conversation_id=chat_log.conversation_id,
            data=structured,
        )


def _strip_code_fences(text: str) -> str:
    """Strip ``` / ```json fences some models wrap JSON output in."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    text = text.split("\n", 1)[1] if "\n" in text else ""
    if "```" in text:
        text = text.rsplit("```", 1)[0]
    return text.strip()
