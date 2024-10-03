import numpy as np
import yaml
import os
import open3d as o3d
from opencda.core.common.data_dumper import DataDumper
from opencda.core.common.misc import get_speed
from opencda.scenario_testing.utils.yaml_utils import save_yaml
from opencda.core.sensing.perception import sensor_transformation as st


class RevampedDataDumper(DataDumper):
    """
    Revamped version of DataDumper, changing the frequency at which files are saved, the ground truth yaml contents,
    the point cloud file name, and saving gnss and imu data.
    """
    def __init__(self, perception_manager, vehicle_id, save_time, path, bp_meta):
        """
        :param perception_manager: RevampedPerceptionManager
        :param vehicle_id: int
        :param save_time: str
        :param path: os.path
        :param bp_meta: dict
            Blueprint dictionary. Used by data_dumper to get the category of each object when dumping data
        """
        super().__init__(perception_manager, vehicle_id, save_time)

        self.create_path(path)
        self.save_parent_folder = os.path.join(path, str(self.vehicle_id))
        self.bp_meta = bp_meta

    def create_path(self, path):
        """
        Creates folder for the vehicle/rsu if it does not exist

        :param path: os.path
        """
        save_parent_folder = os.path.join(path, str(self.vehicle_id))

        if not os.path.exists(save_parent_folder):
            os.makedirs(save_parent_folder)

    def run_step(self, perception_manager, localization_manager, behavior_agent):
        """
        Saves data for the current frame of the simulation

        :param perception_manager: RevampedPerceptionManager
        :param localization_manager: opencda.LocalizationManager
        :param behavior_agent: RevampedBehaviorAgent
        """
        self.count += 1

        # Ignores first 60 frames due to object spawning
        if self.count < 60:
            return

        # Saves at every frame (10 Hz)
        self.save_rgb_image(self.count)
        self.save_yaml_file(perception_manager, localization_manager, behavior_agent, self.count)
        self.save_lidar_points()

        # If it is a CAV
        if behavior_agent is not None:
            self.save_gnss_imu(localization_manager.gnss, localization_manager.imu, self.save_parent_folder, self.count)

    def save_lidar_points(self):
        """
        Saves point cloud to file
        """
        point_cloud = self.lidar.data

        point_xyz = point_cloud[:, :-1]
        point_intensity = point_cloud[:, -1]
        point_intensity = np.c_[point_intensity, np.zeros_like(point_intensity), np.zeros_like(point_intensity)]

        o3d_pcd = o3d.geometry.PointCloud()
        o3d_pcd.points = o3d.utility.Vector3dVector(point_xyz)
        o3d_pcd.colors = o3d.utility.Vector3dVector(point_intensity)

        # write to pcd file
        pcd_name = "%06d" % self.count + "_lidar.ply"
        o3d.io.write_point_cloud(os.path.join(self.save_parent_folder, pcd_name), pointcloud=o3d_pcd, write_ascii=True)

    def save_gnss_imu(self, gnss, imu, save_path, frame):
        """
        Saves GNSS & IMU data to file

        :param gnss: opencda.GnssSensor
        :param imu: opencda.ImuSensor
        :param save_path: os.path
        :param frame: int
        """
        localization_dictionary = {
            "gnss": {
                "lat": gnss.lat,
                "lon": gnss.lon,
                "alt": gnss.alt,
                "timestamp": gnss.timestamp,
            },
            "imu": {
                "accelerometer": {
                    "x": imu.accelerometer[0],
                    "y": imu.accelerometer[1],
                    "z": imu.accelerometer[2]
                },
                "gyroscope": {
                    "x": imu.gyroscope[0],
                    "y": imu.gyroscope[1],
                    "z": imu.gyroscope[2]
                },
                "compass": imu.compass
            }
        }
        file_name = os.path.join(save_path, "%06d" % frame + "_gnss_imu.yaml")

        with open(file_name, "w") as outfile:
            yaml.dump(localization_dictionary, outfile, default_flow_style=False)

    def save_yaml_file(self, perception_manager, localization_manager, behavior_agent, count):
        """
        Save ground truths about the scene to a yaml file

        :param perception_manager: RevampedPerceptionManager
        :param localization_manager: opencda.LocalizationManager
        :param behavior_agent: RevampedBehaviorAgent
        :param count: int
        """
        frame = count

        dump_yml = {}
        vehicle_dict = {}
        walker_dict = {}

        # dump obstacle vehicles first
        objects = perception_manager.objects
        vehicle_list = objects["vehicles"]
        walker_list = objects["walkers"]

        for veh in vehicle_list:
            veh_carla_id = veh.carla_id
            veh_pos = veh.get_transform()
            veh_bbx = veh.bounding_box
            veh_speed = get_speed(veh)

            assert veh_carla_id != -1, "Please turn off perception active mode if you are dumping data"

            vehicle_dict.update({veh_carla_id: {
                "bp_id": veh.type_id,
                "class": self.bp_meta[veh.type_id]["class"],
                "color": veh.color,
                "location": [veh_pos.location.x,
                             veh_pos.location.y,
                             veh_pos.location.z],
                "center": [veh_bbx.location.x,
                           veh_bbx.location.y,
                           veh_bbx.location.z],
                "angle": [veh_pos.rotation.roll,
                          veh_pos.rotation.yaw,
                          veh_pos.rotation.pitch],
                "extent": [veh_bbx.extent.x,
                           veh_bbx.extent.y,
                           veh_bbx.extent.z],
                "speed": veh_speed,
                "dist": perception_manager.dist(veh),
                "relative_angle": perception_manager.relative_angle(veh)
            }})

        dump_yml.update({"vehicles": vehicle_dict})

        for walker in walker_list:
            walker_carla_id = walker.carla_id
            walker_pos = walker.get_transform()
            walker_bbx = walker.bounding_box
            walker_speed = get_speed(walker)

            walker_dict.update({walker_carla_id: {
                "bp_id": walker.type_id,
                "location": [walker_pos.location.x,
                             walker_pos.location.y,
                             walker_pos.location.z],
                "angle": [walker_pos.rotation.roll,
                          walker_pos.rotation.yaw,
                          walker_pos.rotation.pitch],
                "extent": [walker_bbx.extent.x,
                           walker_bbx.extent.y,
                           walker_bbx.extent.z],
                "speed": walker_speed,
                "class": "walker",
                "dist": perception_manager.dist(walker),
                "relative_angle": perception_manager.relative_angle(walker)
            }})

            dump_yml.update({"walkers": walker_dict})

        # dump ego pose and speed, if vehicle does not exist, then it is
        # a rsu(road side unit).
        predicted_ego_pos = localization_manager.get_ego_pos()
        true_ego_pos = localization_manager.vehicle.get_transform() \
            if hasattr(localization_manager, "vehicle") \
            else localization_manager.true_ego_pos

        dump_yml.update({"predicted_ego_pos": [
            predicted_ego_pos.location.x,
            predicted_ego_pos.location.y,
            predicted_ego_pos.location.z,
            predicted_ego_pos.rotation.roll,
            predicted_ego_pos.rotation.yaw,
            predicted_ego_pos.rotation.pitch]})
        dump_yml.update({"true_ego_pos": [
            true_ego_pos.location.x,
            true_ego_pos.location.y,
            true_ego_pos.location.z,
            true_ego_pos.rotation.roll,
            true_ego_pos.rotation.yaw,
            true_ego_pos.rotation.pitch]})
        dump_yml.update({"ego_speed":
                        float(localization_manager.get_ego_spd())})

        # dump lidar sensor coordinates under world coordinate system
        lidar_transformation = self.lidar.sensor.get_transform()
        dump_yml.update({"lidar_pose": [
            lidar_transformation.location.x,
            lidar_transformation.location.y,
            lidar_transformation.location.z,
            lidar_transformation.rotation.roll,
            lidar_transformation.rotation.yaw,
            lidar_transformation.rotation.pitch]})

        # dump camera sensor coordinates under world coordinate system
        for (i, camera) in enumerate(self.rgb_camera):
            camera_param = {}
            camera_transformation = camera.sensor.get_transform()
            camera_param.update({"cords": [
                camera_transformation.location.x,
                camera_transformation.location.y,
                camera_transformation.location.z,
                camera_transformation.rotation.roll,
                camera_transformation.rotation.yaw,
                camera_transformation.rotation.pitch
            ]})

            # dump intrinsic matrix
            camera_intrinsic = st.get_camera_intrinsic(camera.sensor)
            camera_intrinsic = self.matrix2list(camera_intrinsic)
            camera_param.update({"intrinsic": camera_intrinsic})

            # dump extrinsic matrix lidar2camera
            lidar2world = st.x_to_world_transformation(self.lidar.sensor.get_transform())
            camera2world = st.x_to_world_transformation(camera.sensor.get_transform())

            world2camera = np.linalg.inv(camera2world)
            lidar2camera = np.dot(world2camera, lidar2world)
            lidar2camera = self.matrix2list(lidar2camera)
            camera_param.update({"extrinsic": lidar2camera})
            dump_yml.update({"camera%d" % i: camera_param})

        dump_yml.update({"RSU": True})
        # dump the planned trajectory if it exists
        if behavior_agent is not None:
            trajectory_deque = behavior_agent.get_local_planner().get_trajectory()
            trajectory_list = []

            for i in range(len(trajectory_deque)):
                tmp_buffer = trajectory_deque.popleft()
                x = tmp_buffer[0].location.x
                y = tmp_buffer[0].location.y
                spd = float(tmp_buffer[1])

                trajectory_list.append([x, y, spd])

            dump_yml.update({"plan_trajectory": trajectory_list})
            dump_yml.update({"RSU": False})

        yml_name = "%06d" % frame + ".yaml"
        save_path = os.path.join(self.save_parent_folder,
                                 yml_name)

        save_yaml(dump_yml, save_path)

