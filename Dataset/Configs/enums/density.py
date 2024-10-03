from enum import Enum


class Density(Enum):
    DENSE = "dense"
    SPARSE = "sparse"


class DensityAbbreviations(Enum):
    D = Density.DENSE
    S = Density.SPARSE

