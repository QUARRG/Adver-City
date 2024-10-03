# Overview

Adver-City was built with [CARLA v0.9.12](https://carla.readthedocs.io/en/0.9.12/) and 
[OpenCDA](https://opencda-documentation.readthedocs.io/en/latest/). If you wish to make any modifications to Adver-City,
please make sure to check the documentation for CARLA and OpenCDA beforehand, to get acquainted to how they work and
get a good understanding of how to make modifications.

On top of OpenCDA's original scenario generation code, Adver-City introduces the following features:

* Traffic Light Manager (allowing traffic light timings to be controlled),
  * `Dataset\Scripts\managers\WalkerManager.py`
* Walker Manager (spawns pedestrians in desired areas of the map),
  * `Dataset\Scripts\managers\TrafficLightManager.py`
* Semantic Camera Sensor (positioned in the same location as the RGB Cameras),
  * `Dataset\Scripts\sensors\SemanticCameraSensor.py`
* GNSS & IMU data dumping (saving data from these sensors to YAML files),
  * `Dataset\Scripts\managers\RevampedDataDumper.py` -> `save_gnss_imu()`
* Vehicle lights (the lights for all vehicles are activated),
  * `Dataset\Scripts\scenario_runner.py` -> `turn_on_vehicle_lights()`
* Vehicle spawning with parameterized object density around CAV paths, as well as CAV and RSU positions (spawns vehicles 
in a rectangular area surrounding these locations),
  * `Dataset\Scripts\scenario_runner.py` -> `add_spawn_from_density()`
* Detailed weather settings (includes more weather parameters for greater weather variation),
  * `Dataset\Scripts\scenario_runner.py` -> `get_weather_from_config()`
* Detailed RGB Camera settings (includes more sensor parameters for more detailed sensor configuration),
  * `Dataset\Scripts\sensors\CameraSensor.py`
* Script to generate all scenarios iteratively (managing the CARLA server and iterating through scenario 
configurations),
  * `main.py`
* Video generation (saves an MP4 video of the frontal RGB cameras for each viewpoint)
  * `generate_video.py`
* Scenario summary creation (stores from each frame's bounding boxes for faster generation of statistics),
  * `generate_summary.py`
* Statistics calculation script (from summary files, generates plots and a CSV table).
  * `generate_statistics.py`
  * `Dataset\Scripts\utils\stats.py`

Each one of these features is documented in their respective files, so here we will talk about the logic behind Scenario 
iteration, which involves multiple files and folders within the project structure.


## Scenario iteration

The `main.py` script loads the scenario configuration files and merges each type of configuration to create the specific
configuration of each scenario to be generated. Each type of configuration (`scenarios`, `weather` and `density`) has an
`Enum` with the full name of the configuration (say, `rural_straight_non_junction`) and an abbreviation to be used in
folders and file names (say, `rsnj`).

First, the `default.yaml` configuration is loaded, which has default settings for all scenario values. Most of the 
parameters in this file are used by OpenCDA and are similar for all Adver-City scenarios.

Then, the `scenario` YAML files are loaded and merged into the `default.yaml` configuration. If a specific scenario is 
being generated (say, `urban_intersection`), then only that file will be loaded and the merged configuration will be 
stored in the `scenario_configs` list. Otherwise, all 5 scenarios will be loaded and merged with the default 
configuration, having their data stored in the `scenario_configs` list. Therefore, if a single scenario is loaded, the
`scenario_configs` list will have a single element, otherwise it will have five.

Next, the `weather` YAML files are loaded and merged with the elements within `scenario_configs` list. If a specific 
weather condition has been chosen, then only the YAML file for that weather condition will be loaded and merged with 
the scenario configurations, storing the results in the `weather_configs` list. Otherwise, if all 11 weather 
configurations are being simulated, then each one of them will be loaded, merged with all configurations in the 
`scenario_configs` list and stored in the `weather_configs` list. If all scenarios and all weather configurations have
been loaded so far, the `weather_configs` list will have 55 elements.

Finally, the `density` YAML files are loaded and merged with each element from the `weather_configs` list. Again, if 
only a single density has been chosen, only that file will be loaded, otherwise all density files will be loaded. After
merging, the results are stored in the `simulation_configs` list, which is then iterated to generate the dataset 
scenarios with the `Dataset\Scripts\scenario_runner.py` script.

If you wish to include a new type of configuration (say, `sensor_placement`) to be used for scenario generation, make 
sure to:
* Create an Enum for the configuration (`SensorPlacements`),
* Create an Enum for its abbreviations (`SensorPlacementAbbreviations`),
* A folder in the `Dataset\Configs` folder (`\SensorPlacements`),
* Another loop to load all configurations and merge them with the previous settings on the `load_simulation_configs()`
method.

Remember that whenever YAML configurations are merged, if a value is present in both, the new configuration will 
overwrite the older one.

The iteration loop within the `main.py` script manages the CARLA server, killing it after every few simulations to avoid
segmentation fault errors that sometimes happen with CARLA. **Make sure to check if the path to CARLA in the 
`init_carla()` function is correct.** The iteration loop also accounts for common execution bugs with the simulator,
such as errors spawning walkers or simulations that end up running indefinitely.

## Other tutorials

* [Data structure](data_structure.md)
* [Annotations](annotations.md)
* [Scenarios](scenarios.md)