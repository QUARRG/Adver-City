import argparse
import os
import yaml
from omegaconf import OmegaConf
from tqdm import tqdm


def split_weather_and_time_of_day(weather_config):
    """
    Splits the weather_config string into weather and time of day

    :param weather_config: str
    :return: str, str
    """
    time_of_day = weather_config.split("_")[-1]
    weather = weather_config[:-(len(time_of_day) + 1)]
    return weather, time_of_day


def generate_summary(path):
    """
    Generates the summary yaml for the scenario located at the given path. The summary file contains all necessary
    information to generate plots and speeds up their generation afterwards

    :param path: os.path
        Path to the scenario folder whose summary is being generated
    """
    scenario_label = path.split("/")[-1]
    folders = os.listdir(path)
    folders.sort()
    data_protocol_path = os.path.join(path, "data_protocol.yaml")
    data_protocol = OmegaConf.load(data_protocol_path)

    pov_ids = folders[:5]

    folder_path = os.path.join(path, pov_ids[2])
    yaml_frames = [file
                   for file in os.listdir(folder_path)
                   if (file.endswith("yaml") and ("_" not in file))]
    yaml_frames.sort()

    weather, time_of_day = split_weather_and_time_of_day(data_protocol["dataset_config"]["weather"])
    num_spawn_points = len(data_protocol["scenario"]["rsu_list"]) + 2 * len(
        data_protocol["scenario"]["single_cav_list"])

    # scenario information to be save in the summary file
    summary = {
        "simulation": scenario_label,
        "scenario": data_protocol["dataset_config"]["scenario"],
        "weather": weather,
        "time_of_day": time_of_day,
        "density": data_protocol["dataset_config"]["density"],
        "num_frames": len(yaml_frames),
        "num_vehicles": round(data_protocol["scenario"]["num_vehicles"] * num_spawn_points *
                              data_protocol["density"]["vehicle_multiplier"]),
        "num_walkers": round(data_protocol["scenario"]["num_walkers"] * data_protocol["density"]["walker_multiplier"])
    }

    frames_dict = {}
    for yaml_frame in tqdm(yaml_frames):
        # iterate through the frames in the scenario
        frame_number = yaml_frame.split(".")[0]
        pov_frame_paths = [os.path.join(path, pov_id, yaml_frame) for pov_id in pov_ids]
        pov_yamls = [OmegaConf.load(pov_frame_path) for pov_frame_path in pov_frame_paths]
        pov_speeds = [pov_yaml["ego_speed"] for pov_yaml in pov_yamls]

        # index 2 is ego, so it goes last in merge list so that it can override values
        merged_yamls = OmegaConf.merge(pov_yamls[0], pov_yamls[1], pov_yamls[3], pov_yamls[4], pov_yamls[2])

        # Number of walkers might be 0, so key might not exist on dictionary
        if "walkers" in pov_yamls[2]:
            num_walkers = len(merged_yamls["walkers"])
            objs = ["vehicles", "walkers"]
            ego_objs = OmegaConf.merge(pov_yamls[2]["vehicles"], pov_yamls[2]["walkers"])
        else:
            num_walkers = 0
            objs = ["vehicles"]
            ego_objs = pov_yamls[2]["vehicles"]

        # information on the current frame to be save to the summary: speeds of cavs and total number of ground truths
        frame_dict = {
            "cav_speeds": {
                "ego": pov_speeds[2],
                "cav1": pov_speeds[3],
                "cav2": pov_speeds[4]
            },
            "num_annotations": len(merged_yamls["vehicles"]) + num_walkers
        }

        for obj in objs:
            # iterates through detected objects, saving their ground truths to the summary
            for obj_id in merged_yamls[obj]:
                if str(obj_id) in pov_ids:
                    # ignore cavs
                    continue
                elif obj_id in ego_objs:
                    # Vehicle/walker detected by ego
                    classe = merged_yamls[obj][obj_id]["class"] if "class" in merged_yamls[obj][obj_id] else "walker"
                    frame_dict.update({obj_id: {
                        "class": classe,
                        "speed": merged_yamls[obj][obj_id]["speed"],
                        "distance_to_ego": merged_yamls[obj][obj_id]["dist"],
                        "angle_to_ego": merged_yamls[obj][obj_id]["relative_angle"]
                    }})
                else:
                    # Vehicle/walker out of range from ego
                    classe = merged_yamls[obj][obj_id]["class"] if "class" in merged_yamls[obj][obj_id] else "walker"
                    frame_dict.update({obj_id: {
                        "class": classe,
                        "speed": merged_yamls[obj][obj_id]["speed"]
                    }})

        frames_dict.update({int(frame_number): frame_dict})
    summary.update({"frames": frames_dict})

    summary_path = os.path.join(path, "summary.yaml")
    with open(summary_path, "w") as outfile:
        yaml.dump(summary, outfile, default_flow_style=False, sort_keys=False)


# create an argument parser
parser = argparse.ArgumentParser(description="Adver-City dataset scenario summary generator.")

# add arguments to the parser
parser.add_argument('-p', "--path", type=str,
                    help='Path of scenario. Eg: data_dumping/2024_06_14_12_47_41/ui_cd_s')
parser.add_argument("-a", "--all", type=bool,
                    help="Boolean to generate summary of all simulations in a folder.")

# parse the arguments and return the result
opt = parser.parse_args()

arg_path = opt.path
if opt.all:
    # if "all" flag is active, lists scenario folders within path and generates summaries for all of them
    simulation_paths = os.listdir(arg_path)
    simulation_paths.sort()
    for simulation_path in simulation_paths:
        # iterates through simulation folders
        print(f"Generating {simulation_path} summary...")
        path = os.path.join(arg_path, simulation_path)
        generate_summary(path)
else:
    # otherwise, just generate the summary for the folder in the given path
    print("Generating summary...")
    generate_summary(arg_path)
