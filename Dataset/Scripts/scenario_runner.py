import os
import shutil
import subprocess
import sys
import time
import carla
import opencda.scenario_testing.utils.sim_api as sim_api
from omegaconf import OmegaConf
from opencda.core.common.cav_world import CavWorld
from opencda.scenario_testing.utils.yaml_utils import save_yaml
sys.path.append(".")  # necessary so that this script may be called as a subprocess on main.py
from Dataset.Configs.enums.weather import Weather
from Dataset.Scripts.managers.RevampedRSUManager import RevampedRSUManager
from Dataset.Scripts.managers.RevampedVehicleManager import RevampedVehicleManager
from Dataset.Scripts.managers.TrafficLightManager import TrafficLightManager
from Dataset.Scripts.managers.WalkerManager import WalkerManager
from Dataset.Scripts.utils.getters import get_label_from_config


def save_configs(scenario_params):
    """
    Saves configs to the data_dumping folder alongside data from scenario

    :param scenario_params: dict
        Scenario parameters from yaml
    :return: os.path
        Path used to save the data
    """
    # Gets proper path for data dumping
    current_path = os.path.dirname(os.path.realpath(__file__))
    current_time = scenario_params['current_time']
    scenario_label = get_label_from_config(scenario_params)
    save_path = os.path.join(current_path, '../../data_dumping', current_time, scenario_label)

    # Saves yaml with scenario settings
    if not os.path.exists(str(save_path)):
        os.makedirs(str(save_path))
    save_yaml_name = os.path.join(str(save_path), 'data_protocol.yaml')
    save_yaml(scenario_params, save_yaml_name)

    return save_path


def turn_on_vehicle_lights(cavs, npcs, weather):
    """
    Iterates through spawned vehicles (both CAVs and traffic), turning on the vehicle lights

    :param cavs: list
        List of VehicleManagers
    :param npcs: list
        List of Vehicles without sensors
    :param weather: dict
        Weather configurations
    """
    if weather["fog_density"] > 30:
        # if scenario is foggy, turns on fog lights as well
        lights = carla.VehicleLightState(
            carla.VehicleLightState.LowBeam | carla.VehicleLightState.Brake | carla.VehicleLightState.Fog
        )
    else:
        # if not foggy, just turns on low beam and brake lights
        lights = carla.VehicleLightState(
            carla.VehicleLightState.LowBeam | carla.VehicleLightState.Brake
        )

    for cav in cavs:
        cav.vehicle.set_light_state(lights)

    for npc in npcs:
        npc.set_light_state(lights)


def get_weather_from_config(config, dataset_config):
    """
    Creates a carla.WeatherParameters object based on the weather settings from the config

    :param config: dict
        Dict from scenario_params["world"]["weather"] containing weather parameters
    :param dataset_config: dict
        Dict from scenario_params["dataset_config"] containing scenario parameters (abbreviation and weather condition)
    :return: carla.WeatherParameters
        WeatherParameters to be applied to simulation
    """
    if dataset_config["weather"] == Weather.GLARE_DAY.value:
        scenario = dataset_config["scenario_abbreviation"]
        sun_azimuth_angle = config["sun_azimuth_angle"][scenario]
        sun_altitude_angle = config["sun_altitude_angle_scenarios"][scenario]
    else:
        sun_altitude_angle = config["sun_altitude_angle"]
        sun_azimuth_angle = 0.0

    weather = carla.WeatherParameters(
        cloudiness=config["cloudiness"],
        fog_density=config["fog_density"],
        wetness=config["wetness"],
        wind_intensity=config["wind_intensity"],
        fog_distance=config["fog_distance"],
        fog_falloff=config["fog_falloff"],
        precipitation=config["precipitation"],
        precipitation_deposits=config["precipitation_deposits"],
        sun_altitude_angle=sun_altitude_angle,
        rayleigh_scattering_scale=config["rayleigh_scattering_scale"],
        scattering_intensity=config["scattering_intensity"],
        mie_scattering_scale=config["mie_scattering_scale"],
        sun_azimuth_angle=sun_azimuth_angle
    )

    return weather


def add_spawn_from_density(params):
    """
    Adds spawn point entries to dictionary based on pov positioning and spawn configurations

    :param params: dict
        Config for current scenario execution
    :return: dict
        Modified config with keys for spawn points
    """
    # gets all values from dicts
    cav_list = params["scenario"]["single_cav_list"]
    rsu_list = params["scenario"]["rsu_list"]
    spawn_distance = params["scenario"]["spawning_distance"]
    spawn_distance_to_path = params["scenario"]["spawning_distance_to_path"]
    params["carla_traffic_manager"]["range"].clear()
    vehicle_num = round(params["scenario"]["num_vehicles"] * params["density"]["vehicle_multiplier"])

    global_distance = params["carla_traffic_manager"]["global_distance"]
    x_step = round(global_distance + 3.183)  # largest dimension of the largest vehicle (except for the firetruck)
    y_step = round(global_distance + 3.183)  # largest dimension of the largest vehicle (except for the firetruck)

    # for each pov (cav or rsu), adds spawn points in a rectangular area around it
    for pov in cav_list + rsu_list:
        spawn_pos = pov["spawn_position"]
        x_min = spawn_pos[0] - spawn_distance
        x_max = spawn_pos[0] + spawn_distance
        y_min = spawn_pos[1] - spawn_distance
        y_max = spawn_pos[1] + spawn_distance
        params["carla_traffic_manager"]["range"].append([x_min, x_max, y_min, y_max, x_step, y_step, vehicle_num])

    # for each cav, adds spawn points along the path taken by the cav
    for cav in cav_list:
        spawn_pos = cav["spawn_position"]
        destination = cav["destination"]
        x_min = min(spawn_pos[0], destination[0]) - spawn_distance_to_path
        x_max = max(spawn_pos[0], destination[0]) + spawn_distance_to_path
        y_min = min(spawn_pos[1], destination[1]) - spawn_distance_to_path
        y_max = max(spawn_pos[1], destination[1]) + spawn_distance_to_path
        params["carla_traffic_manager"]["range"].append([x_min, x_max, y_min, y_max, x_step, y_step, vehicle_num])

    return params


def create_vehicle_manager(scenario_manager, save_path):
    """
    Creates instances of RevampedVehicleManager for each CAV in the scenario

    :param scenario_manager: ScenarioManager
    :param save_path: os.path
        Path of data_dumping
    :return: list
        List of RevampedVehicleManagers created
    """
    # By default, we use Lincoln MKZ2017 as our CAV model
    if scenario_manager.carla_version == '0.9.11':
        default_model = 'vehicle.lincoln.mkz2017'
    else:
        default_model = 'vehicle.lincoln.mkz_2017'

    cav_vehicle_bp = scenario_manager.world.get_blueprint_library().find(default_model)
    single_cav_list = []

    for i, cav_config in enumerate(scenario_manager.scenario_params['scenario']['single_cav_list']):
        platoon_base = OmegaConf.create({'platoon': scenario_manager.scenario_params.get('platoon_base', {})})
        cav_config = OmegaConf.merge(scenario_manager.scenario_params['vehicle_base'], platoon_base, cav_config)

        # creates carla.Transform based on config
        spawn_transform = carla.Transform(
            carla.Location(
                x=cav_config['spawn_position'][0],
                y=cav_config['spawn_position'][1],
                z=cav_config['spawn_position'][2]),
            carla.Rotation(
                pitch=cav_config['spawn_position'][5],
                yaw=cav_config['spawn_position'][4],
                roll=cav_config['spawn_position'][3]))

        cav_vehicle_bp.set_attribute('color', '0, 0, 255')  # all CAVs are blue
        vehicle = scenario_manager.world.spawn_actor(cav_vehicle_bp, spawn_transform)

        # create vehicle manager for each cav
        vehicle_manager = RevampedVehicleManager(
            vehicle, cav_config, scenario_manager.carla_map, scenario_manager.cav_world,
            save_path, scenario_manager.bp_meta, scenario_manager.scenario_params['current_time']
        )

        scenario_manager.world.tick()
        vehicle_manager.v2x_manager.set_platoon(None)  # Adver-City does not use platooning
        destination = carla.Location(x=cav_config['destination'][0],
                                     y=cav_config['destination'][1],
                                     z=cav_config['destination'][2])
        vehicle_manager.update_info()
        vehicle_manager.set_destination(vehicle_manager.vehicle.get_location(), destination, clean=True)

        single_cav_list.append(vehicle_manager)

    return single_cav_list


def create_rsu_manager(scenario_manager, save_path):
    """
    Creates instances of RevampedRSUManager for each RSU in scenario

    :param scenario_manager: ScenarioManager
    :param save_path: os.path
        Path of data_dumping
    :return: list
        List of RevampedRSUManagers
    """
    params = scenario_manager.scenario_params
    rsu_list = []
    for i, rsu_config in enumerate(params['scenario']['rsu_list']):
        rsu_config = OmegaConf.merge(params['rsu_base'], rsu_config)
        rsu_manager = RevampedRSUManager(
            scenario_manager.world, rsu_config, scenario_manager.carla_map, scenario_manager.cav_world,
            save_path, scenario_manager.bp_meta, params['current_time']
        )

        rsu_list.append(rsu_manager)

    return rsu_list


def run_scenario():
    """
    Initializes manager classes and runs simulation on Carla
    """
    try:
        # loads config from temp file. Config was not passed was argument to simplify subprocess run call
        scenario_params = OmegaConf.load("temp_config.yaml")
        scenario_params = add_spawn_from_density(scenario_params)

        cav_world = CavWorld()
        scenario_manager = sim_api.ScenarioManager(
            scenario_params, False, '0.9.12', town=scenario_params['town'], cav_world=cav_world
        )

        # Spawn pedestrians (done before vehicles because world.tick() is called for each pedestrian spawned)
        num_walkers = round(scenario_params["scenario"]["num_walkers"] *
                            scenario_params["density"]["walker_multiplier"])
        walker_manager = WalkerManager(scenario_params, num_walkers, scenario_manager.carla_map, scenario_manager.world)

        # Save scenario configs and return path used for saving
        save_path = save_configs(scenario_params)

        # Spawn POV vehicles and RSUs
        cav_list = create_vehicle_manager(scenario_manager, save_path)
        rsu_list = create_rsu_manager(scenario_manager, save_path)

        # create background traffic in carla
        traffic_manager, bg_veh_list = scenario_manager.create_traffic_carla()
        traffic_manager.set_random_device_seed(scenario_params["world"]["seed_traffic"])

        turn_on_vehicle_lights(cav_list, bg_veh_list, scenario_params["world"]["weather"])

        spectator = scenario_manager.world.get_spectator()

        traffic_light_manager = TrafficLightManager(
            cav_list, scenario_params["scenario"]["traffic_lights"], scenario_params["world"]["fixed_delta_seconds"],
            scenario_manager.world
        )

        # Set weather conditions
        weather = get_weather_from_config(scenario_params["world"]["weather"], scenario_params["dataset_config"])
        scenario_manager.world.set_weather(weather)

        count = 0
        # Iterates until scenario termination
        while True:
            scenario_manager.tick()

            transform = cav_list[0].vehicle.get_transform()
            spectator.set_transform(
                carla.Transform(transform.location + carla.Location(z=70), carla.Rotation(pitch=-90))
            )

            traffic_light_manager.update_info(cav_list, debug=False)

            for i, cav in enumerate(cav_list):
                cav.update_info()
                control = cav.run_step()
                cav.vehicle.apply_control(control)

            for i, rsu in enumerate(rsu_list):
                rsu.update_info()
                rsu.run_step()

            count += 1

            # No Aver-City scenario has 3 minutes of data. If that happens during simulation,
            # it's due to undesired agent behavior
            if count == 1800:
                label = get_label_from_config(scenario_params)
                print(f"THE {label} SCENARIO HAS REACHED 1800 FRAMES")
                path_opt = "-p" + "data_dumping/" + scenario_params["current_time"] + "/" + label
                # generates the video of current run so that error may be observed afterwards
                p = subprocess.run(["python", "generate_video.py", path_opt, "-a y"], env=os.environ)
                # delete data from this run
                shutil.rmtree(save_path)
                time.sleep(3)
                break

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print("#" * 20)
        print(f"ERROR {type(e).__name__} on {fname}, line {exc_tb.tb_lineno}:")
        print(e)
        print("#" * 20)

    for cav in cav_list:
        cav.destroy()

    for rsu in rsu_list:
        rsu.destroy()


if __name__ == "__main__":
    run_scenario()
