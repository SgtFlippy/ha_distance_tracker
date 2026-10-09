import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry, selector

DOMAIN = "distance_tracker"
UTILITY_METER_DOMAIN = "utility_meter"
CONFIG_FIELDS = {
    "device_tracker": "Choose the device to track",
    "binary_sensor": "Choose the binary sensor that needs to be on to track",
    "create_daily_utility_meter": "Create daily utility meter (resets every day)",
    "create_weekly_utility_meter": "Create weekly utility meter (resets every week)",
    "create_monthly_utility_meter": "Create monthly utility meter (resets every month)",
    "sensor_name": "Name for the distance sensor",
}
UTILITY_METERS_FIELD = "Select utility meters to delete (unchecked meters are kept)"

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
                title=f"Distance Tracker ({data['device_tracker'].split('.')[-1]})",
                data=data
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONFIG_FIELDS["device_tracker"]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="device_tracker")
                ),
                vol.Required(CONFIG_FIELDS["binary_sensor"]): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
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
                vol.Required(CONFIG_FIELDS["sensor_name"]): selector.TextSelector(),
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
        sensor_entity_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            f"distance_tracker_{self.config_entry.entry_id}_distance",
        )
        meter_entries = [
            entry
            for entry in self.hass.config_entries.async_entries(UTILITY_METER_DOMAIN)
            if sensor_entity_id is not None
            and entry.options.get("source", entry.data.get("source"))
            == sensor_entity_id
        ]

        if user_input is not None:
            selected_ids = set(user_input.get(UTILITY_METERS_FIELD, []))
            for meter_entry in meter_entries:
                if meter_entry.entry_id in selected_ids:
                    await self.hass.config_entries.async_remove(meter_entry.entry_id)

            return self.async_create_entry(
                title="", data=dict(self.config_entry.options)
            )

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
                )
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={"meter_count": str(len(meter_entries))},
        )
