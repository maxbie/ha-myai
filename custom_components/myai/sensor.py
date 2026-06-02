"""Sensor platform for the myAI integration — token usage tracking."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODEL, DOMAIN, SIGNAL_USAGE_UPDATED

# Per-sensor icons: input (prompt), output (completion), and the sum (total).
ICONS = {
    "prompt_tokens": "mdi:debug-step-into",
    "completion_tokens": "mdi:debug-step-out",
    "total_tokens": "mdi:sigma",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the myAI token usage sensors."""
    async_add_entities(
        [
            MyAITokenSensor(config_entry, "total_tokens", "Total Tokens"),
            MyAITokenSensor(config_entry, "prompt_tokens", "Prompt Tokens"),
            MyAITokenSensor(config_entry, "completion_tokens", "Completion Tokens"),
        ]
    )


class MyAITokenSensor(SensorEntity):
    """Sensor tracking cumulative token usage for a myAI instance."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "tokens"
    _attr_translation_key = "token_usage"

    def __init__(
        self, config_entry: ConfigEntry, token_key: str, name_suffix: str
    ) -> None:
        """Initialize the sensor."""
        self._entry = config_entry
        self._token_key = token_key
        self._attr_name = name_suffix
        self._attr_unique_id = f"{config_entry.entry_id}_{token_key}"
        self._attr_icon = ICONS.get(token_key)

    @property
    def device_info(self) -> DeviceInfo:
        """Group the sensor under the same device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data[CONF_NAME],
            manufacturer="myAI",
            model=self._entry.data[CONF_MODEL],
        )

    @property
    def native_value(self) -> int:
        """Return the current token count."""
        runtime = self._entry.runtime_data
        if runtime is None:
            return 0
        return getattr(runtime, self._token_key, 0)

    async def async_added_to_hass(self) -> None:
        """Subscribe to usage update signals."""
        await super().async_added_to_hass()

        @callback
        def _handle_usage_update() -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_USAGE_UPDATED.format(entry_id=self._entry.entry_id),
                _handle_usage_update,
            )
        )
