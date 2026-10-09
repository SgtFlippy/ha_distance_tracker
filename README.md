# ha_distance_tracker
The integration also creates a cumulative time sensor that counts how long the selected binary sensor is on. It reports seconds as a duration and restores its accumulated total after a restart. Time while Home Assistant is stopped is not counted.

During setup, independently choose whether to create daily, weekly, and/or monthly Utility Meter helpers for distance and for time. Each selected helper is created as a standard Home Assistant Utility Meter.

For an existing installation, use the integration's Configure screen to create any missing daily, weekly, or monthly time helpers. The same screen can remove selected distance or time utility meters.

The distance sensor is grouped under its own Home Assistant device. Utility Meter helpers created from it are associated with that same device.

During setup, select a `device_tracker` entity and a `binary_sensor` entity from the dropdowns, then enter the name to use for the distance sensor. Each dropdown is filtered to show entities of the appropriate type that are available in your Home Assistant instance.

During setup, choose whether distance should be reported in kilometers or miles. The distance sensor and its Utility Meter helpers use the selected unit.

A quick vibe coded integration to track a person when connected to a certain device. It asks for the device to track and a binary sensor which needs to be on to start tracking.

You can create a helper binary sensor for when connected to a certain bluetooth device (in my case a bike) to start tracking the distance while connected.

With the created sensor, you can create utility sensors for tracking daily, weekly, monthly travelled kilometers.
