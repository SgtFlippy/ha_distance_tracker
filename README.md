# ha_distance_tracker
This integration is fully vibe coded, so credit is not to me, neither any weird coding or mistakes.
It was made because I couldn't find an integration that could reliably measure my distance travelled by bike. They either rely on time travelled and HA-distance (which is off, since HA-distance is a straight line) or takes the coördinates from point A and B and then takes those to calculate the route on a map (which is also off, since it doesn't know what route you took or maybe doesn't know all bicycle paths).

This integration calculates distance travelled by constantly tracking the device and adding up the distance between every point of position update. It works best when you activate high accuracy mode in the companion app, while connected to the same sensor the integration uses to activate.

Examples: 
I track my bicycle for my commute, the sensor is a template sensor when my phone's bluetooth is connected to my bicycle.
I track my cars, the sensor is a template sensor when my phone's connected to the Android Auto of the specific car.
