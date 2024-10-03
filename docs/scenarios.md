# Scenarios

Each Adver-City scenario is set up from merging 4 configuration files: `default.yaml`, a scenario configuration file,
a weather configuration file, and a density configuration file.

The `default.yaml` configuration is shared across all Adver-City scenarios, so its values do not change for different 
scenarios and most of them are actually used by OpenCDA classes. For more information on how it is structured, please
refer to [OpenCDA's documentation](https://opencda-documentation.readthedocs.io/en/latest/md_files/yaml_define.html).

Here we will cover the configuration files used by Adver-City to create its diverse scenarios.

### Scenario configuration file

The scenario configuration file is used to configure object placement in the scene. 

```yaml
town: Town03  # CARLA Town map used for this scenario

dataset_config:
  scenario: "urban_intersection"  # label
  scenario_abbreviation: "ui"  # abbreviated label

world:
  seed: 18 # seed for numpy and random
  seed_traffic: 4 # seed for traffic
  weather:
    mie_scattering_scale: 0.05  # refers to air pollution and how light is influenced by it

scenario:
  num_vehicles: 6 # Number of vehicles per spawn point range (8 spawn point ranges are used)
  num_walkers: 60 # Total number of pedestrians spawned
  rsu_list:
    - name: rsu1
      spawn_position: [3.84, 119.13, 6.45, 0.0, 88, -18] # x, y, z, roll, yaw, pitch
      id: -1
      wall_facing: False
      sensing:
        perception:
          lidar:
            upper_fov: -1  # overrides standard value for the upper fov, since this rsu is elevated
    - name: rsu2
      spawn_position: [-7.86, 143.43, 6.59, 0.0, -91.9, -10.57] # x, y, z, roll, yaw, pitch
      id: -2
      wall_facing: False
      sensing:
        perception:
          lidar:
            upper_fov: -1

  single_cav_list:
    - name: cav1
      spawn_position: [-6.44, 46.45, 0.3, 0, 90.42, 0] # x, y, z, roll, yaw, pitch
      destination: [64.96, 134.08, 0.3] # x, y, z
    - name: cav2
      spawn_position: [90.8, 129.10, 0.3, 0.0, 178.58, 0] # x, y, z, roll, yaw, pitch
      destination: [-141.34, -96.32, 0.3] # x, y, z
    - name: cav3
      spawn_position: [-64.20, 135.71, 0.3, 0.0, -0.85, 0] # x, y, z, roll, yaw, pitch
      destination: [247.51, -81.3, 0.3] # x, y, z

  traffic_lights:  # configuration for the TrafficLightManager
    active_light_id: 2  # sets which traffic light in the intersection is active in the beginning of the simulation
    active_light_state: "g"  #'y', 'r' or 'g', not case-sensitive. Check TrafficLightManager for further info
    initial_active_frame_counter: 20  # starting value for the active light's frame counter
    distinct_lights:  # used to control a traffic light not in the intersection, but that affects intersection traffic
      - location: [-63.52, 128.21, 4.15]

vehicle_base:  # overrides behavior configuration from the default.yaml file
  behavior:
    max_speed: 35
    tailgate_speed: 40
  controller:
    max_throttle: 0.9

blueprint:
  bp_class_sample_prob:  # during spawning, these probabilities are used to select the vehicles to be spawned
    car: 0.52
    van: 0.16
    truck: 0.16
    bicycle: 0.08
    motorcycle: 0.08
```

### Weather configuration file

The weather configuration file defines the parameters used for CARLA's WeatherParameters object. Therefore, all of the
parameter used refer to instance variables of the carla.WeatherParameters class. For explanations of what each value
means, please refer to 
[CARLA's documentation](https://carla.readthedocs.io/en/0.9.12/python_api/#carlaweatherparameters).

```yaml
world:
  weather:
    cloudiness: 100
    fog_density: 100
    wetness: 5
    precipitation_deposits: 0
    fog_distance: 0
    fog_falloff: 0
    precipitation: 0
    wind_intensity: 0
    sun_altitude_angle: -90
    rayleigh_scattering_scale: 0.02
    scattering_intensity: 1

dataset_config:
  weather: "foggy_night"
  weather_abbreviation: "fn"
```

The Glare Day weather configuration file follows a slightly different structure, since its `sun_altitude_angle` and
`sun_azimuth_angle` change according to the road configuration. As such, these values are actually stored as 
dictionaries, with each road configuration having a unique value.

```yaml
world:
  weather:
    cloudiness: 0
    fog_density: 8
    wetness: 0
    precipitation_deposits: 0
    fog_distance: 0.75
    fog_falloff: 0.2
    precipitation: 0
    wind_intensity: 0
    sun_altitude_angle: 20  # ScenarioManager uses this value before override happens, so a dummy value must be used
    sun_altitude_angle_scenarios:  # Angles set to the lowest possible value that does not occlude sun from ego view
      ui: 8
      unj: 5
      ri: 10
      rsnj: 11
      rcnj: 22
    rayleigh_scattering_scale: 0.02
    scattering_intensity: 1
    sun_azimuth_angle:  # Azimuth set so that sunlight hits straight onto ego's path
      ui: 271
      unj: 1.3  # Decimal value due to ego's lane change
      ri: 90
      rsnj: 90
      rcnj: 100
    mie_scattering_scale: 0

dataset_config:
  weather: "glare_day"
  weather_abbreviation: "gd"
```

### Density configuration file

The density configuration file simply defines the multiplication factor used by dense scenes in relation to sparse 
scenes.

```yaml
density:
  vehicle_multiplier: 2.67  # Multiplies "scenario" -> "num_vehicles"
  walker_multiplier: 2.33  # Multiplies "scenario" -> "num_walkers"

dataset_config:
  density: "dense"
  density_abbreviation: "d"
```

* The walker multiplier used is smaller than the vehicle multiplier because pedestrians have a smaller area within the
map that they can be spawned at. Therefore, we can use a smaller number of pedestrians than vehicles and have the
sidewalks just as crowded as the roads.