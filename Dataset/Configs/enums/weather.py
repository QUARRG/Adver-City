from enum import Enum


class Daytime(Enum):
    DAY = "day"
    NIGHT = "night"


class WeatherCondition(Enum):
    CLEAR = "clear"
    FOGGY = "foggy"
    HARD_RAIN = "hard_rain"
    SOFT_RAIN = "soft_rain"
    FOGGY_HARD_RAIN = "foggy_hard_rain"
    GLARE = "glare"


class Weather(Enum):
    CLEAR_NIGHT = WeatherCondition.CLEAR.value + "_" + Daytime.NIGHT.value
    CLEAR_DAY = WeatherCondition.CLEAR.value + "_" + Daytime.DAY.value
    FOGGY_NIGHT = WeatherCondition.FOGGY.value + "_" + Daytime.NIGHT.value
    FOGGY_DAY = WeatherCondition.FOGGY.value + "_" + Daytime.DAY.value
    HARD_RAIN_NIGHT = WeatherCondition.HARD_RAIN.value + "_" + Daytime.NIGHT.value
    HARD_RAIN_DAY = WeatherCondition.HARD_RAIN.value + "_" + Daytime.DAY.value
    SOFT_RAIN_NIGHT = WeatherCondition.SOFT_RAIN.value + "_" + Daytime.NIGHT.value
    SOFT_RAIN_DAY = WeatherCondition.SOFT_RAIN.value + "_" + Daytime.DAY.value
    FOGGY_HARD_RAIN_NIGHT = WeatherCondition.FOGGY_HARD_RAIN.value + "_" + Daytime.NIGHT.value
    FOGGY_HARD_RAIN_DAY = WeatherCondition.FOGGY_HARD_RAIN.value + "_" + Daytime.DAY.value
    GLARE_DAY = WeatherCondition.GLARE.value + "_" + Daytime.DAY.value


class WeatherAbbreviations(Enum):
    CN = Weather.CLEAR_NIGHT
    CD = Weather.CLEAR_DAY
    FN = Weather.FOGGY_NIGHT
    FD = Weather.FOGGY_DAY
    HRN = Weather.HARD_RAIN_NIGHT
    HRD = Weather.HARD_RAIN_DAY
    SRN = Weather.SOFT_RAIN_NIGHT
    SRD = Weather.SOFT_RAIN_DAY
    FHRN = Weather.FOGGY_HARD_RAIN_NIGHT
    FHRD = Weather.FOGGY_HARD_RAIN_DAY
    GD = Weather.GLARE_DAY
