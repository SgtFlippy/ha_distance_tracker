import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry, selector

DOMAIN = "distance_tracker"
UTILITY_METER_DOMAIN = "utility_meter"

class DistanceTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Distance Tracker."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=f"Distance Tracker ({user_input['device_tracker'].split('.')[-1]})",
                data=user_input
            )

        data_schema = vol.Schema(
            {
                vol.Required("device_tracker"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="device_tracker")
                ),
                vol.Required("binary_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor")
                ),
                vol.Required("create_daily_utility_meter", default=False): (
                    selector.BooleanSelector()
                ),
                vol.Required("create_weekly_utility_meter", default=False): (
                    selector.BooleanSelector()
                ),
                vol.Required("create_monthly_utility_meter", default=False): (
                    selector.BooleanSelector()
                ),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return DistanceTrackerOptionsFlow(config_entry)


class DistanceTrackerOptionsFlow(config_entries.OptionsFlow):
    """Manage helpers associated with a Distance Tracker entry."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

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
            selected_ids = set(user_input.get("utility_meters", []))
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
                vol.Optional("utility_meters", default=[]): selector.SelectSelector(
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
