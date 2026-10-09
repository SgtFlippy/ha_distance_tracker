import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

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

        DATA_SCHEMA = vol.Schema({
            vol.Required("device_tracker", default="device_tracker."): str,
            vol.Required("binary_sensor", default="binary_sensor."): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )
