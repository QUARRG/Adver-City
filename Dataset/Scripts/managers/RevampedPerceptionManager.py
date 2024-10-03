import sys
import weakref
import cv2
import numpy as np
from opencda.core.common.misc import cal_distance_angle
from opencda.core.sensing.perception.o3d_lidar_libs import o3d_visualizer_init, o3d_pointcloud_encode, o3d_visualizer_show
import opencda.core.sensing.perception.sensor_transformation as st
from opencda.core.sensing.perception.obstacle_vehicle import ObstacleVehicle
from opencda.core.sensing.perception.perception_manager import PerceptionManager, SemanticLidarSensor, LidarSensor
from Dataset.Scripts.sensors.CameraSensor import CameraSensor
from Dataset.Scripts.sensors.SemanticCameraSensor import SemanticCameraSensor


class RevampedPerceptionManager(PerceptionManager):
    """
    Revamped version of PerceptionManager, adding Semantic Cameras and considering Walkers among the objects to be
    detected in the scene
    """
    def __init__(self, vehicle, config_yaml, cav_world, carla_world=None, infra_id=None):
        """
        :param vehicle: carla.Vehicle
        :param config_yaml: dict
        :param cav_world: opencda.CavWorld
        :param carla_world: carla.world
        :param infra_id: int
        """
        self.vehicle = vehicle
        self.carla_world = carla_world if carla_world is not None else self.vehicle.get_world()
        self._map = self.carla_world.get_map()
        self.id = infra_id if infra_id is not None else vehicle.id

        self.activate = config_yaml["activate"]
        self.camera_visualize = config_yaml["camera"]["visualize"]
        self.camera_config = config_yaml["camera"]
        self.camera_num = config_yaml["camera"]["num"]
        self.lidar_config = config_yaml["lidar"]
        self.lidar_visualize = config_yaml["lidar"]["visualize"]
        self.global_position = config_yaml["global_position"] if "global_position" in config_yaml else None

        self.cav_world = weakref.ref(cav_world)()
        ml_manager = cav_world.ml_manager

        if self.activate:
            sys.exit("When you dump data, please deactivate the detection function for precise label.")

        if self.activate and not ml_manager:
            sys.exit("If you activate the perception module, then apply_ml must be set to true in the argument parser "
                     "to load the detection DL model.")
        self.ml_manager = ml_manager

        if self.activate or self.camera_visualize:
            self.rgb_camera = []
            self.semantic_cameras = []  # Semantic cameras will be added after
            mount_position = self.camera_config["positions"]
            assert len(mount_position) == self.camera_num, \
                "The camera number has to be the same as the length of the relative positions list"

            for i in range(self.camera_num):
                self.rgb_camera.append(
                    CameraSensor(vehicle, self.carla_world, mount_position[i], self.global_position, self.camera_config)
                )
        else:
            self.rgb_camera = None
            self.semantic_cameras = None

        # we only spawn the LiDAR when perception module is activated or lidar visualization is needed
        if self.activate or self.lidar_visualize:
            self.lidar = LidarSensor(vehicle, self.carla_world, config_yaml["lidar"], self.global_position)
            self.o3d_vis = o3d_visualizer_init(self.id)
        else:
            self.lidar = None
            self.o3d_vis = None

        self.data_dump = True
        self.semantic_lidar = SemanticLidarSensor(
                vehicle, self.carla_world, config_yaml["lidar"], self.global_position)

        # count how many steps have been passed
        self.count = 0
        self.ego_pos = None

        # the dictionary contains all objects
        self.objects = {}
        # traffic light detection related
        self.traffic_thresh = config_yaml["traffic_light_thresh"] if "traffic_light_thresh" in config_yaml else 50

    def add_semantic_cameras(self, data_dumper):
        """
        Creates instances of SemanticCameraSensors and adds them to the semantic_cameras list.

        :param data_dumper: RevampedDataDumper
        """
        if (self.activate or self.camera_visualize) and (data_dumper is not None):
            mount_position = self.camera_config["positions"]
            for i in range(self.camera_num):
                self.semantic_cameras.append(
                    SemanticCameraSensor(
                        self.vehicle, self.carla_world, mount_position[i], self.global_position, i,
                        self.camera_config, data_dumper
                    )
                )

    def detect(self, ego_pos):
        """
        Revamped version of PerceptionManager's detect method, adding walkers to the list of detected objects

        :param ego_pos: carla.Transform
        :return: list
        """
        self.ego_pos = ego_pos
        objects = {"vehicles": [],
                   "walkers": [],
                   "traffic_lights": []}

        world = self.carla_world

        vehicle_list = world.get_actors().filter("*vehicle*")
        walker_list = world.get_actors().filter("*walker*")
        thresh = 50 if not self.data_dump else self.lidar_config["range"]

        vehicle_list = [v for v in vehicle_list if self.dist(v) < thresh and v.id != self.id]
        walker_list = [w for w in walker_list if self.dist(w) < thresh]

        # use semantic lidar to filter out vehicles out of the range
        if self.data_dump:
            vehicle_list = self.filter_vehicle_out_sensor(vehicle_list)
            walker_list = self.filter_walker_out_sensor(walker_list)

        # convert carla.Vehicle to opencda.ObstacleVehicle if lidar visualization is required
        if self.lidar:
            vehicle_list = [
                ObstacleVehicle(None, None, v, self.lidar.sensor, self.cav_world.sumo2carla_ids)
                for v in vehicle_list
            ]
            walker_list = [
                ObstacleVehicle(None, None, w, self.lidar.sensor, self.cav_world.sumo2carla_ids)
                for w in walker_list
            ]
        else:
            vehicle_list = [
                ObstacleVehicle(None, None, v, None, self.cav_world.sumo2carla_ids)
                for v in vehicle_list
            ]
            walker_list = [
                ObstacleVehicle(None, None, w, self.lidar.sensor, self.cav_world.sumo2carla_ids)
                for w in walker_list
            ]

        objects.update({"vehicles": vehicle_list})
        objects.update({"walkers": walker_list})

        if self.camera_visualize:
            while self.rgb_camera[0].image is None:
                continue

            names = ["front", "right", "left", "back"]

            for (i, rgb_camera) in enumerate(self.rgb_camera):
                if i > self.camera_num - 1 or i > self.camera_visualize - 1:
                    break
                # we only visualize the frontal camera
                rgb_image = np.array(rgb_camera.image)
                # draw the ground truth bbx on the camera image
                rgb_image = self.visualize_3d_bbx_front_camera(objects, rgb_image, i)
                # resize to make it fittable to the screen
                rgb_image = cv2.resize(rgb_image, (0, 0), fx=0.4, fy=0.4)

                # show image using cv2
                cv2.imshow("%s camera of actor %d, perception deactivated" % (names[i], self.id), rgb_image)
                cv2.waitKey(1)

        if self.lidar_visualize:
            while self.lidar.data is None:
                continue
            o3d_pointcloud_encode(self.lidar.data, self.lidar.o3d_pointcloud)
            # render the raw lidar
            o3d_visualizer_show(self.o3d_vis, self.count, self.lidar.o3d_pointcloud, objects)

        # add traffic light
        objects = self.retrieve_traffic_lights(objects)
        self.objects = objects

        self.count += 1

        return objects

    def visualize_3d_bbx_front_camera(self, objects, rgb_image, camera_index):
        """
        Revamped version of PerceptionManager's visualize_3d_bbx_front_camera method, drawing bounding boxes for not
        only vehicles, but also walkers

        :param objects: list
        :param rgb_image: np.ndarray
        :param camera_index: int
        :return: np.ndarray
        """
        camera_transform = self.rgb_camera[camera_index].sensor.get_transform()
        camera_location = camera_transform.location
        camera_rotation = camera_transform.rotation

        for obj in objects["walkers"] + objects["vehicles"]:
            # we only draw the bounding box in the fov of camera
            _, angle = cal_distance_angle(obj.get_location(), camera_location, camera_rotation.yaw)
            if angle < 60:
                bbx_camera = st.get_2d_bb(obj, self.rgb_camera[camera_index].sensor, camera_transform)
                cv2.rectangle(rgb_image,
                              (int(bbx_camera[0, 0]), int(bbx_camera[0, 1])),
                              (int(bbx_camera[1, 0]), int(bbx_camera[1, 1])),
                              (255, 0, 0), 2)

        return rgb_image

    def filter_walker_out_sensor(self, walker_list):
        """
        Removes walkers out of the scope of the sensor from the list of detected objects

        :param walker_list: list
        :return: list
        """
        semantic_idx = self.semantic_lidar.obj_idx
        semantic_tag = self.semantic_lidar.obj_tag

        # label 4 is the walker -> https://carla.readthedocs.io/en/0.9.12/ref_sensors/#semantic-segmentation-camera
        walker_idx = semantic_idx[semantic_tag == 4]
        # each individual instance id
        walker_unique_id = list(np.unique(walker_idx))

        new_walker_list = []
        for w in walker_list:
            if w.id in walker_unique_id:
                new_walker_list.append(w)

        return new_walker_list

    def relative_angle(self, obj):
        """
        Calculates the relative angle between obj and the ego vehicle

        :param obj: carla.Vehicle or carla.Walker
        :return: float
        """
        a_yaw = obj.get_transform().rotation.yaw
        ego_yaw = self.ego_pos.rotation.yaw
        # Relative angle in (-180, 180) range
        relative_angle = (((a_yaw - ego_yaw) + 180) % 360) - 180
        return relative_angle

    def destroy(self):
        """
        Destroys all sensors
        """
        super().destroy()
        if self.semantic_cameras:
            for semantic_camera in self.semantic_cameras:
                semantic_camera.delete_last_saved_image()
                semantic_camera.sensor.destroy()
