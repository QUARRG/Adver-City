# Data structure

The folder and file structure is as follows:

```sh
Adver-City  # root of project
├───data_dumping 
│    ├──2024_07_12_14_13_22  # timestamp of scenario generation
│    │   ├──unj_cn_d  # scenario label
│    │   │  ├──data_protocol.yaml  # merged configuration of all configuration YAMLs used for this scenario
│    │   │  ├──summary.yaml  # summary file of the scenario, used to quickly generate statistics
│    │   │  ├──698  # each CAV's folder is named after the object id it is assigned in CARLA
│    │   │  │  ├──000060.yaml  # ground truth file with information on frame 60 (frame count starts at 60)
│    │   │  │  ├──000060_camera0.png  # frontal RGB camera 
│    │   │  │  ├──000060_camera1.png  # right RGB camera 
│    │   │  │  ├──000060_camera2.png  # left RGB camera 
│    │   │  │  ├──000060_camera3.png  # back RGB camera 
│    │   │  │  ├──000060_semantic0.png  # frontal semantic camera
│    │   │  │  ├──000060_semantic1.png  # right semantic camera
│    │   │  │  ├──000060_semantic2.png  # left semantic camera
│    │   │  │  ├──000060_semantic3.png  # back semantic camera 
│    │   │  │  ├──000060_lidar.ply  # point cloud file 
│    │   │  │  ├──000060_gnss_imu.yaml  # gnss and imu data (only available for vehicles) 
```

Some notes regarding the folder structure:

* Each timestamp folder contains the folders for all scenarios generated when `main.py` was executed. Also, if the 
statistics script was executed, a `stats` folder will also appear, with the statistics files within it.

```sh
Adver-City
├───data_dumping 
│    ├──2024_07_12_14_13_22  
│    │   ├──stats
│    │   │  ├──class_histogram.pdf
│    │   │  ├──densiy_by_range_to_ego.pdf
│    │   │  ├──num_frames_per_ego_speed.pdf
│    │   │  ├──num_keyframes_per_num_annotations.pdf
│    │   │  ├──polar_density_map.pdf
│    │   │  ├──stats.csv
│    │   │  ├──time_of_day.pdf
│    │   │  ├──vehicles_per_speed.pdf
│    │   │  ├──weather.pdf
│    │   ├──unj_cn_d  
│    │   ├──unj_cn_s  
│    │   ├──unj_cd_d  
│    │   ├──unj_cn_s  
```

* Each scenario has a folder for each viewpoint. Adver-City's scenarios all have 2 RSUs (which always have negative ids)
and 3 CAVs (whose folders are named after their CARLA object id).

```sh
Adver-City  # root of project
├───data_dumping 
│    ├──2024_07_12_14_13_22  
│    │   ├──unj_cn_d  
│    │   │  ├──698  # ego vehicle (the first folder is always the ego)
│    │   │  ├──712  # first vehicle
│    │   │  ├──726  # second vehicle
│    │   │  ├──-1  # first RSU
│    │   │  ├──-2  # second RSU
```

* Each frame will generate 11 files within the viewpoint's folder. As such, 55 files are saved for every frame executed
in the simulation, which naturally causes CARLA to run significantly slower than usual during data dumping.
* Frame count starts at 60 since the initial frames of the simulation are not saved to avoid unusual after-spawning 
behavior.