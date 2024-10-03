from opencda.core.common.rsu_manager import RSUManager
from opencda.core.sensing.localization.rsu_localization_manager import LocalizationManager
from Dataset.Scripts.managers.RevampedDataDumper import RevampedDataDumper
from Dataset.Scripts.managers.RevampedPerceptionManager import RevampedPerceptionManager


class RevampedRSUManager(RSUManager):
    """
    Revamped class from RSUManager, substituting DataDumper and PerceptionManager for their Revamped versions
    """
    def __init__(self, carla_world, config_yaml, carla_map, cav_world, save_path, bp_meta, current_time):
        """
        :param carla_world: carla.World
        :param config_yaml: dict
        :param carla_map: carla.Map
        :param cav_world: opencda.CavWorld
        :param save_path: os.path
        :param bp_meta: dict
            Blueprint dictionary. Used by data_dumper to get the category of each object when dumping data
        :param current_time: str
        """
        self.rid = config_yaml['id']
        # The id of RSUs is always a negative int
        if self.rid > 0:
            self.rid = -self.rid

        self.carla_map = carla_map

        # retrieve the configure for different modules
        sensing_config = config_yaml['sensing']
        sensing_config['localization']['global_position'] = config_yaml['spawn_position']
        sensing_config['perception']['global_position'] = config_yaml['spawn_position']

        self.localizer = LocalizationManager(carla_world, sensing_config['localization'], self.carla_map)
        self.perception_manager = RevampedPerceptionManager(
            None, sensing_config['perception'], cav_world, carla_world, self.rid
        )
        self.data_dumper = RevampedDataDumper(self.perception_manager, self.rid, current_time, save_path, bp_meta)

        # semantic cameras are added after creation of data_dumper
        self.perception_manager.add_semantic_cameras(self.data_dumper)
        cav_world.update_rsu_manager(self)
