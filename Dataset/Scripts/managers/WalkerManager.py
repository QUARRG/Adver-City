import random
import carla
from tqdm import tqdm


class WalkerManager:
    """
    Class to spawn Walkers (pedestrians) according to scenario configurations and then destroy the spawned actors.
    """
    def __init__(self, scenario_params, num_walkers, carla_map, world):
        """
        :param scenario_params: dict
        :param num_walkers: int
        :param carla_map: carla.Map
        :param world: carla.World
        """
        self.num_walkers = num_walkers
        self.carla_map = carla_map
        self.world = world

        if num_walkers > 0:
            self.spawn_areas = self.create_spawn_ranges(scenario_params)
            self.walker_blueprints = self.world.get_blueprint_library().filter('walker')
            self.world.set_pedestrians_cross_factor(scenario_params["scenario"]["walker_crossing_factor"])
            self.walkers = self.spawn_walkers()

    def create_spawn_ranges(self, params):
        """
        Calculates the spawn ranges (x_min, x_max, y_min, y_max) that will be used to spawn walkers based on provided
        configuration

        :param params: dict
            Config for current scenario execution
        :return: list
            List of spawn ranges (x_min, x_max, y_min, y_max)
        """
        cav_list = params["scenario"]["single_cav_list"]
        rsu_list = params["scenario"]["rsu_list"]
        spawn_distance = params["scenario"]["spawning_distance"]
        spawn_distance_to_path = params["scenario"]["spawning_distance_to_path"]

        spawn_ranges = []

        for pov in cav_list + rsu_list:
            # Defines spawn positions around the CAVs and RSUs
            spawn_pos = pov["spawn_position"]
            x_min = spawn_pos[0] - spawn_distance
            x_max = spawn_pos[0] + spawn_distance
            y_min = spawn_pos[1] - spawn_distance
            y_max = spawn_pos[1] + spawn_distance
            spawn_ranges.append([x_min, x_max, y_min, y_max])

        for cav in cav_list:
            # Define spawn positions along the paths that will be taken by the CAVs
            spawn_pos = cav["spawn_position"]
            destination = cav["destination"]
            x_min = min(spawn_pos[0], destination[0]) - spawn_distance_to_path
            x_max = max(spawn_pos[0], destination[0]) + spawn_distance_to_path
            y_min = min(spawn_pos[1], destination[1]) - spawn_distance_to_path
            y_max = max(spawn_pos[1], destination[1]) + spawn_distance_to_path
            spawn_ranges.append([x_min, x_max, y_min, y_max])

        return spawn_ranges

    def get_valid_spawn_point(self):
        """
        Gets a random location for walkers and checks if it is within any of the spawn areas. Repeats until a valid
        spawn location is found or if the maximum number of attempts (100000) is reached.

        :return: carla.Location
            Valid spawn point
        """
        attempts = 100000
        for i in range(attempts):
            spawn_point = self.world.get_random_location_from_navigation()

            for area in self.spawn_areas:
                if area[0] < spawn_point.x < area[1] and area[2] < spawn_point.y < area[3]:
                    return spawn_point

        print("### ERROR: No valid spawning points encountered ###")
        return None

    def spawn_walkers(self):
        """
        Spawns walkers in Carla and starts their movement controller

        :return: list
            List of lists. Each inner list has a carla.Walker and its corresponding carla.WalkerAIController
        """
        print("Spawning walkers...")
        walkers = []
        count = 0
        pbar = tqdm(total=self.num_walkers)

        while count < self.num_walkers:
            pos = self.get_valid_spawn_point()
            if pos is None:
                break

            spawn_transform = carla.Transform(pos, carla.Rotation())

            walker_bp = random.choice(self.walker_blueprints)
            walker = self.world.try_spawn_actor(walker_bp, spawn_transform)
            if not walker:  # Spawning failures are usually caused by collisions
                continue

            controller_bp = self.world.get_blueprint_library().find('controller.ai.walker')
            walker_controller = self.world.try_spawn_actor(controller_bp, carla.Transform(), walker)
            if not walker_controller:
                walker.destroy()
                continue

            self.world.tick()  # MUST be called between AI Controller spawning and start(), otherwise segfaults
            walker_controller.start()
            walker_controller.go_to_location(self.world.get_random_location_from_navigation())
            walker_controller.set_max_speed(1 + random.random())  # Between 1 and 2 m/s (default is 1.4 m/s)
            self.world.tick()

            walkers.append([walker, walker_controller])
            count += 1
            pbar.update(1)

        pbar.close()
        return walkers

    def destroy(self):
        """
        Destroy all carla.Walker and carla.WalkerAIController objects from simulation
        """
        print("Destroying walkers...")
        pbar = tqdm(total=self.num_walkers)
        for (walker, controller) in self.walkers:
            controller.stop()
            controller.destroy()
            walker.destroy()
            pbar.update(1)
        pbar.close()

