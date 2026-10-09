import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry, selector
from .helpers import async_create_utility_meters

DOMAIN = "distance_tracker"
UTILITY_METER_DOMAIN = "utility_meter"
CONFIG_FIELDS = {
    "device_tracker": "Choose the device to track",
    "binary_sensor": "Choose the binary sensor that needs to be on to track",
    "distance_unit": "Distance unit",
    "create_daily_utility_meter": "Create daily distance utility meter (resets every day)",
    "create_weekly_utility_meter": "Create weekly distance utility meter (resets every week)",
    "create_monthly_utility_meter": "Create monthly distance utility meter (resets every month)",
    "create_daily_time_utility_meter": "Create daily time utility meter (resets every day)",
    "create_weekly_time_utility_meter": "Create weekly time utility meter (resets every week)",
    "create_monthly_time_utility_meter": "Create monthly time utility meter (resets every month)",
    "sensor_name": "Name for the distance sensor",
}
UTILITY_METERS_FIELD = "Select utility meters to delete (unchecked meters are kept)"
DISTANCE_METER_FIELDS = {
    "Create daily distance utility meter if missing": "daily",
    "Create weekly distance utility meter if missing": "weekly",
    "Create monthly distance utility meter if missing": "monthly",
}
TIME_METER_FIELDS = {
    "Create daily time utility meter if missing": "daily",
    "Create weekly time utility meter if missing": "weekly",
    "Create monthly time utility meter if missing": "monthly",
}

class DistanceTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Distance Tracker."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            data = {
                key: user_input[display_name]
                for key, display_name in CONFIG_FIELDS.items()
            }
            return self.async_create_entry(
                title=data["sensor_name"],
                data=data
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONFIG_FIELDS["sensor_name"]): selector.TextSelector(),
                vol.Required(CONFIG_FIELDS["device_tracker"]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="device_tracker")
                ),
                vol.Required(CONFIG_FIELDS["binary_sensor"]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Required(CONFIG_FIELDS["distance_unit"], default="km"): (
                    selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                {"value": "km", "label": "Kilometers (km)"},
                                {"value": "mi", "label": "Miles (mi)"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                ),
                vol.Required(CONFIG_FIELDS["create_daily_utility_meter"], default=False): (
                    selector.BooleanSelector()
                ),
                vol.Required(CONFIG_FIELDS["create_weekly_utility_meter"], default=False): (
                    selector.BooleanSelector()
                ),
                vol.Required(CONFIG_FIELDS["create_monthly_utility_meter"], default=False): (
                    selector.BooleanSelector()
                ),
                vol.Required(CONFIG_FIELDS["create_daily_time_utility_meter"], default=False): (
                    selector.BooleanSelector()
                ),
                vol.Required(CONFIG_FIELDS["create_weekly_time_utility_meter"], default=False): (
                    selector.BooleanSelector()
                ),
                vol.Required(CONFIG_FIELDS["create_monthly_time_utility_meter"], default=False): (
                    selector.BooleanSelector()
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return DistanceTrackerOptionsFlow()


class DistanceTrackerOptionsFlow(config_entries.OptionsFlow):
    """Manage helpers associated with a Distance Tracker entry."""

    async def async_step_init(self, user_input=None):
        """Offer removal of utility meters linked to this distance sensor."""
        registry = entity_registry.async_get(self.hass)
        distance_sensor_entity_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            f"distance_tracker_{self.config_entry.entry_id}_distance",
        )
        time_sensor_entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"distance_tracker_{self.config_entry.entry_id}_time"
        )
        sensor_entity_ids = {
            entity_id
            for entity_id in (distance_sensor_entity_id, time_sensor_entity_id)
            if entity_id is not None
        }
        meter_entries = [
            entry
            for entry in self.hass.config_entries.async_entries(UTILITY_METER_DOMAIN)
            if entry.options.get("source", entry.data.get("source"))
            in sensor_entity_ids
        ]
        meter_cycles_by_source = {
            source_entity_id: {
                entry.options.get("cycle")
                for entry in meter_entries
                if entry.options.get("source", entry.data.get("source"))
                == source_entity_id
            }
            for source_entity_id in sensor_entity_ids
        }
        missing_meter_fields = {
            **{
                field: cycle
                for field, cycle in DISTANCE_METER_FIELDS.items()
                if distance_sensor_entity_id is not None
                and cycle
                not in meter_cycles_by_source.get(distance_sensor_entity_id, set())
            },
            **{
                field: cycle
                for field, cycle in TIME_METER_FIELDS.items()
                if time_sensor_entity_id is not None
                and cycle
                not in meter_cycles_by_source.get(time_sensor_entity_id, set())
            },
        }

        if user_input is not None:
            selected_distance_cycles = [
                cycle
                for field, cycle in missing_meter_fields.items()
                if field in DISTANCE_METER_FIELDS
                if user_input.get(field, False)
            ]
            selected_time_cycles = [
                cycle
                for field, cycle in missing_meter_fields.items()
                if field in TIME_METER_FIELDS
                if user_input.get(field, False)
            ]
            if selected_time_cycles and time_sensor_entity_id is None:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_data_schema(
                        meter_entries, missing_meter_fields
                    ),
                    errors={"base": "time_sensor_not_found"},
                    description_placeholders={"meter_count": str(len(meter_entries))},
                )
            if selected_distance_cycles and distance_sensor_entity_id is None:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._get_data_schema(
                        meter_entries, missing_meter_fields
                    ),
                    errors={"base": "distance_sensor_not_found"},
                    description_placeholders={"meter_count": str(len(meter_entries))},
                )

            selected_ids = set(user_input.get(UTILITY_METERS_FIELD, []))
            for meter_entry in meter_entries:
                if meter_entry.entry_id in selected_ids:
                    await self.hass.config_entries.async_remove(meter_entry.entry_id)

            sensor_name = (
                self.config_entry.data.get("sensor_name")
                or f"{self.config_entry.title} Afstand"
            )
            if selected_distance_cycles:
                await async_create_utility_meters(
                    self.hass,
                    distance_sensor_entity_id,
                    sensor_name,
                    "Distance travelled",
                    selected_distance_cycles,
                )

            if selected_time_cycles:
                await async_create_utility_meters(
                    self.hass,
                    time_sensor_entity_id,
                    sensor_name,
                    "Time traveled",
                    selected_time_cycles,
                )

            return self.async_create_entry(
                title="", data=dict(self.config_entry.options)
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self._get_data_schema(meter_entries, missing_meter_fields),
            description_placeholders={"meter_count": str(len(meter_entries))},
        )

    def _get_data_schema(self, meter_entries, missing_meter_fields):
        """Build options for removing meters and creating missing meters."""
        meter_options = [
            {
                "value": entry.entry_id,
                "label": (
                    f"{entry.options.get('cycle', 'Utility meter').title()} - "
                    f"{entry.title}"
                ),
            }
            for entry in meter_entries
        ]
        data_schema = vol.Schema(
            {
                vol.Optional(UTILITY_METERS_FIELD, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=meter_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                **{
                    vol.Optional(field, default=False): selector.BooleanSelector()
                    for field in missing_meter_fields
                },
            }
        )
        return data_schema
