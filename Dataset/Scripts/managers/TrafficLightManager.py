import carla


class TrafficLightManager:
    """
    Manages the state of traffic lights on the intersection ahead of the ego vehicle.

    Parameters
    ----------
    cav : opencda.VehicleManager
        The VehicleManager for the ego vehicle.

    config : dict
        Configuration from the yaml files under "scenario" -> "traffic_lights".

    inv_fps : float
        Time in second that each frame of the simulation takes.

    Attributes
    ----------
    config : dict
        Configuration from the yaml file.

    green_time : float
        Number of frames the green light stays on during the traffic light cycle. First state in the cycle.

    yellow_time : float
        Number of frames the yellow light stays on during the traffic light cycle. Second state in the cycle.

    red_time : float
        Number of frames that all lights stay red during the traffic light cycle. Third state in the cycle.

    frame : int
        Current simulation frame counter. Used just for debugging purposes.

    reset_counter : boolean
        Flag to reset active_frame_counter after server has ticked.

    active_light_id : int
        Index of the traffic light that is currently on. Gets incremented every time cycle is completed.

    active_light_state : carla.TrafficLightState
        Current state of the light that is active during the cycle.

    active_frame_counter : int
        Number of frames that have passed since the current light became active. Resets to 0 once cycle completes.

    traffic_lights : list
        List of the traffic lights (carla.TrafficLight) in the intersection.
    """

    def __init__(self, cav_list, config, inv_fps, world):
        self.world = world
        self.lead_cav_index = config["lead_cav_id"]
        cav = cav_list[self.lead_cav_index]
        self.config = config
        self.green_time = config["times"]["green"] * int(1 / inv_fps)
        self.yellow_time = config["times"]["yellow"] * int(1 / inv_fps)
        self.red_time = config["times"]["red"] * int(1 / inv_fps)

        self.frame = 0
        self.reset_counter = False
        self.active_light_id = config["active_light_id"]
        self.active_light_state = self.key_to_carla_state(config["active_light_state"])
        self.active_frame_counter = config["initial_active_frame_counter"]

        if "distinct_lights" in config:
            self.start_another_traffic_light()

        self.traffic_lights = self.update_traffic_lights_list(cav)
        if self.traffic_lights is not None:
            self.start_traffic_lights()

    def start_another_traffic_light(self):
        """
        Sets the state of a traffic light not ahead of the ego vehicle, but that might affect traffic around it, to
        always green
        """
        for distinct_light in self.config["distinct_lights"]:
            pos = distinct_light["location"]
            wp = self.world.get_map().get_waypoint(carla.Location(x=pos[0], y=pos[1], z=pos[2]))
            tls = self.world.get_traffic_lights_from_waypoint(wp, 20)
            lights = tls[0].get_group_traffic_lights()
            for light in lights:
                light.freeze(True)
            lights[1].set_state(carla.TrafficLightState.Green)

    def key_to_carla_state(self, key):
        """
        Converts a key string to its corresponding carla.TrafficLightState, if it exists

        :param key: str
        :return: carla.TrafficLightState
        """
        if key == "g":
            return carla.TrafficLightState.Green
        elif key == "y":
            return carla.TrafficLightState.Yellow
        elif key == "r":
            return carla.TrafficLightState.Red
        elif key == "o":
            return carla.TrafficLightState.Off
        else:
            print("\n-----\nERROR: Invalid key in key_to_carla_state().\n-----\n")
            return carla.TrafficLightState.Unknown

    def start_traffic_lights(self):
        """
        Freezes all traffic lights in the intersection ahead of the ego vehicle and sets their state according to the
        configuration. The active light will have its state defined by the configuration, while all others will be red
        """
        for i, traffic_light in enumerate(self.traffic_lights):
            traffic_light.freeze(True)
            if i == self.active_light_id:
                traffic_light.set_state(self.active_light_state)
            else:
                traffic_light.set_state(carla.TrafficLightState.Red)

    def stop_traffic_lights(self):
        """
        Method not used in any of Adver-City's scenarios. Unfreezes the traffic lights so that another set of traffic
        lights may be controlled. To be used if ego path goes through multiple intersections
        """
        if self.traffic_lights is not None:
            for traffic_light in self.traffic_lights:
                traffic_light.freeze(False)

            self.traffic_lights[0].reset_group()
            self.traffic_lights = None

    def update_traffic_lights_list(self, cav):
        """
        If ego has detected the traffic lights, returns their corresponding Carla objects

        :param cav: RevampedVehicleManager
        :return: list
            List of carla.TrafficLights
        """
        traffic_light_list = cav.agent.objects['traffic_lights']
        if not traffic_light_list:
            return None
        else:
            return traffic_light_list[0].actor.get_group_traffic_lights()

    def get_time_from_state(self, state):
        """
        For a given state, returns the number of frames that the traffic light should stay in this state

        :param state: carla.TrafficLightState
        :return: float
            Number of frames
        """
        if state == carla.TrafficLightState.Green:
            return self.green_time
        elif state == carla.TrafficLightState.Yellow:
            return self.yellow_time
        elif state == carla.TrafficLightState.Red:
            return self.red_time
        else:
            print("\n-----\nERROR: Invalid state in get_time_from_state().\n-----\n")
            return 0

    def get_next_state(self):
        """
        Returns the next state for the active traffic light. The order is:
        Green -> Yellow -> Red -> Green*

        *If the current light is Red, then it stays Red and the next light will go Green. The attribute changes, but
        the current light will still be Red, the next one is the one to change state

        :return: carla.TrafficLightState
        """
        if self.active_light_state == carla.TrafficLightState.Green:
            return carla.TrafficLightState.Yellow
        elif self.active_light_state == carla.TrafficLightState.Yellow:
            return carla.TrafficLightState.Red
        elif self.active_light_state == carla.TrafficLightState.Red:
            return carla.TrafficLightState.Green
        else:
            print("\n-----\nERROR: Invalid state in get_next_state().\n-----\n")
            return carla.TrafficLightState.Unknown

    def update_info(self, cav_list, debug=False):
        """
        Updates information for the TrafficLightManager. Called once for every frame of the simulation.

        :param cav_list: list
            List of RevampedVehicleManagers
        :param debug: boolean
            If True, prints the traffic light states at every frame.
        """
        ego = cav_list[0]
        traffic_lights = self.update_traffic_lights_list(ego)

        if self.lead_cav_index != 0 and traffic_lights is None:  # If Ego is not at light, considers leading vehicle
            cav = cav_list[self.lead_cav_index]
            traffic_lights = self.update_traffic_lights_list(cav)

        if traffic_lights is not None:  # If car is approaching lights, updated variable
            if self.traffic_lights is None:  # If car wasn't approaching lights, but now is, start those lights
                self.start_traffic_lights()
            self.traffic_lights = traffic_lights

        if self.traffic_lights is not None:  # If there are lights being controlled by the manager, keep controlling it
            if self.reset_counter:
                self.active_frame_counter = 0
                self.reset_counter = False
            elif self.active_frame_counter == self.get_time_from_state(self.active_light_state) - 1:
                self.active_light_state = self.get_next_state()
                if self.active_light_state == carla.TrafficLightState.Green:
                    self.active_light_id = (self.active_light_id + 1) % len(self.traffic_lights)
                self.traffic_lights[self.active_light_id].set_state(self.active_light_state)
                self.reset_counter = True

            self.active_frame_counter += 1

        if debug and traffic_lights is not None:
            self.print_states()

        self.frame += 1

    def print_states(self):
        """
        Helper method to print states of the Traffic Lights and allow for easier understanding of how this class is
        working
        """
        print("-" * 10)
        print(f"frame: {self.frame}, active_frame_counter: {self.active_frame_counter}, "
              f"active_light_id: {self.active_light_id}, pole_index: {self.traffic_lights[0].get_pole_index()}")
        for state in self.traffic_lights:
            print(state.get_state(), end=" | ")
        print("")
