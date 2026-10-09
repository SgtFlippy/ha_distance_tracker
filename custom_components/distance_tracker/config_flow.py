import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

DOMAIN = "distance_tracker"

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
