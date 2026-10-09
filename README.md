# ha_distance_tracker
During setup, select a `device_tracker` entity and a `binary_sensor` entity from the dropdowns. Each dropdown is filtered to show entities of the appropriate type that are available in your Home Assistant instance.

A quick vibe coded integration to track a person when connected to a certain device. It asks for the device to track and a binary sensor which needs to be on to start tracking.

You can create a helper binary sensor for when connected to a certain bluetooth device (in my case a bike) to start tracking the distance while connected.

With the created sensor, you can create utility sensors for tracking daily, weekly, monthly travelled kilometers.
