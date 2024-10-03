import weakref
import carla
import numpy as np


class CameraSensor:
    """
    Camera manager for vehicle or infrastructure.

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
    config: dict
        Configuration from yaml

    Attributes
    ----------
    sensor : carla.sensor
        The carla sensor that mounts at the vehicle.
    image : np.ndarray
        Current received rgb image.
    timestamp: carla.Timestamp
        Timestamp of current frame
    frame: int
        Current frame number
    image_width: int
        Width from config file
    image_height: int
        Height from config file
    """
    def __init__(self, vehicle, world, relative_position, global_position, config):
        if vehicle is not None:
            world = vehicle.get_world()

        blueprint = world.get_blueprint_library().find('sensor.camera.rgb')
        blueprint.set_attribute('fov', str(config["fov"]))
        blueprint.set_attribute('image_size_x', str(config["image_size_x"]))
        blueprint.set_attribute('image_size_y', str(config["image_size_y"]))
        blueprint.set_attribute('bloom_intensity', str(config["bloom_intensity"]))
        blueprint.set_attribute('fstop', str(config["fstop"]))
        blueprint.set_attribute('iso', str(config["iso"]))
        blueprint.set_attribute('gamma', str(config["gamma"]))
        blueprint.set_attribute('lens_flare_intensity', str(config["lens_flare_intensity"]))
        blueprint.set_attribute('shutter_speed', str(config["shutter_speed"]))

        spawn_point = self.spawn_point_estimation(relative_position, global_position)

        if vehicle is not None:
            self.sensor = world.spawn_actor(blueprint, spawn_point, attach_to=vehicle)
        else:
            self.sensor = world.spawn_actor(blueprint, spawn_point)

        self.image = None
        self.timestamp = None
        self.frame = 0
        weak_self = weakref.ref(self)
        self.sensor.listen(lambda event: CameraSensor._on_rgb_image_event(weak_self, event))

        # camera attributes
        self.image_width = int(self.sensor.attributes['image_size_x'])
        self.image_height = int(self.sensor.attributes['image_size_y'])

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

        # this is for RSUs. It utilizes global position instead of relative position to the vehicle
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
    def _on_rgb_image_event(weak_self, event):
        """
        Called at every frame, converts image and stores it in the class attributes

        :param weak_self: weakref.ref
        :param event: event
        """
        self = weak_self()
        if not self:
            return
        image = np.array(event.raw_data)
        image = image.reshape((self.image_height, self.image_width, 4))
        # we need to remove the alpha channel
        image = image[:, :, :3]

        self.image = image
        self.frame = event.frame
        self.timestamp = event.timestamp