import logging
from collections.abc import Iterable

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_create_utility_meters(
    hass: HomeAssistant,
    source_entity: str,
    sensor_name: str,
    meter_description: str,
    cycles: Iterable[str],
) -> None:
    """Create selected Utility Meter helpers for a sensor."""
    for cycle in cycles:
        entries = hass.config_entries.async_entries("utility_meter")
        meter_name = f"{sensor_name} - {meter_description} {cycle}"
        existing_entry = next(
            (
                entry
                for entry in entries
                if entry.options.get("source") == source_entity
                and entry.options.get("cycle") == cycle
            ),
            None,
        )
        if existing_entry is not None:
            if existing_entry.title != meter_name:
                hass.config_entries.async_update_entry(
                    existing_entry, title=meter_name
                )
            continue

        result = await hass.config_entries.flow.async_init(
            "utility_meter",
            context={"source": "user"},
            data={
                "name": meter_name,
                "source": source_entity,
                "cycle": cycle,
                "offset": 0,
                "tariffs": [],
                "net_consumption": False,
                "delta_values": False,
                "periodically_resetting": True,
                "always_available": False,
            },
        )
        if result["type"] != "create_entry":
            _LOGGER.error(
                "Could not create %s %s utility meter for %s: %s",
                meter_description,
                cycle,
                source_entity,
                result,
            )
