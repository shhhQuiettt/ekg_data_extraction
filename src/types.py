from dataclasses import dataclass
import numpy as np
import numpy.typing as npt


@dataclass
class PlotArea:
    label: str
    label_center: tuple[int, int]
    top_left_absolute: tuple[int, int]
    bottom_right_absolute: tuple[int, int]
    image: npt.NDArray[np.uint8]


@dataclass
class SignalFunction:
    label: str
    x: npt.NDArray[np.float64]
    y: npt.NDArray[np.float64]
    base_line: float
    pixels_per_ms: float
