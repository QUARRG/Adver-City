def get_label_from_config(config):
    """
    Helper function

    :param config: dict
        Config dictionary from Omegaconf.load
    :return: str
        Simulation label in a file-friendly format
    """
    dataset_config = config["dataset_config"]
    scenario_label = (dataset_config["scenario_abbreviation"] + "_" +
                      dataset_config["weather_abbreviation"] + "_" +
                      dataset_config["density_abbreviation"])
    return scenario_label
