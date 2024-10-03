from opencda.core.plan.behavior_agent import BehaviorAgent


class RevampedBehaviorAgent(BehaviorAgent):
    """
    Revamped version of BehaviorAgent. Modifies the traffic_light_manager method and includes walkers among
    possible obstacles to be considered by the vehicle
    """
    def __init__(self, vehicle, carla_map, config_yaml):
        """
        :param vehicle: carla.Vehicle
        :param carla_map: carla.map
        :param config_yaml: dict
        """
        super().__init__(vehicle, carla_map, config_yaml)
        self.crossed_on_yellow = False
        self.previous_light_state = None

    def update_information(self, ego_pos, ego_speed, objects):
        """
        Revamped method from BehaviorAgent, adding walkers as objects and including the crossed_on_yellow flag

        :param ego_pos: carla.Transform
            Ego position from LocalizationManager
        :param ego_speed: float
            Ego speed in km/h
        :param objects: dict
            Objects detection results from perception module
        """
        self.previous_light_state = self.light_state
        super().update_information(ego_pos, ego_speed, objects)
        self.obstacle_vehicles = objects["vehicles"] + objects["walkers"]
        if self.light_state == "Red" and self.previous_light_state == "Yellow":
            self.crossed_on_yellow = True
        elif self.light_state == "Green":
            self.crossed_on_yellow = False

    def traffic_light_manager(self, waypoint):
        """
        Revamped method from method because vehicles were often not stopping at red lights

        :param waypoint: carla.Waypoint
            Parameter is not used anymore, but it is kept in the method signature to make it compatible with OpenCDA
            calls to it
        :return: int
            1 if vehicle should stop, 0 if it may continue
        """
        # This method can be improved to account for more general situations

        if self.vehicle.get_traffic_light() is not None:
            light_id = self.vehicle.get_traffic_light().id
        else:
            light_id = -1

        # vehicle just passed a stop sign, and won't stop at any stop sign in the next 20 seconds
        if 40 <= self.stop_sign_wait_count < 240:
            self.stop_sign_wait_count += 1
        elif self.stop_sign_wait_count >= 240 or self.light_state != "Red":
            self.stop_sign_wait_count = 0

        if self.light_state == "Red":
            # when light state is red and light id is -1, it means the vehicle is near a stop sign
            if light_id == -1:
                # we force the vehicle to wait for 4 seconds in front of the stop sign
                if self.stop_sign_wait_count < 40:
                    self.stop_sign_wait_count += 1
                    return 1  # stop
                # After passing a stop sign, the vehicle shouldn't stop at the stop sign in the opposite direction
                else:
                    return 0  # no need to stop

            if self.crossed_on_yellow:
                return 0  # no need to stop
            else:
                return 1  # stop

        return 0
