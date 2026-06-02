"""The myAI integration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN  # noqa: F401

PLATFORMS = [Platform.SENSOR, Platform.CONVERSATION, Platform.AI_TASK]

type MyAIConfigEntry = ConfigEntry["MyAIRuntimeData"]


@dataclass
class MyAIRuntimeData:
    """Runtime data stored on the config entry."""

    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0


async def async_setup_entry(hass: HomeAssistant, entry: MyAIConfigEntry) -> bool:
    """Set up myAI from a config entry."""
    entry.runtime_data = MyAIRuntimeData()

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyAIConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: MyAIConfigEntry) -> None:
    """Handle options update — reload the entry to pick up new settings."""
    await hass.config_entries.async_reload(entry.entry_id)
