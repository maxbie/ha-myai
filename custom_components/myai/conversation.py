"""Conversation platform for the myAI integration."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal

import aiohttp
from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import async_call_api, get_option
from .const import (
    CONF_HA_CONTROL,
    CONF_MAX_HISTORY,
    CONF_MODEL,
    CONF_SYSTEM_PROMPT,
    DEFAULT_HA_CONTROL,
    DEFAULT_MAX_HISTORY,
    DEFAULT_SYSTEM_PROMPT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10

# Resolve the selector serializer defensively across HA versions.
_SELECTOR_SERIALIZER = getattr(llm, "selector_serializer", None) or getattr(
    llm, "_selector_serializer", None
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the myAI conversation entity from a config entry."""
    async_add_entities([MyAIConversationEntity(config_entry)])


class MyAIConversationEntity(conversation.ConversationEntity):
    """myAI conversation agent."""

    _attr_has_entity_name = True
    _attr_name = "Conversation"
    _attr_supports_streaming = False
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the entity."""
        self._entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_conversation"

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    @property
    def device_info(self) -> DeviceInfo:
        """Group the entity under a device in the UI."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data[CONF_NAME],
            manufacturer="myAI",
            model=self._entry.data[CONF_MODEL],
        )

    async def async_added_to_hass(self) -> None:
        """Register as a conversation agent when added to HA."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister as a conversation agent when removed."""
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        """Process the user input and call the API."""
        # Build the custom system prompt from options.
        custom_prompt = get_option(
            self._entry, CONF_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT
        ) or None

        # Determine whether to expose HA device control tools.
        ha_control = get_option(self._entry, CONF_HA_CONTROL, DEFAULT_HA_CONTROL)
        llm_api = llm.LLM_API_ASSIST if ha_control else None

        # Provide LLM data (system prompt, tools, exposed entities) to the chat log.
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                user_llm_hass_api=llm_api,
                user_llm_prompt=custom_prompt,
                user_extra_system_prompt=user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        # Run the multi-turn tool-calling loop.
        for _iteration in range(MAX_TOOL_ITERATIONS):
            result = await self._call_api(chat_log)

            # If the model didn't request any tool calls, we're done.
            if not result.tool_calls:
                break

            # Execute tool calls and feed results back into the chat log.
            async for _tool_result in chat_log.async_add_assistant_content(result):
                pass

            # If there are no unresponded tool results, stop.
            if not chat_log.unresponded_tool_results:
                break
        else:
            # Exceeded max iterations — add a final message.
            chat_log.async_add_assistant_content_without_tools(
                conversation.AssistantContent(
                    agent_id=self.entity_id,
                    content="Sorry, I wasn't able to complete that request within the allowed number of steps.",
                )
            )

        return conversation.async_get_result_from_chat_log(user_input, chat_log)

    async def _call_api(
        self, chat_log: conversation.ChatLog
    ) -> conversation.AssistantContent:
        """Make a single API call and return the assistant content."""
        messages = self._build_messages(chat_log)
        payload: dict[str, Any] = {"messages": messages}

        # Expose HA tools to the model if available.
        tools_spec = self._build_tools_spec(chat_log)
        if tools_spec:
            payload["tools"] = tools_spec

        try:
            result = await async_call_api(self.hass, self._entry, payload)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            return self._error_content(f"Error talking to the myAI API: {err}")

        status = result.get("_http_status", 200)
        if status == 401:
            return self._error_content("myAI rejected the API key (HTTP 401)")
        if status >= 400:
            return self._error_content(
                f"myAI API error (HTTP {status}): {str(result)[:200]}"
            )

        try:
            message = result["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            return self._error_content("Unexpected response format from the API.")

        content_text = message.get("content") or ""
        tool_calls_raw = message.get("tool_calls")

        # Parse tool calls into HA ToolInput objects.
        tool_calls: list[llm.ToolInput] | None = None
        if tool_calls_raw:
            tool_calls = []
            for tc in tool_calls_raw:
                try:
                    args = json.loads(tc["function"]["arguments"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    args = {}
                tool_calls.append(
                    llm.ToolInput(
                        tool_name=tc["function"]["name"],
                        tool_args=args,
                        id=tc.get("id", ""),
                    )
                )

        assistant_content = conversation.AssistantContent(
            agent_id=self.entity_id,
            content=content_text or None,
            tool_calls=tool_calls,
        )

        # If there are no tool calls, add to chat log directly.
        if not tool_calls:
            chat_log.async_add_assistant_content_without_tools(assistant_content)

        return assistant_content

    def _build_messages(
        self, chat_log: conversation.ChatLog
    ) -> list[dict[str, Any]]:
        """Convert the HA chat log into myAI-compatible messages.

        Applies the max_history limit to avoid exceeding token budgets.
        """
        max_history = get_option(self._entry, CONF_MAX_HISTORY, DEFAULT_MAX_HISTORY)

        messages: list[dict[str, Any]] = []

        for content in chat_log.content:
            if content.role == "system" and content.content:
                messages.append({"role": "system", "content": content.content})
            elif content.role == "user":
                msg = self._build_user_message(content)
                messages.append(msg)
            elif content.role == "assistant":
                msg: dict[str, Any] = {"role": "assistant"}
                if content.content:
                    msg["content"] = content.content
                if content.tool_calls:
                    msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.tool_name,
                                "arguments": json.dumps(tc.tool_args),
                            },
                        }
                        for tc in content.tool_calls
                    ]
                messages.append(msg)
            elif content.role == "tool_result":
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": content.tool_call_id,
                        "content": json.dumps(content.tool_result),
                    }
                )

        # Apply history limit: keep system messages + last N messages,
        # ensuring we don't split tool_call / tool_result pairs.
        if len(messages) > max_history + 1:
            system_msgs = [m for m in messages if m["role"] == "system"]
            non_system = [m for m in messages if m["role"] != "system"]

            # Trim from the front, but never start on a "tool" message
            # or an "assistant" message with tool_calls (both would be
            # orphaned without their counterpart).
            trimmed = non_system[-max_history:]
            while trimmed and (
                trimmed[0]["role"] == "tool"
                or (
                    trimmed[0]["role"] == "assistant"
                    and "tool_calls" in trimmed[0]
                )
            ):
                trimmed = trimmed[1:]

            messages = system_msgs + trimmed

        return messages

    def _build_user_message(self, content: Any) -> dict[str, Any]:
        """Build a user message."""
        return {"role": "user", "content": content.content}

    def _build_tools_spec(
        self, chat_log: conversation.ChatLog
    ) -> list[dict[str, Any]] | None:
        """Build the tools array from the LLM API tools."""
        if not chat_log.llm_api or not chat_log.llm_api.tools:
            return None

        tools: list[dict[str, Any]] = []
        for tool in chat_log.llm_api.tools:
            func_spec: dict[str, Any] = {"name": tool.name}
            if tool.description:
                func_spec["description"] = tool.description
            if tool.parameters.schema:
                func_spec["parameters"] = convert(
                    tool.parameters,
                    custom_serializer=(
                        chat_log.llm_api.custom_serializer or _SELECTOR_SERIALIZER
                    ),
                )
            else:
                func_spec["parameters"] = {"type": "object", "properties": {}}
            tools.append({"type": "function", "function": func_spec})

        return tools or None

    def _error_content(self, message: str) -> conversation.AssistantContent:
        """Create an AssistantContent with an error message (no tool calls)."""
        return conversation.AssistantContent(
            agent_id=self.entity_id,
            content=message,
        )
