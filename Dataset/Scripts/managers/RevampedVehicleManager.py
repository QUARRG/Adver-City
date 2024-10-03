import uuid
from opencda.core.actuation.control_manager import ControlManager
from opencda.core.common.v2x_manager import V2XManager
from opencda.core.common.vehicle_manager import VehicleManager
from opencda.core.map.map_manager import MapManager
from opencda.core.safety.safety_manager import SafetyManager
from opencda.core.sensing.localization.localization_manager import LocalizationManager
from Dataset.Scripts.managers.RevampedBehaviorAgent import RevampedBehaviorAgent
from Dataset.Scripts.managers.RevampedDataDumper import RevampedDataDumper
from Dataset.Scripts.managers.RevampedPerceptionManager import RevampedPerceptionManager


class RevampedVehicleManager(VehicleManager):
    """
    Revamped version of VehicleManager, using Revamped versions of PerceptionManager, BehaviorAgent, and DataDumper.
    The constructor also adds semantic cameras to the RevampedPerceptionManager, since they reference the
    RevampedDataDumper
    """
    def __init__(self, vehicle, config_yaml, carla_map, cav_world, save_path, bp_meta, current_time):
        """
        :param vehicle: carla.Vehicle
        :param config_yaml: dict
        :param carla_map: carla.Map
        :param cav_world: opencda.CavWorld
        :param save_path: os.path
        :param bp_meta: dict
            Blueprint dictionary. Used by data_dumper to get the category of each object when dumping data
        :param current_time: str
        """
        self.vid = str(uuid.uuid1())
        self.vehicle = vehicle
        self.carla_map = carla_map

        # retrieve the configuration for different modules
        sensing_config = config_yaml['sensing']
        map_config = config_yaml['map_manager']
        behavior_config = config_yaml['behavior']
        control_config = config_yaml['controller']
        v2x_config = config_yaml['v2x']

        self.v2x_manager = V2XManager(cav_world, v2x_config, self.vid)
        self.localizer = LocalizationManager(vehicle, sensing_config['localization'], carla_map)
        self.perception_manager = RevampedPerceptionManager(vehicle, sensing_config['perception'], cav_world)
        self.map_manager = MapManager(vehicle, carla_map, map_config)
        self.safety_manager = SafetyManager(vehicle=vehicle, params=config_yaml['safety_manager'])
        self.agent = RevampedBehaviorAgent(vehicle, carla_map, behavior_config)
        self.controller = ControlManager(control_config)
        self.data_dumper = RevampedDataDumper(self.perception_manager, vehicle.id, current_time, save_path, bp_meta)

        # semantic cameras are added after creation of data_dumper
        self.perception_manager.add_semantic_cameras(self.data_dumper)
        cav_world.update_vehicle_manager(self)
