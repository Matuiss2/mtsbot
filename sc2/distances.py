from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units
from sc2.game_state import GameState

import logging

logger = logging.getLogger(__name__)

from scipy.spatial.distance import pdist, cdist
import math
from math import pow
import numpy as np

from typing import Dict, Tuple, Iterable, Generator


class DistanceCalculation:
    def __init__(self):
        self.state: GameState = None
        self._generated_frame = -100
        self._generated_frame2 = -100
        # A Dictionary with a dict positions: index of the pdist condensed matrix
        self._cached_unit_index_dict: Dict[int, int] = None
        # Pdist condensed vector generated by scipy pdist, half the size of the cdist matrix as 1d array
        self._cached_pdist: np.ndarray = None
        self._cached_cdist: np.ndarray = None

    @property
    def _units_count(self) -> int:
        return len(self.all_units)

    @property
    def _unit_index_dict(self) -> Dict[int, int]:
        """ As property, so it will be recalculated each time it is called, or return from cache if it is called multiple times in teh same game_loop. """
        if self._generated_frame != self.state.game_loop:
            return self.generate_unit_indices()
        return self._cached_unit_index_dict

    @property
    def _pdist(self) -> np.ndarray:
        """ As property, so it will be recalculated each time it is called, or return from cache if it is called multiple times in teh same game_loop. """
        if self._generated_frame2 != self.state.game_loop:
            return self.calculate_distances()
        return self._cached_pdist

    @property
    def _cdist(self) -> np.ndarray:
        """ As property, so it will be recalculated each time it is called, or return from cache if it is called multiple times in teh same game_loop. """
        if self._generated_frame2 != self.state.game_loop:
            return self.calculate_distances()
        return self._cached_cdist

    def generate_unit_indices(self) -> Dict[int, int]:
        if self._generated_frame != self.state.game_loop:
            self._cached_unit_index_dict = {unit.tag: index for index, unit in enumerate(self.all_units)}
            self._generated_frame = self.state.game_loop
        return self._cached_unit_index_dict

    def _calculate_distances_method1(self) -> np.ndarray:
        if self._generated_frame2 != self.state.game_loop:
            # Converts tuple [(1, 2), (3, 4)] to flat list like [1, 2, 3, 4]
            flat_positions = (coord for unit in self.all_units for coord in unit.position_tuple)
            # Converts to numpy array, then converts the flat array back to shape (n, 2): [[1, 2], [3, 4]]
            positions_array: np.ndarray = np.fromiter(
                flat_positions, dtype=np.float, count=2 * self._units_count
            ).reshape((self._units_count, 2))
            if len(positions_array) != self._units_count:
                raise AssertionError()
            self._generated_frame2 = self.state.game_loop
            # See performance benchmarks
            self._cached_pdist = pdist(positions_array, "sqeuclidean")
        return self._cached_pdist

    def _calculate_distances_method2(self) -> np.ndarray:
        if self._generated_frame2 != self.state.game_loop:
            # Converts tuple [(1, 2), (3, 4)] to flat list like [1, 2, 3, 4]
            flat_positions = (coord for unit in self.all_units for coord in unit.position_tuple)
            # Converts to numpy array, then converts the flat array back to shape (n, 2): [[1, 2], [3, 4]]
            positions_array: np.ndarray = np.fromiter(
                flat_positions, dtype=np.float, count=2 * self._units_count
            ).reshape((self._units_count, 2))
            if len(positions_array) != self._units_count:
                raise AssertionError()
            self._generated_frame2 = self.state.game_loop
            # See performance benchmarks
            self._cached_cdist = cdist(positions_array, positions_array, "sqeuclidean")

        return self._cached_cdist

    def _calculate_distances_method3(self) -> np.ndarray:
        """ Nearly same as above, but without asserts"""
        if self._generated_frame2 != self.state.game_loop:
            flat_positions = (coord for unit in self.all_units for coord in unit.position_tuple)
            positions_array: np.ndarray = np.fromiter(
                flat_positions, dtype=np.float, count=2 * self._units_count
            ).reshape((-1, 2))
            self._generated_frame2 = self.state.game_loop
            # See performance benchmarks
            self._cached_cdist = cdist(positions_array, positions_array, "sqeuclidean")

        return self._cached_cdist

    def _get_index_of_two_units_method1(self, unit1: Unit, unit2: Unit) -> int:
        if unit1.tag not in self._unit_index_dict:
            raise AssertionError(
                f"Unit1 {unit1} is not in index dict for distance calculation."
                f" Make sure the unit is alive in the current frame. Ideally take units"
                f" from 'self.units' or 'self.structures'"
                f" as these contain unit data from the current frame. Do not try to save"
                f" 'Units' objects over several iterations."
            )
        if unit2.tag not in self._unit_index_dict:
            raise AssertionError(
                f"Unit2 {unit2} is not in index dict for distance calculation."
                f" Make sure the unit is alive in the current frame. Ideally take units"
                f" from 'self.units' or 'self.structures'"
                f" as these contain unit data from the current frame."
                f" Do not try to save 'Units' objects over several iterations."
            )
        # index1 = self._unit_index_dict[unit1.tag]
        # index2 = self._unit_index_dict[unit2.tag]
        return self.square_to_condensed(self._unit_index_dict[unit1.tag], self._unit_index_dict[unit2.tag])

    def _get_index_of_two_units_method2(self, unit1: Unit, unit2: Unit) -> Tuple[int, int]:
        if unit1.tag not in self._unit_index_dict:
            raise AssertionError(
                f"Unit1 {unit1} is not in index dict for distance calculation."
                f" Make sure the unit is alive in the current frame."
                f" Ideally take units from 'self.units' or 'self.structures'"
                f" as these contain unit data from the current frame."
                f" Do not try to save 'Units' objects over several iterations."
            )
        if unit2.tag not in self._unit_index_dict:
            raise AssertionError(
                f"Unit2 {unit2} is not in index dict for distance calculation."
                f" Make sure the unit is alive in the current frame."
                f" Ideally take units from 'self.units' or 'self.structures'"
                f" as these contain unit data from the current frame."
                f" Do not try to save 'Units' objects over several iterations."
            )
        return self._unit_index_dict[unit1.tag], self._unit_index_dict[unit2.tag]

    def _get_index_of_two_units_method3(self, unit1: Unit, unit2: Unit) -> Tuple[int, int]:
        """ Same function as above, but without asserts"""
        return self._unit_index_dict[unit1.tag], self._unit_index_dict[unit2.tag]

    # Helper functions

    def square_to_condensed(self, i, j) -> int:
        # Converts indices of a square matrix to condensed matrix
        # https://stackoverflow.com/a/36867493/10882657
        if i == j:
            raise AssertionError("No diagonal elements in condensed matrix! Diagonal elements are zero")
        if i < j:
            i, j = j, i
        return self._units_count * j - j * (j + 1) // 2 + i - 1 - j

    def convert_tuple_to_numpy_array(self, pos: Tuple[float, float]) -> np.ndarray:
        """ Converts a single position to a 2d numpy array with 1 row and 2 columns. """
        return np.fromiter(pos, dtype=float, count=2).reshape((1, 2))

    # Fast and simple calculation functions

    def distance_math_hypot(self, p1: Tuple[float, float], p2: Tuple[float, float]):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def distance_math_hypot_squared(self, p1: Tuple[float, float], p2: Tuple[float, float]):
        return pow(p1[0] - p2[0], 2) + pow(p1[1] - p2[1], 2)

    def _distance_squared_unit_to_unit_method0(self, unit1: Unit, unit2: Unit) -> float:
        return self.distance_math_hypot_squared(unit1.position_tuple, unit2.position_tuple)

    # Distance calculation using the pre-calculated matrix above

    def _distance_squared_unit_to_unit_method1(self, unit1: Unit, unit2: Unit) -> float:
        # If checked on units if they have the same tag, return distance 0 as these are not in the 1 dimensional pdist array - would result in an error otherwise
        if unit1.tag == unit2.tag:
            return 0
        # Calculate index, needs to be after pdist has been calculated and cached
        condensed_index = self._get_index_of_two_units(unit1, unit2)
        if condensed_index >= len(self._cached_pdist):
            raise AssertionError(
                f"Condensed index is larger than amount of calculated distances:"
                f" {condensed_index} < {len(self._cached_pdist)},"
                f" units that caused the assert error: {unit1} and {unit2}"
            )
        distance = self._pdist[condensed_index]
        return distance

    def _distance_squared_unit_to_unit_method2(self, unit1: Unit, unit2: Unit) -> float:
        # Calculate index, needs to be after cdist has been calculated and cached
        # index1, index2 = self._get_index_of_two_units(unit1, unit2)
        # distance = self._cdist[index1, index2]
        # return distance
        return self._cdist[self._get_index_of_two_units(unit1, unit2)]

    # Distance calculation using the fastest distance calculation functions

    def _distance_pos_to_pos(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        return self.distance_math_hypot(pos1, pos2)

    def _distance_units_to_pos(self, units: Units, pos: Tuple[float, float]) -> Generator[float, None, None]:
        """ This function does not scale well, if len(units) > 100 it gets fairly slow """
        return (self.distance_math_hypot(u.position_tuple, pos) for u in units)

    def _distance_unit_to_points(
        self, unit: Unit, points: Iterable[Tuple[float, float]]
    ) -> Generator[float, None, None]:
        """ This function does not scale well, if len(points) > 100 it gets fairly slow """
        pos = unit.position_tuple
        return (self.distance_math_hypot(p, pos) for p in points)

    def _distances_override_functions(self, method: int = 0):
        """ Overrides the internal distance calculation functions at game start in bot_ai.py self._prepare_start() function
        method 0: Use python's math.hypot
        The following methods calculate the distances between all units once:
        method 1: Use scipy's pdist condensed matrix (1d array)
        method 2: Use scipy's cidst square matrix (2d array)
        method 3: Use scipy's cidst square matrix (2d array) without asserts (careful: very weird error messages, but maybe slightly faster) """
        if not 0 <= method <= 3:
            raise AssertionError(f"Selected method was: {method}")
        if method == 0:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method0
        elif method == 1:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method1
            self.calculate_distances = self._calculate_distances_method1
            self._get_index_of_two_units = self._get_index_of_two_units_method1
        elif method == 2:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method2
            self.calculate_distances = self._calculate_distances_method2
            self._get_index_of_two_units = self._get_index_of_two_units_method2
        elif method == 3:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method2
            self.calculate_distances = self._calculate_distances_method3
            self._get_index_of_two_units = self._get_index_of_two_units_method3
