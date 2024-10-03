import argparse
import gc
import os
import subprocess
import sys
import time
from datetime import datetime
import psutil
from omegaconf import OmegaConf
from opencda.scenario_testing.utils.yaml_utils import add_current_time, save_yaml
from Dataset.Configs.enums.weather import Weather, WeatherAbbreviations
from Dataset.Configs.enums.scenarios import Scenarios, ScenarioAbbreviations
from Dataset.Configs.enums.density import Density, DensityAbbreviations
from Dataset.Scripts.utils.getters import get_label_from_config


def arg_parse():
    """
    Parses arguments provided to running python script

    :return: parser
        Parser with script arguments
    """

    # create an argument parser
    parser = argparse.ArgumentParser(description="Adver-City dataset generator.")

    # add arguments to the parser
    parser.add_argument("-w", "--weather", type=str,
                        help="Select weather condition to be generated. If none is selected, all conditions will be "
                             "generated. Available conditions: CLEAR_NIGHT (CN), CLEAR_DAY (CD), FOGGY_NIGHT (FN), "
                             "FOGGY_DAY (FD), HARD_RAIN_NIGHT (HRN), HARD_RAIN_DAY (HRD), SOFT_RAIN_NIGHT (SRN), "
                             "SOFT_RAIN_DAY (SRD), FOGGY_HARD_RAIN_NIGHT (FHRN), FOGGY_HARD_RAIN_DAY (FHRD).")
    parser.add_argument("-s", "--scenario", type=str,
                        help="Select scenario to be simulated. If none is selected, all scenarios will be "
                             "simulated. Available scenarios: RURAL_INTERSECTION (RI), RURAL_CURVED_NON_JUNCTION "
                             "(RCNJ), RURAL_STRAIGHT_NON_JUNCTION (RSNJ), URBAN_INTERSECTION (UI), URBAN_NON_JUNCTION "
                             "(UNJ).")
    parser.add_argument("-d", "--density", type=str,
                        help="Density of objects within the scene. Available densities: DENSE (D), SPARSE (S).")
    parser.add_argument("-v", "--video", type=bool,
                        help="If a video of the frames saved by each POV\'s main camera should be generated at the end "
                             "of the simulation. Y/N.")
    parser.add_argument("-m", "--summary", type=bool,
                        help="Generate summary of simulation right after its run. Y/N.")

    # parse the arguments and return the result
    opt = parser.parse_args()
    return opt


def print_progress(delta, times, num_simulations, label):
    """
    Helper function to print progress information to terminal while simulations are running

    :param delta: int
        Time in seconds of last simulation
    :param times: list
        Times in seconds of simulations that have already finished running, used to estimate remaining time
    :param num_simulations: int
        Total number of simulations being run
    :param label: str
        Simulation label in a file-friendly format
    """
    hours = round(delta // 3600)
    minutes = round((delta % 3600) // 60)
    seconds = round(delta % 60, 2)

    simulations_remaining = num_simulations - len(times)
    average_time = sum(times) / len(times)
    time_remaining = average_time * simulations_remaining
    hours_remaining = round(time_remaining // 3600)
    minutes_remaining = round((time_remaining % 3600) // 60)
    seconds_remaining = round(time_remaining % 60, 2)

    print("-" * 71)
    print(f"Time taken to generate scenario {label}: {hours}h {minutes}m {seconds}s")
    print(f"{simulations_remaining} simulations remaining | "
          f"Estimated time remaining: {hours_remaining}h {minutes_remaining}m {seconds_remaining}s")
    print("-" * 71)
    print("")


def load_simulation_configs(arg):
    """
    Loads and merges yaml files with information about the simulations to be executed

    :param arg: parser
        Parser with script arguments
    :return: list
        List of configuration dictionaries for simulations
    """
    # load default configs
    default_yaml = "Dataset/Configs/default.yaml"
    if not os.path.isfile(default_yaml):
        sys.exit("default.yaml file not found!")
    dataset_dict = OmegaConf.load(default_yaml)

    # load scenario configs
    if arg.scenario is None:
        scenario_configs = load_all_configs(dataset_dict, Scenarios)
    elif (arg.scenario.upper() not in ScenarioAbbreviations.__members__ and
          arg.scenario.upper() not in Scenarios.__members__):
        sys.exit("Invalid scenario!")
    else:
        scenario_configs = load_config(dataset_dict, arg.scenario.upper(), ScenarioAbbreviations, Scenarios)

    # load weather configs and merge with previous configs
    weather_configs = []
    for scenario_config in scenario_configs:
        if arg.weather is None:
            weather_config = load_all_configs(scenario_config, Weather)
        elif (arg.weather.upper() not in WeatherAbbreviations.__members__ and
              arg.weather.upper() not in Weather.__members__):
            sys.exit("Invalid weather condition!")
        else:
            weather_config = load_config(scenario_config, arg.weather.upper(), WeatherAbbreviations, Weather)

        weather_configs.extend(weather_config)

    # load density configs and merge with previous configs
    simulation_configs = []
    for weather_config in weather_configs:
        if arg.density is None:
            simulation_config = load_all_configs(weather_config, Density)
        elif (arg.density.upper() not in DensityAbbreviations.__members__ and
              arg.density.upper() not in Density.__members__):
            sys.exit("Invalid density!")
        else:
            simulation_config = load_config(weather_config, arg.density.upper(), DensityAbbreviations, Density)

        simulation_configs.extend(simulation_config)

    simulation_configs[0] = add_current_time(simulation_configs[0])

    return simulation_configs


def load_config(default_dict, config: str, config_abbreviation_enum, config_enum):
    """
    Loads a single YAML config

    :param default_dict: dict
        Dictionary with configs already loaded, to be merged with new config
    :param config: str
        Name of config to be loaded
    :param config_abbreviation_enum: Enum
        Abbreviation enum for config being loaded
    :param config_enum: Enum
        Enum for config being loaded
    :return: list
        List with a single element: the config loaded. List is used to make the return compatible with other operations
    """
    if config in config_abbreviation_enum.__members__:
        chosen_config = config_abbreviation_enum[config].value
    else:
        chosen_config = config_enum[config]

    config_yaml = f"Dataset/Configs/{config_enum.__name__}/{chosen_config.value}.yaml"

    if not os.path.isfile(config_yaml):
        sys.exit(f"{chosen_config.value}.yaml file not found!")

    config_dict = OmegaConf.load(config_yaml)
    dataset_dict = OmegaConf.merge(default_dict, config_dict)

    return [dataset_dict]


def load_all_configs(default_dict, config_enum):
    """
    Loads all YAML configs for a given Enum type

    :param default_dict: dict
        Dictionary with configs already loaded, to be merged with new configs
    :param config_enum: Enum
        Enum with info on new YAMLs to be loaded
    :return: list
        Returns a list of all configs loaded, merged with default_dict
    """
    config_dicts = []
    for config in config_enum:
        config_yaml = f"Dataset/Configs/{config_enum.__name__}/{config.value}.yaml"

        if not os.path.isfile(config_yaml):
            sys.exit(f"{config.value}.yaml file not found!")

        config_dict = OmegaConf.load(config_yaml)
        config_dict = OmegaConf.merge(default_dict, config_dict)
        config_dicts.append(config_dict)

    return config_dicts


def init_carla():
    """
    Initializes Carla subprocess

    :return: str/None
        Returns os's username of Carla's process, or None if process failed to initialize
    """
    #carla12 = subprocess.Popen(["../../../Carla12/CarlaUE4.sh"])
    try:
        carla12 = subprocess.Popen(["../../../Carla12/CarlaUE4.sh"])
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print("-"*40)
        print(f"CarlaUE4.sh NOT FOUND!\nChange the path to CarlaUE4.sh on:\n{fname}, line {exc_tb.tb_lineno}")
        print("-"*40)
        exit(1)

    # Sleep used so that Carla may have enough time to properly initialize
    time.sleep(10)

    carla12_pid = carla12.pid
    for proc in psutil.process_iter(["pid", "name", "username"]):
        if proc.info["pid"] == carla12_pid:
            return proc.info["username"]

    return None


def kill_carla(user):
    """
    Kills Carla process

    :param user: str
        OS username running Carla process
    """
    for proc in psutil.process_iter(["pid", "name", "username"]):
        try:
            if user and proc.info["username"] != user:
                continue

            if "CarlaUE4-Linux-Shipping" in proc.info["name"]:
                proc.kill()
                proc.wait()
                print(f"Process with PID {proc.info['pid']} ({proc.info['name']}) terminated.")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    time.sleep(10)


def restart_carla(user):
    """
    Kills Carla, then initializes it again

    :param user: str
        OS username running Carla process
    """
    kill_carla(user)
    gc.collect()
    init_carla()


if __name__ == "__main__":
    # parse the arguments
    arg = arg_parse()
    # load and merge yamls
    simulation_configs = load_simulation_configs(arg)

    # initialize variables
    starting_time = simulation_configs[0]["current_time"]
    times = []
    counter = 0

    # initialize carla and get the user info
    carla12_user = init_carla()

    # iterates through simulations
    for simulation_config in simulation_configs:
        counter += 1
        if counter % 8 == 0:  # restarts carla every 8 simulations
            restart_carla(carla12_user)

        simulation_config["current_time"] = starting_time
        # saves current config as a temporary file so that yaml address is always the same
        save_yaml(simulation_config, "temp_config.yaml")
        label = get_label_from_config(simulation_config)

        # prints current time and label of simulation that will start its execution
        current_time = datetime.now()
        current_time = current_time.strftime("(%Y-%m-%d) %H:%M:%S")
        print(f"--- Running {label} {current_time} ---")

        try:
            attempts = 0
            while attempts < 5:
                t0 = time.time()
                p = subprocess.run(["python", "Dataset/Scripts/scenario_runner.py"])
                # Walker spawning sometimes randomly glitches due to unreachable target locations, resulting in runs
                # of less than a minute. In those cases, scenario should be rerun
                if time.time() - t0 > 60:
                    break
                else:
                    # if walker spawning error occurs, restarts Carla and try again, up to 5 times
                    attempts += 1
                    print(f"Error spawning walkers on {label} scenario. Attempt #{attempts}")
                    print("-"*50)
                    restart_carla(carla12_user)

            path_opt = "-p" + "data_dumping/" + starting_time + "/" + label

            if arg.video:
                print("#####")
                p = subprocess.run(["python", "generate_video.py", path_opt, "-a y"], env=os.environ)

            if arg.summary:
                print("#####")
                p = subprocess.run(["python", "generate_summary.py", path_opt], env=os.environ)

            delta = time.time() - t0
            times.append(delta)
            print_progress(delta, times, len(simulation_configs), label)
            gc.collect()
        except Exception as e:
            print(e)

    os.remove("temp_config.yaml")
    kill_carla(carla12_user)
