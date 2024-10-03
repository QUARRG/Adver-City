import argparse
import os
from omegaconf import OmegaConf
from tqdm import tqdm
from Dataset.Scripts.utils.stats import Stats

# create an argument parser
parser = argparse.ArgumentParser(description="Adver-City dataset annotation statistics generator.")

# add arguments to the parser
parser.add_argument('-p', "--path", type=str,
                    help='Path of run to have its annotation statistics generated. Eg: '
                         'data_dumping/2024_06_14_12_47_41')

# parse the arguments and return the result
opt = parser.parse_args()

run_path = opt.path
simulation_folders = os.listdir(run_path)
statistics_path = os.path.join(run_path, "stats/")
if not os.path.exists(statistics_path):
    os.makedirs(statistics_path)

stats = Stats(statistics_path)

print("Reading summary data...")
for simulation_folder in tqdm(simulation_folders):
    if simulation_folder == "stats":
        continue
    simulation_summary = OmegaConf.load(os.path.join(run_path, simulation_folder, "summary.yaml"))
    stats.read_summary_data(simulation_summary)

print("Generating charts...")
stats.generate_charts()



