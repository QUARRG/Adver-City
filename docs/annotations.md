# Annotations

Adver-City follows an annotation schema compatible with OPV2V. However, due to changes in sensors, there are some minor
differences.

For each viewpoints' folder, each frame has a YAML file with data taken directly from the CARLA server. The data within 
it is organized as follows:

```yaml
RSU: false # if this agent is an RSU or not
camera0: # parameters for the frontal camera
  cords: # camera coordinates under CARLA map coordinates
  - 213.1973419189453 # x
  - -5.52460241317749 # y
  - 1.483937382698059 # z
  - -0.00433349609375 # roll
  - -174.12957763671875 # yaw
  - -0.2315092533826828 # pitch
  extrinsic: # extrinsic matrix from camera to lidar
  - - 1.0
    - -2.1286936818054485e-17
    - -7.180017982536492e-20
    - -0.9500086905572118
  - - -4.959221109941733e-18
    - 0.9999999999999998
    - -4.757742642355514e-20
    - 1.0234670639874821e-06
  - - -4.90559482280122e-19
    - 6.599812935430275e-20
    - 1.0
    - 0.44999985330774583
  - - 0.0
    - 0.0
    - 0.0
    - 1.0
  intrinsic: # camera intrinsic matrix
  - - 805.5356459301888
    - 0.0
    - 960.0
  - - 0.0
    - 805.5356459301888
    - 540.0
  - - 0.0
    - 0.0
    - 1.0
camera1: ... # parameters for right camera
camera2: ... # parameters for left camera
camera3: ... # parameters for back camera
ego_speed: 0.1760935088021043 # speed of this agent in km/h
lidar_pose: # lidar pose under CARLA coordinates
- 214.1405487060547 # x
- -5.427590370178223 # y
- 1.9377721548080444 # z
- -0.00433349609375 # roll
- -174.12957763671875 # yaw
- -0.2315092533826828 # pitch
plan_trajectory: # list of locations to be followed by this agent, as defined by the path planning algorithm
- - 212.44387817382812 # x
  - -5.307567596435547 # y
  - 9.429222033557476 # z
- - 211.8439483642578
  - -5.316528797149658
  - 9.429222033557476
- - 211.04403686523438
  - -5.328477382659912
  - 9.429222033557476
- ...
predicted_ego_pos: # agent`s localization from GNSS
- 213.65081787109375 # x
- -5.478086948394775 # y
- 0.0357675738632679 # z
- -0.00433349609375 # roll
- -174.12957763671875 # yaw
- -0.2315092533826828 # pitch
true_ego_pos: # true position of this agent
- 213.65081787109375 # x
- -5.478086948394775 # y
- 0.0357675738632679 # z
- -0.00433349609375 # roll
- -174.12957763671875 # yaw
- -0.2315092533826828 # pitch
vehicles: # list of vehicles within line of sight of this agent
  1554: # id of the perceived vehicle
    angle: # under CARLA map coordinate system 
    - 0.00028235220815986395 # roll
    - 0.8933372497558594 # yaw
    - -0.032047245651483536 # pitch
    bp_id: vehicle.lincoln.mkz_2017 # blueprint id for this vehicle, from CARLA
    center: # relative position from the center of the bounding box to the frontal axis of the vehicle
    - 0.004043583292514086 # x
    - 7.466280038670448e-08 # y
    - 0.7188605070114136 # z
    class: car # class/category of this object. Adver-City has 6 classes: car, van, truck, motorcycle, bicycle and pedestrian
    color: 0, 0, 255 # integer r, g, b values for this vehicle
    dist: 94.9173812866211 # distance from the agent, in meters
    extent: # half length, width and height of the vehicle, in meters
    - 2.4508416652679443
    - 1.0641621351242065
    - 0.7553732395172119
    location: # position of the center in the frontal axis of the vehicle under CARLA map coordinate system
    - 119.29178619384766 # x
    - 4.802069187164307 # y
    - 0.0340358167886734 # z
    relative_angle: 175.0229148864746 # relative angle to the agent
    speed: 12.787282262180959 # speed of the vehicle, in km/h, in relation to the world (not in relation to the agent)
  1568: ...
  1608: ...
walkers: # list of pedestrians within line of sight of this agent
  1300:
    angle: # under CARLA map coordinate system 
    - 0.0 # roll
    - -0.6118773818016052 # yaw
    - 0.0 # pitch
    bp_id: walker.pedestrian.0024 # blueprint id for this pedestrian, from CARLA
    class: walker # class/category of this object. For pedestrians, it is always `walker`
    dist: 58.161373138427734
    extent: # half length, width and height of the pedestrian, in meters
    - 0.18767888844013214
    - 0.18767888844013214
    - 0.9300000071525574
    location: # position of the center in the frontal axis of the vehicle under CARLA map coordinate system
    - 159.15383911132812 # x
    - 14.811898231506348 # y
    - 1.1038998365402222 # z
    relative_angle: 173.51770025491714 # relative angle to the agent
    speed: 5.411598565237392 # speed of the pedestrian, in km/h, in relation to the world (not in relation to the agent)
  1318: ...
  1322: ...
```

## Other tutorials

* [Overview](overview.md)
* [Data structure](data_structure.md)
* [Scenarios](scenarios.md)