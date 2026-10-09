from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the counter reset buttons."""
    async_add_entities(
        [
            CounterResetButton(entry.entry_id, "distance", "reset_distance"),
            CounterResetButton(entry.entry_id, "time", "reset_time"),
        ]
    )


class CounterResetButton(ButtonEntity):
    """Button that resets one counter for a distance tracker."""

    _attr_has_entity_name = True

    def __init__(self, entry_id: str, counter: str, translation_key: str) -> None:
        self._entry_id = entry_id
        self._counter = counter
        self._attr_unique_id = f"distance_tracker_{entry_id}_reset_{counter}"
        self._attr_translation_key = translation_key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
        )

    async def async_press(self) -> None:
        """Reset the selected counter."""
        self.hass.bus.async_fire(
            f"distance_tracker_reset_{self._counter}_{self._entry_id}"
        )
