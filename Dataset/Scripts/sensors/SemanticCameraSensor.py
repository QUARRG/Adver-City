import os
import carla


class SemanticCameraSensor:
    """
    Semantic camera manager for vehicle or infrastructure.

    Parameters
    ----------
    vehicle : carla.Vehicle
        The carla.Vehicle, this is for cav.
    world : carla.World
        The carla world object, this is for rsu.
    relative_position : list
        Relative position of the camera, [x, y, z]
    global_position : list
        Global position of the infrastructure, [x, y, z]
    id: int
        Id of object (vehicle or rsu) that this camera is attached to
    config: dict
        Configuration from yaml
    data_dumper: RevampedDataDumper
        Used for keeping a consistent frame count

    Attributes
    ----------
    sensor : carla.sensor
        The carla sensor that mounts at the vehicle.
    save_folder: str
        Path of the folder used to save data
    id: int
        Id of the object this camera is attached to
    """
    def __init__(self, vehicle, world, relative_position, global_position, id, config, data_dumper):
        if vehicle is not None:
            world = vehicle.get_world()

        blueprint = world.get_blueprint_library().find('sensor.camera.semantic_segmentation')
        blueprint.set_attribute('fov', str(config["fov"]))
        blueprint.set_attribute('image_size_x', str(config["image_size_x"]))
        blueprint.set_attribute('image_size_y', str(config["image_size_y"]))

        spawn_point = self.spawn_point_estimation(relative_position, global_position)

        if vehicle is not None:
            self.sensor = world.spawn_actor(blueprint, spawn_point, attach_to=vehicle)
        else:
            self.sensor = world.spawn_actor(blueprint, spawn_point)

        self.data_dumper = data_dumper
        self.save_folder = str(data_dumper.save_parent_folder)
        self.id = id
        self.sensor.listen(
            lambda image: SemanticCameraSensor._on_image_event(image, self.save_folder, self.id, self.data_dumper)
        )

    @staticmethod
    def spawn_point_estimation(relative_position, global_position):
        """
        Estimates the spawn point based on relative and global positions

        :param relative_position: list
        :param global_position: list
        :return: carla.Transform
        """
        pitch = 0
        roll = 0
        carla_location = carla.Location(x=0, y=0, z=0)
        x, y, z, yaw = relative_position

        # this is for rsu. It utilizes global position instead of relative
        # position to the vehicle
        if global_position is not None:
            carla_location = carla.Location(x=global_position[0], y=global_position[1], z=global_position[2])
            roll = global_position[3]
            yaw = yaw + global_position[4]
            pitch = global_position[5]

        carla_location = carla.Location(x=carla_location.x + x,
                                        y=carla_location.y + y,
                                        z=carla_location.z + z)

        carla_rotation = carla.Rotation(roll=roll, yaw=yaw, pitch=pitch)
        spawn_point = carla.Transform(carla_location, carla_rotation)

        return spawn_point

    @staticmethod
    def _on_image_event(image, save_folder, camera_id, data_dumper):
        """
        Called at every frame, converts image and stores it in the class attributes

        :param weak_self: weakref.ref
        :param event: event
        """
        counter = data_dumper.count + 1  # Counter is only updated after this method
        if counter >= 60:
            image.save_to_disk(
                os.path.join(save_folder, '%06d' % counter + '_semantic' + str(camera_id) + '.png'),
                carla.ColorConverter.CityScapesPalette
            )

    def delete_last_saved_image(self):
        """
        Semantic image is saved through listen method, while the regular camera images are saved through OpenCDA.
        When the Ego vehicle reaches the destination, OpenCDA exits, but the semantic images are still saved for
        that last frame, which requires them to be removed
        """
        counter = self.data_dumper.count + 1
        os.remove(os.path.join(self.save_folder, '%06d' % counter + '_semantic' + str(self.id) + '.png'))
