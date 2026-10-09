import logging
import math
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfLength
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

_LOGGER = logging.getLogger(__name__)

DOMAIN = "distance_tracker"
MIN_ACCURACY = 25
MIN_DISTANCE = 0.005
UTILITY_METER_OPTIONS = {
    "create_daily_utility_meter": "daily",
    "create_weekly_utility_meter": "weekly",
    "create_monthly_utility_meter": "monthly",
}

def haversine(lon1, lat1, lon2, lat2):
    rad_earth = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return rad_earth * c

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform from a config entry."""
    config = entry.data
    tracker_entity = config.get("device_tracker")
    bluetooth_entity = config.get("binary_sensor")
    utility_meter_cycles = tuple(
        cycle
        for option, cycle in UTILITY_METER_OPTIONS.items()
        if config.get(option, False)
    )
    sensor_name = config.get("sensor_name") or f"{entry.title} Afstand"
    
    async_add_entities(
        [
            DistanceSensor(
                entry.entry_id,
                sensor_name,
                tracker_entity,
                bluetooth_entity,
                utility_meter_cycles,
            )
        ],
        True,
    )

class DistanceSensor(RestoreEntity, SensorEntity):
    """Sensor tracking total distance using breadcrumbs and UI config."""

    def __init__(
        self, entry_id, sensor_name, tracker_entity, bluetooth_entity, utility_meter_cycles
    ):
        self._entry_id = entry_id
        self._tracker_entity = tracker_entity
        self._bluetooth_entity = bluetooth_entity
        self._utility_meter_cycles = utility_meter_cycles
        
        self._attr_name = sensor_name
        self._attr_unique_id = f"distance_tracker_{entry_id}_distance"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=sensor_name,
            manufacturer="Distance Tracker",
        )
        self._attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_icon = "mdi:map-marker-distance"
        self._state = 0.0
        self._last_lat = None
        self._last_lon = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        await self._async_create_utility_meters()
        
        old_state = await self.async_get_last_state()
        if old_state is not None and old_state.state not in (None, "unknown", "unavailable"):
            try:
                self._state = float(old_state.state)
            except ValueError:
                self._state = 0.0

        # Listen for reset event specific to this entry
        self.async_on_remove(
            self.hass.bus.async_listen(f"distance_tracker_reset_{self._entry_id}", self._handle_reset_event)
        )

        # Listen for tracker changes
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._tracker_entity], self._async_tracker_changed
            )
        )

    async def _async_create_utility_meters(self):
        """Create the selected Home Assistant utility meter helpers."""
        entries = self.hass.config_entries.async_entries("utility_meter")

        for cycle in self._utility_meter_cycles:
            meter_name = f"{self.name} {cycle}"
            if any(
                entry.title == meter_name
                and entry.options.get("source") == self.entity_id
                and entry.options.get("cycle") == cycle
                for entry in entries
            ):
                continue

            result = await self.hass.config_entries.flow.async_init(
                "utility_meter",
                context={"source": "user"},
                data={
                    "name": meter_name,
                    "source": self.entity_id,
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
                    "Could not create %s utility meter for %s: %s",
                    cycle,
                    self.entity_id,
                    result,
                )

    @property
    def native_value(self):
        return round(self._state, 2)

    async def _handle_reset_event(self, event):
        self._state = 0.0
        self._last_lat = None
        self._last_lon = None
        self.async_write_ha_state()

    async def _async_tracker_changed(self, event):
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unknown", "unavailable"):
            return

        bt_state = self.hass.states.get(self._bluetooth_entity)
        if bt_state is None or bt_state.state != "on":
            self._last_lat = None
            self._last_lon = None
            return

        attrs = new_state.attributes
        lat = attrs.get("latitude")
        lon = attrs.get("longitude")
        accuracy = attrs.get("gps_accuracy", 0)

        if lat is None or lon is None or accuracy > MIN_ACCURACY:
            return

        if self._last_lat is not None and self._last_lon is not None:
            distance_segment = haversine(self._last_lon, self._last_lat, lon, lat)
            if distance_segment > MIN_DISTANCE:
                self._state += distance_segment
                self.async_write_ha_state()

        self._last_lat = lat
        self._last_lon = lon
