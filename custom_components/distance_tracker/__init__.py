import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

DOMAIN = "distance_tracker"
PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """YAML setup is niet meer nodig, we retourneren True."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Stel de integratie in vanuit een UI config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Registreer de reset-actie
    async def handle_reset(call):
        hass.bus.async_fire(f"distance_tracker_reset_{entry.entry_id}")

    hass.services.async_register(DOMAIN, "reset_tracker", handle_reset)

    # Stuur door naar het sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Verwijder de integratie netjes via de UI."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
sib