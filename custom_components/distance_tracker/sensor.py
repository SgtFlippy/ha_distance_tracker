from datetime import timedelta
import logging
import math
from time import monotonic

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfTime
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .helpers import async_create_utility_meters

_LOGGER = logging.getLogger(__name__)

DOMAIN = "distance_tracker"
MIN_ACCURACY = 25
MIN_DISTANCE = 0.005
UTILITY_METER_OPTIONS = {
    "create_daily_utility_meter": "daily",
    "create_weekly_utility_meter": "weekly",
    "create_monthly_utility_meter": "monthly",
}
TIME_UTILITY_METER_OPTIONS = {
    "create_daily_time_utility_meter": "daily",
    "create_weekly_time_utility_meter": "weekly",
    "create_monthly_time_utility_meter": "monthly",
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
    time_utility_meter_cycles = tuple(
        cycle
        for option, cycle in TIME_UTILITY_METER_OPTIONS.items()
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
            ),
            TimeSpentSensor(
                entry.entry_id,
                f"{sensor_name} Time Spent",
                bluetooth_entity,
                time_utility_meter_cycles,
            ),
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
        await async_create_utility_meters(
            self.hass, self.entity_id, self.name, self._utility_meter_cycles
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


class TimeSpentSensor(RestoreEntity, SensorEntity):
    """Track cumulative time while the configured binary sensor is on."""

    def __init__(self, entry_id, sensor_name, binary_sensor, utility_meter_cycles):
        self._entry_id = entry_id
        self._binary_sensor = binary_sensor
        self._utility_meter_cycles = utility_meter_cycles
        self._accumulated_seconds = 0.0
        self._tracking_started = None

        self._attr_name = sensor_name
        self._attr_unique_id = f"distance_tracker_{entry_id}_time"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=sensor_name.removesuffix(" Time Spent"),
            manufacturer="Distance Tracker",
        )
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        self._attr_icon = "mdi:timer-outline"

    async def async_added_to_hass(self):
        """Restore accumulated time and start tracking if currently active."""
        await super().async_added_to_hass()

        old_state = await self.async_get_last_state()
        if old_state is not None and old_state.state not in (
            None,
            "unknown",
            "unavailable",
        ):
            try:
                self._accumulated_seconds = float(old_state.state)
            except ValueError:
                _LOGGER.warning("Could not restore time sensor state %s", old_state.state)

        binary_state = self.hass.states.get(self._binary_sensor)
        if binary_state is not None and binary_state.state == "on":
            self._tracking_started = monotonic()

        await async_create_utility_meters(
            self.hass,
            self.entity_id,
            self.name,
            self._utility_meter_cycles,
        )

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._binary_sensor], self._async_binary_sensor_changed
            )
        )
        self.async_on_remove(
            async_track_time_interval(
                self.hass, self._async_update, timedelta(seconds=30)
            )
        )
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"distance_tracker_reset_{self._entry_id}", self._async_reset
            )
        )

    @property
    def native_value(self):
        """Return total time in seconds."""
        total = self._accumulated_seconds
        if self._tracking_started is not None:
            total += monotonic() - self._tracking_started
        return round(total, 2)

    async def _async_binary_sensor_changed(self, event):
        """Start or stop accumulating time when tracking is toggled."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.state == "on":
            if self._tracking_started is None:
                self._tracking_started = monotonic()
        elif self._tracking_started is not None:
            self._accumulated_seconds += monotonic() - self._tracking_started
            self._tracking_started = None

        self.async_write_ha_state()

    async def _async_update(self, now):
        """Refresh the displayed duration while tracking is active."""
        if self._tracking_started is not None:
            self.async_write_ha_state()

    async def _async_reset(self, event):
        """Reset accumulated time when the integration reset service is called."""
        self._accumulated_seconds = 0.0
        binary_state = self.hass.states.get(self._binary_sensor)
        self._tracking_started = (
            monotonic() if binary_state is not None and binary_state.state == "on" else None
        )
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Persist elapsed time before the entity is unloaded."""
        if self._tracking_started is not None:
            self._accumulated_seconds += monotonic() - self._tracking_started
            self._tracking_started = None
            self.async_write_ha_state()
        await super().async_will_remove_from_hass()
