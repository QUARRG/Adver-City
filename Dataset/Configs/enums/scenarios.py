from enum import Enum


class Scenarios(Enum):
    URBAN_NON_JUNCTION = "urban_non_junction"
    URBAN_INTERSECTION = "urban_intersection"
    RURAL_INTERSECTION = "rural_intersection"
    RURAL_STRAIGHT_NON_JUNCTION = "rural_straight_non_junction"
    RURAL_CURVED_NON_JUNCTION = "rural_curved_non_junction"


class ScenarioAbbreviations(Enum):
    UNJ = Scenarios.URBAN_NON_JUNCTION
    UI = Scenarios.URBAN_INTERSECTION
    RI = Scenarios.RURAL_INTERSECTION
    RSNJ = Scenarios.RURAL_STRAIGHT_NON_JUNCTION
    RCNJ = Scenarios.RURAL_CURVED_NON_JUNCTION
