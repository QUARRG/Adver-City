import copy
import os.path
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import colors
from Dataset.Configs.enums.density import Density
from Dataset.Configs.enums.scenarios import Scenarios
from Dataset.Configs.enums.weather import WeatherCondition, Daytime


class Stats:
    """
    Used to store information on each frame of the simulation and then generate statistics of the scenarios
    """
    def __init__(self, path):
        """
        :param path: os.path
            Path used to save plots

        Attributes:
        ---
        scenarios (dict):
            Stores data for each scenario
            Keys: {
                "urban_intersection", "urban_intersection", "rural_intersection", "rural_straight_non_junction",
                "rural_curved_non_junction"
            }
            Values: (dict) {
                Each scenario value is a dict itself, with lists storing information on objects in the scenarios
                Keys: {
                    "num_frames", "num_vehicles", "num_walkers", "traffic_speed", "cav_speed"
                }
                Values: (list)
            }
        }
        weather (dict):
            Stores the number of frames for each weather condition
            Keys: {
                "clear", "foggy", "hard_rain", "soft_rain", "foggy_hard_rain", "glare"
            }
            Values: (int)
        }
        time_of_day (dict): {
            Stores the number of frames for each time of day
            Keys: {
                "day", "night"
            }
            Values: (int)
        }
        density (dict): {
            Stores discretized values for the number of objects per distance to the ego vehicle
            Keys: {
                "dense", "sparse"
            }
            Values: (ndarray, dim 10)
        }
        class_histogram (dictionary): {
            Stores the amount of objects for each category
            Keys: {
                "car", "truck", "van", "bicycle", "motorcycle", "walker"
            }
            Values: (int)
        }
        traffic_speed (ndarray, dim 10):
            Stores discretized values for the speed of non-CAV vehicles
        ego_speed (ndarray, dim 10):
            Stores discretized values for the speed of the ego vehicle
        num_keyframes (ndarray, dim 15):
            Store discretized values of the amount of annotations in each keyframe
        angles_to_ego (list):
            Stores the relative angle of objects in the scene to the ego vehicle (if object is within ego`s line of
            sight)
        distances_to_ego (list):
            Stores the distance of objects in the scene to the ego vehicle (if object is within ego`s line of sight)
        discretization (dict):
            Stores parameters used to discretize data for plotting
            Keys: {
                "speed", "annotations", "distance", "angle_polar", "distance_polar"
            }
            Values: (dict) {
                Keys: {
                    "max", "bins"
                }
                Values: (int)
            }
        }
        color_dict (dict): {
            Used to assign specific colors for each weather condition
            Keys: {
                "clear", "hard_rain", "soft_rain", "foggy_hard_rain", "glare", "foggy", "night", "day"
            }
            Values: (str)
        }
        """
        self.path = path

        base_scenario = {
            "num_frames": [],
            "num_vehicles": [],
            "num_walkers": [],
            "traffic_speed": [],
            "cav_speed": []
        }

        self.scenarios = {}
        for scenario in Scenarios:
            self.scenarios.update({scenario.name.lower(): copy.deepcopy(base_scenario)})

        self.weather = {}
        for weather in WeatherCondition:
            self.weather.update({weather.name.lower(): 0})

        self.time_of_day = {}
        for time_of_day in Daytime:
            self.time_of_day.update({time_of_day.name.lower(): 0})

        self.density = {}
        for density in Density:
            self.density.update({density.name.lower(): np.zeros(11)})

        self.class_histogram = {
            "car": 0,
            "truck": 0,
            "van": 0,
            "bicycle": 0,
            "motorcycle": 0,
            "walker": 0
        }

        self.traffic_speed = np.zeros(101)
        self.ego_speed = np.zeros(101)
        self.num_keyframes = np.zeros(15)

        self.angles_to_ego = []
        self.distances_to_ego = []

        self.discretization = {
            "speed": {"max": 75, "bins": 75},
            "annotations": {"max": 140, "bins": 14},
            "distance": {"max": 200, "bins": 10},
            "angle_polar": {"max": 360, "bins": 12},
            "distance_polar": {"max": 200, "bins": 16},
        }

        self.color_dict = {
            "clear": "limegreen",
            "hard_rain": "teal",
            "soft_rain": "cornflowerblue",
            "foggy_hard_rain": "dimgray",
            "glare": "gold",
            "foggy": "lightgray",
            "night": "dimgray",
            "day": "skyblue"
        }

        plt.rcParams.update({'font.size': 22, 'pdf.fonttype': 42})

    def read_summary_data(self, summary):
        """
        Reads data from a summary file and saves it to class attributes

        :param summary: dict
            Dictionary with data read from the summary yaml file
        """
        label = summary["scenario"]
        num_frames = summary["num_frames"]
        self.scenarios[label]["num_frames"].append(num_frames)
        self.scenarios[label]["num_vehicles"].append(summary["num_vehicles"])
        self.scenarios[label]["num_walkers"].append(summary["num_walkers"])

        self.weather[summary["weather"]] += num_frames
        self.time_of_day[summary["time_of_day"]] += num_frames

        for frame in summary["frames"]:
            for key, value in summary["frames"][frame]["cav_speeds"].items():
                self.scenarios[label]["cav_speed"].append(value)
                if key == "ego":
                    speed_bin = self.get_discretized_bin(value, "speed")
                    self.ego_speed[speed_bin] += 1

            num_annotations = summary["frames"][frame]["num_annotations"]
            annotation_bin = self.get_discretized_bin(num_annotations, "annotations")
            self.num_keyframes[annotation_bin] += 1

            for obj_id, values in summary["frames"][frame].items():
                if obj_id in ["cav_speeds", "num_annotations"]:
                    continue

                self.class_histogram[values["class"]] += 1
                if values["class"] != "walker":
                    speed_bin = self.get_discretized_bin(values["speed"], "speed")
                    self.traffic_speed[speed_bin] += 1
                    self.scenarios[label]["traffic_speed"].append(values["speed"])

                if "distance_to_ego" in values:
                    distance_bin = self.get_discretized_bin(values["distance_to_ego"], "distance")
                    self.density[summary["density"]][distance_bin] += 1

                    self.angles_to_ego.append(self.rad_angle(values["angle_to_ego"]))
                    self.distances_to_ego.append(values["distance_to_ego"])

    def rad_angle(self, angle):
        """
        Converts angle from degrees to radians, keeping the values within the range [0, 2PI]

        :param angle: float
            Angle in degrees
        :return: float
            Angle in radians
        """
        positive_value = (angle + 360) % 360
        radians = (positive_value / 180) * np.pi
        return radians

    def get_discretized_bin(self, value, key, angle=False):
        """
        Given a value and the key that describes it, returns the index of the bin this value belongs to

        :param value: float
        :param key: str
        :param angle: boolean
            If value is an angle or not
        :return: int
            Index of bin used to discretize values
        """
        discretization_factor = self.discretization[key]["max"] / self.discretization[key]["bins"]

        if angle and value > (360 - (discretization_factor / 2)):
            return 0
        else:
            return round(value / discretization_factor)

    def generate_charts(self):
        """
        Calls all methods that create the statistics charts
        """
        self.scenario_stats_table()
        self.weather_frames_pie_chart()
        self.time_of_day_frames_pie_chart()
        self.plot_class_histogram()
        self.num_vehicles_per_speed()
        self.density_by_range_to_ego()
        self.num_frames_per_ego_speed()
        self.num_keyframes_per_num_annotations()
        self.polar_density_map()

    def avg(self, values, decimal_places=0):
        """
        Helper function to calculate the average of a list of values

        :param values: list
        :param decimal_places: int
            Decimal places to be used for rounding the average value
        :return: float
            Average value of the list, rounded
        """
        if not values:
            return 0
        elif decimal_places == 0:
            return round(np.average(values))
        else:
            return round(np.average(values), decimal_places)

    def stddev(self, values, decimal_places=0):
        """
        Helper function to calculate the standard deviation of a list of values

        :param values: list
        :param decimal_places: int
            Decimal places to be used for rounding the average value
        :return: float
            Standard deviation of the list, rounded
        """
        if not values:
            return 0
        elif decimal_places == 0:
            return round(np.std(values))
        else:
            return round(np.std(values), decimal_places)

    def sum(self, values, decimal_places=0):
        """
        Helper function to calculate the sum of a list of values

        :param values: list
        :param decimal_places: int
            Decimal places to be used for rounding the average value
        :return: float
            Sum of the list, rounded
        """
        if not values:
            return 0
        elif decimal_places == 0:
            return round(np.sum(values))
        else:
            return round(np.sum(values), decimal_places)

    def save_to_csv(self, label, num_frames, num_vehicles, num_walkers, traffic_speed, cav_speed):
        """
        Helper function to store data in CSV file, handling file creation if necessary

        :param label: str
        :param num_frames: list
        :param num_vehicles: list
        :param num_walkers: list
        :param traffic_speed: list
        :param cav_speed: list
        """
        csv_file_path = os.path.join(self.path, "stats.csv")

        df = pd.DataFrame({
            "Scenario": [label],
            "Length (avg)": [self.avg(num_frames)],
            "Length (stddev)": [self.stddev(num_frames)],
            "Length (sum)": [np.sum(num_frames)],
            "Num vehicles (avg)": [self.avg(num_vehicles)],
            "Num vehicles (stddev)": [self.stddev(num_vehicles)],
            "Num vehicles (sum)": [np.sum(num_vehicles)],
            "Num walkers (avg)": [self.avg(num_walkers)],
            "Num walkers (stddev)": [self.stddev(num_walkers)],
            "Num walkers (sum)": [np.sum(num_walkers)],
            "Traffic speed (avg)": [self.avg(traffic_speed, decimal_places=3)],
            "Traffic speed (stddev)": [self.stddev(traffic_speed, decimal_places=3)],
            "CAV speed (avg)": [self.avg(cav_speed, decimal_places=3)],
            "CAV speed (stddev)": [self.stddev(cav_speed, decimal_places=3)]
        })

        if not os.path.isfile(csv_file_path):
            df.to_csv(csv_file_path, index=False)
        else:
            file_df = pd.read_csv(csv_file_path)
            file_df = file_df.append(df)
            file_df.to_csv(csv_file_path, index=False)

    def scenario_stats_table(self):
        """
        Iterates through scenarios, saving their statistics to a CSV file
        """
        num_frames = []
        num_vehicles = []
        num_walkers = []
        traffic_speed = []
        cav_speed = []

        for label, scenario in self.scenarios.items():
            self.save_to_csv(label, scenario["num_frames"], scenario["num_vehicles"], scenario["num_walkers"],
                             scenario["traffic_speed"], scenario["cav_speed"])

            num_frames.extend(scenario["num_frames"])
            num_vehicles.extend(scenario["num_vehicles"])
            num_walkers.extend(scenario["num_walkers"])
            traffic_speed.extend(scenario["traffic_speed"])
            cav_speed.extend(scenario["cav_speed"])

        self.save_to_csv("TOTAL", num_frames, num_vehicles, num_walkers, traffic_speed, cav_speed)

    def weather_frames_pie_chart(self):
        """
        Creates a plot for the percentage of frames for each weather condition
        """
        labels, frames, colors = [], [], []
        for weather, frame in self.weather.items():
            if frame == 0:
                continue
            labels.append(self.format_weather(weather))
            colors.append(self.color_dict[weather])
            frames.append(frame)

        with plt.rc_context({'font.size': 18}):
            fig, ax = plt.subplots()
            ax.pie(frames, labels=labels, autopct='%1.1f%%', colors=colors)
            fig.tight_layout()
            fig.savefig(self.path + "weather.pdf")

    def format_weather(self, weather_label):
        """
        Formats weather labels for the plot
        """
        label_words = weather_label.split("_")
        new_label = ""
        for i, label_word in enumerate(label_words):
            new_label += self.first_upper(label_word)
            if i != len(label_words) - 1:
                new_label += " "
        return new_label

    def time_of_day_frames_pie_chart(self):
        """
        Creates a plot for the percentage of frames per time of day
        """
        labels, frames, colors = [], [], []
        for time_of_day, frame in self.time_of_day.items():
            if frame == 0:
                continue
            labels.append(self.first_upper(time_of_day))
            colors.append(self.color_dict[time_of_day])
            frames.append(frame)

        fig, ax = plt.subplots()
        ax.pie(frames, labels=labels, autopct='%1.1f%%', colors=colors)
        fig.tight_layout()
        fig.savefig(self.path + "time_of_day.pdf")

    def first_upper(self, word):
        """
        Helper function that capitalizes the first letter of the string

        :param word: str
        :return: str
        """
        return word[0].upper() + word[1:]

    def plot_class_histogram(self):
        """
        Creates a class histogram for the objects in the dataset
        """
        classes = []
        counts = []
        for obj_class, obj_count in self.class_histogram.items():
            if obj_class == "walker":
                classes.append("Pedestrian")
            else:
                classes.append(self.first_upper(obj_class))
            counts.append(obj_count)

        counts, classes = zip(*sorted(zip(counts, classes), reverse=True))

        with plt.rc_context({'font.size': 12}):
            fig, ax = plt.subplots()
            bars = ax.bar(classes, counts)
            ax.bar_label(bars)
            ax.set_ylabel("Annotated Instances")
            fig.tight_layout()
            fig.savefig(self.path + "class_histogram.pdf")

    def num_vehicles_per_speed(self):
        """
        Creates a plot for the number of vehicles per speed
        """
        speed_discretization_factor = self.discretization["speed"]["max"] / self.discretization["speed"]["bins"]
        non_zero_indices = np.nonzero(self.traffic_speed)[0]
        if len(non_zero_indices) > 0:
            max_speed = non_zero_indices[-1] * speed_discretization_factor
            last_index = non_zero_indices[-1] + 1
        else:
            last_index = len(self.traffic_speed)
            max_speed = len(self.traffic_speed) * speed_discretization_factor

        speeds = np.arange(0, max_speed + speed_discretization_factor, speed_discretization_factor).tolist()
        num_vehicles = self.traffic_speed.tolist()[:last_index]

        fig, ax = plt.subplots()
        ax.bar(speeds, num_vehicles)
        ax.set_ylabel("Vehicles")
        ax.set_xlabel("Speed (km/h)")
        ax.set_yscale("log")
        fig.tight_layout()
        fig.savefig(self.path + "vehicles_per_speed.pdf")

    def density_by_range_to_ego(self):
        """
        Creates a plot showing the number of objects per distance to the ego vehicle for dense and sparse scenarios
        """
        distance_discretization_factor = self.discretization["distance"]["max"] / self.discretization["distance"][
            "bins"]
        density_dict = {
            "Dense": self.density["dense"].tolist(),
            "Sparse": self.density["sparse"].tolist()
        }

        fig, ax = plt.subplots()
        x = np.arange(len(self.density["dense"].tolist())) * distance_discretization_factor
        width = 8
        multiplier = 0

        for density, frequency in density_dict.items():
            offset = width * multiplier
            ax.bar(x + offset, frequency, width, label=density)
            multiplier += 1

        ax.set_ylabel("Objects")
        ax.set_xlabel("Distance to ego (m)")
        ax.legend(loc="upper right")
        fig.tight_layout()
        fig.savefig(self.path + "density_by_range_to_ego.pdf")

    def num_frames_per_ego_speed(self):
        """
        Creates a plot for the number of frames per ego speed (in km/h)
        """
        speed_discretization_factor = self.discretization["speed"]["max"] / self.discretization["speed"]["bins"]
        non_zero_indices = np.nonzero(self.ego_speed)[0]
        if len(non_zero_indices) > 0:
            max_speed = non_zero_indices[-1] * speed_discretization_factor
            last_index = non_zero_indices[-1] + 1
        else:
            last_index = len(self.traffic_speed)
            max_speed = len(self.ego_speed) * speed_discretization_factor

        speeds = np.arange(0, max_speed + speed_discretization_factor, speed_discretization_factor).tolist()
        num_frames = self.ego_speed.tolist()[:last_index]

        fig, ax = plt.subplots()
        ax.bar(speeds, num_frames)
        ax.set_yscale("log")
        ax.set_ylabel("Keyrames")
        ax.set_xlabel("Ego vehicle speed (km/h)")
        fig.tight_layout()
        fig.savefig(self.path + "num_frames_per_ego_speed.pdf")

    def num_keyframes_per_num_annotations(self):
        """
        Creates a plot for the number of keyframes per annotation
        """
        discrete_factor = self.discretization["annotations"]["max"] / self.discretization["annotations"]["bins"]
        non_zero_indices = np.nonzero(self.num_keyframes)[0]
        if len(non_zero_indices) > 0:
            max_annotations = non_zero_indices[-1] * discrete_factor
            last_index = non_zero_indices[-1] + 1
        else:
            last_index = len(self.num_keyframes)
            max_annotations = len(self.num_keyframes) * discrete_factor

        num_annotations = np.arange(0, max_annotations + discrete_factor, discrete_factor).tolist()
        num_keyframes = self.num_keyframes.tolist()[:last_index]

        fig, ax = plt.subplots()
        ax.bar(num_annotations, num_keyframes, width=7)
        ax.set_yscale("log")
        ax.set_xlabel("Annotations")
        ax.set_ylabel("Keyframes")
        fig.tight_layout()
        fig.savefig(self.path + "num_keyframes_per_num_annotations.pdf")

    def polar_density_map(self):
        """
        Creates a polar density maps of objects in relation to the ego vehicle, in log scale
        """
        rbins = np.linspace(0, 200, 17)
        abins = np.linspace(0, 2 * np.pi, 37)
        angles_array = np.array(self.angles_to_ego)
        distances_array = np.array(self.distances_to_ego)
        hist, _, _ = np.histogram2d(angles_array, distances_array, bins=(abins, rbins))
        A, R = np.meshgrid(abins, rbins)

        with plt.rc_context({'font.size': 14}):
            fig, ax = plt.subplots(subplot_kw=dict(projection="polar"))
            ax.set_theta_zero_location("N")
            ax.set_rticks([50, 100, 150, 200])
            ax.tick_params(pad=10)

            pc = ax.pcolormesh(A, R, hist.T, cmap="Blues", norm=colors.LogNorm())
            fig.colorbar(pc, pad=0.12)
            fig.tight_layout()
            fig.savefig(self.path + "polar_density_map.pdf")
