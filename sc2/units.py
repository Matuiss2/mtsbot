"""
Groups a lot of info and methods to control a group made from the same type of unit
"""
from __future__ import annotations

import random
import warnings
from itertools import chain
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

from .ids.unit_typeid import UnitTypeId
from .position import Point2, Point3
from .unit import Unit

warnings.simplefilter("once")

if TYPE_CHECKING:
    from .bot_ai import BotAI


class Units(list):
    """ A collection of Unit objects. Makes it easy to select units by selectors."""

    @classmethod
    def from_proto(cls, units, bot_object: BotAI):
        """ Get necessary info from sc2 protocol"""
        return cls((Unit(u, bot_object=bot_object) for u in units))

    def __init__(self, units, bot_object: BotAI):
        super().__init__(units)
        self.bot_object = bot_object

    def __call__(self, *args, **kwargs):
        return UnitSelection(self, *args, **kwargs)

    def select(self, *args, **kwargs):
        """ Select the units group"""
        return UnitSelection(self, *args, **kwargs)

    def copy(self):
        """ Copies the units group"""
        return self.subgroup(self)

    def _merge_units(self, other_units):
        return Units(
            chain(
                iter(self),
                (unit for unit in other_units if unit.tag not in (self_unit.tag for self_unit in self)),
            ),
            self.bot_object,
        )

    def __or__(self, other: Units) -> Units:
        return self._merge_units(other)

    def __add__(self, other: Units) -> Units:
        return self._merge_units(other)

    def __and__(self, other: Units) -> Units:
        return Units(
            (other_unit for other_unit in other if other_unit.tag in (self_unit.tag for self_unit in self)),
            self.bot_object,
        )

    def __sub__(self, other: Units) -> Units:
        return Units(
            (self_unit for self_unit in self if self_unit.tag not in (other_unit.tag for other_unit in other)),
            self.bot_object,
        )

    def __hash__(self):
        return hash(unit.tag for unit in self)

    def find_by_tag(self, tag) -> Optional[Unit]:
        """ Find an unit by the given tag, if no such unit is found it returns None"""
        for unit in self:
            if unit.tag == tag:
                return unit
        return None

    def take(self, n: int) -> Units:
        """ Take n units from self group or all of then if n >= len(self) """
        if n >= len(self):
            return self
        return self.subgroup(self[:n])

    @property
    def random_unit(self) -> Unit:
        """ Take a random unit from the group object"""
        if not self:
            raise AssertionError("Units object is empty")
        return random.SystemRandom().choice(self)

    def random_unit_or(self, other: any) -> Unit:
        """ Same as above, but instead of giving an error if object is empty returns the other parameter instead"""
        return self.random_unit() if self else other

    def random_group_of(self, n: int) -> Units:
        """ Returns self if n >= self.amount. """
        if n < 1:
            return Units([], self.bot_object)
        if n >= len(self):
            return self
        return self.subgroup(random.sample(self, n))

    def in_attack_range_of(self, unit: Unit, bonus_distance: Union[int, float] = 0) -> Units:
        """
        Filters units that are in attack range of the given unit. This uses the unit and target unit.radius when
        calculating the distance, so it should be accurate. Caution: This may not work well for static structures (
        bunker, sieged tank, planetary fortress, photon cannon, spine and spore crawler) because it the attack
        ranges differ for static / immovable units.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                all_zerglings_my_marine_can_attack = enemy_zerglings.in_attack_range_of(my_marine)

        Example::

            enemy_mutalisks = self.enemy_units(UnitTypeId.MUTALISK)
            my_marauder = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARAUDER), None)
            if my_marauder:
                all_mutalisks_my_marauder_can_attack = enemy_mutalisks.in_attack_range_of(my_marauder)
                # Is empty because mutalisk are flying and marauder cannot attack air

        """
        return self.filter(lambda x: unit.target_in_range(x, bonus_distance=bonus_distance))

    def closest_distance_to(self, position: Union[Unit, Point2, Point3]) -> float:
        """
        Returns the distance between the closest unit from this group to the target unit.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next(unit for unit in self.units if unit.type_id == UnitTypeId.MARINE)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                closest_zergling_distance = enemy_zerglings.closest_distance_to(my_marine)
            # Contains the distance between the marine and the closest zergling

        """
        if not self:
            raise AssertionError("Units object is empty")
        if isinstance(position, Unit):
            return min(self.bot_object.distance_squared_unit_to_unit(unit, position) for unit in self) ** 0.5
        return min(self.bot_object.distance_units_to_pos(self, position))

    def furthest_distance_to(self, position: Union[Unit, Point2, Point3]) -> float:
        """
        Returns the distance between the furthest unit from this group to the target unit


        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                furthest_zergling_distance = enemy_zerglings.furthest_distance_to(my_marine)
                # Contains the distance between the marine and the furthest away zergling

        """
        if not self:
            raise AssertionError("Units object is empty")
        if isinstance(position, Unit):
            return max(self.bot_object.distance_squared_unit_to_unit(unit, position) for unit in self) ** 0.5
        return max(self.bot_object.distance_units_to_pos(self, position))

    def closest_to(self, position: Union[Unit, Point2, Point3]) -> Unit:
        """
        Returns the closest unit from the object to the target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                closest_zergling = enemy_zerglings.closest_to(my_marine)
                # Contains the zergling that is closest to the target marine

        """
        if not self:
            raise AssertionError("Units object is empty")
        if isinstance(position, Unit):
            return min(
                (unit1 for unit1 in self),
                key=lambda unit2: self.bot_object.distance_squared_unit_to_unit(unit2, position),
            )

        distances = self.bot_object.distance_units_to_pos(self, position)
        return min(((unit, dist) for unit, dist in zip(self, distances)), key=lambda my_tuple: my_tuple[1])[0]

    def furthest_to(self, position: Union[Unit, Point2, Point3]) -> Unit:
        """
        Returns the furthest unit from the object to the target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                furthest_zergling = enemy_zerglings.furthest_to(my_marine)
                # Contains the zergling that is furthest away to the target marine

        """
        if not self:
            raise AssertionError("Units object is empty")
        if isinstance(position, Unit):
            return max(
                (unit1 for unit1 in self),
                key=lambda unit2: self.bot_object.distance_squared_unit_to_unit(unit2, position),
            )
        distances = self.bot_object.distance_units_to_pos(self, position)
        return max(((unit, dist) for unit, dist in zip(self, distances)), key=lambda my_tuple: my_tuple[1])[0]

    def closer_than(self, distance: Union[int, float], position: Union[Unit, Point2, Point3]) -> Units:
        """
        Returns all units from the object that are closer than the given distance from the target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING) my_marine = next((unit for unit in self.units if
            unit.type_id == UnitTypeId.MARINE), None) if my_marine: close_zerglings = enemy_zerglings.closer_than(3,
            my_marine) # Contains all zerglings that are distance 3 or less away from the marine (does not include
            unit radius in calculation)

        """
        if not self:
            return self
        if isinstance(position, Unit):
            distance_squared = distance ** 2
            return self.subgroup(
                unit
                for unit in self
                if self.bot_object.distance_squared_unit_to_unit(unit, position) < distance_squared
            )
        distances = self.bot_object.distance_units_to_pos(self, position)
        return self.subgroup(unit for unit, dist in zip(self, distances) if dist < distance)

    def further_than(self, distance: Union[int, float], position: Union[Unit, Point2, Point3]) -> Units:
        """
        Returns all units from the object that are further than the given distance from the target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                far_zerglings = enemy_zerglings.further_than(3, my_marine)
                # Contains all zerglings that are distance 3 or more away from the marine (does not include unit radius)

        """
        if not self:
            return self
        if isinstance(position, Unit):
            distance_squared = distance ** 2
            return self.subgroup(
                unit
                for unit in self
                if distance_squared < self.bot_object.distance_squared_unit_to_unit(unit, position)
            )
        distances = self.bot_object.distance_units_to_pos(self, position)
        return self.subgroup(unit for unit, dist in zip(self, distances) if distance < dist)

    def in_distance_between(
        self, position: Union[Unit, Point2, Tuple[float, float]], closest: float, furthest: float
    ) -> Units:
        """
        Returns units that are between the closest(parameter) and the furthest(parameter) to unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                zerglings_filtered = enemy_zerglings.in_distance_between(my_marine, 3, 5)
                # Contains all zerglings between distance 3 and 5 away from the marine (does not include unit radius)

        """
        if not self:
            return self
        if isinstance(position, Unit):
            distance1_squared = closest ** 2
            distance2_squared = furthest ** 2
            return self.subgroup(
                unit
                for unit in self
                if distance1_squared < self.bot_object.distance_squared_unit_to_unit(unit, position) < distance2_squared
            )
        distances = self.bot_object.distance_units_to_pos(self, position)
        return self.subgroup(unit for unit, dist in zip(self, distances) if closest < dist < furthest)

    def closest_n_units(self, position: Union[Unit, Point2], n: int) -> Units:
        """
        Returns the n closest units to the given position or unit.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                zerglings_filtered = enemy_zerglings.closest_n_units(my_marine, 5)
                # Contains 5 zerglings that are the closest to the marine

        """
        if not self:
            return self
        return self.subgroup(self._list_sorted_by_distance_to(position)[:n])

    def furthest_n_units(self, position: Union[Unit, Point2, np.ndarray], n: int) -> Units:
        """
        Returns the n furthest units to the given position or unit.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                zerglings_filtered = enemy_zerglings.furthest_n_units(my_marine, 5)
                # Contains 5 zerglings that are the furthest to the marine

        """
        if not self:
            return self
        return self.subgroup(self._list_sorted_by_distance_to(position)[-n:])

    def in_distance_of_group(self, other_units: Units, distance: float) -> Units:
        """ Returns units that are closer than the distance given from any unit in the other_units object."""
        if not self:
            raise AssertionError("Units object is empty")
        if not self:
            return self
        distance_squared = distance ** 2
        if len(self) == 1:
            if any(
                self.bot_object.distance_squared_unit_to_unit(self[0], target) < distance_squared
                for target in other_units
            ):
                return self
            return self.subgroup([])

        return self.subgroup(
            self_unit
            for self_unit in self
            if any(
                self.bot_object.distance_squared_unit_to_unit(self_unit, other_unit) < distance_squared
                for other_unit in other_units
            )
        )

    def in_closest_distance_to_group(self, other_units: Units) -> Unit:
        """
        Returns unit in shortest distance from any unit in the object to any unit in other_units.

        Loops over all units in the object, then loops over all units in other_units
        and calculates the shortest distance.
        Returns the units that is closest to any unit of 'other_units'.
        """
        if not self:
            raise AssertionError("Units object is empty")
        if not other_units:
            raise AssertionError("Given units object is empty")
        return min(
            self,
            key=lambda self_unit: min(
                self.bot_object.distance_squared_unit_to_unit(self_unit, other_unit) for other_unit in other_units
            ),
        )

    def _list_sorted_closest_to_distance(self, position: Union[Unit, Point2], distance: float) -> List[Unit]:
        """ This function should be a bit faster than using units.sorted(key=lambda u: u.distance_to(position)) """
        if isinstance(position, Unit):
            return sorted(
                self,
                key=lambda unit: abs(self.bot_object.distance_squared_unit_to_unit(unit, position) - distance),
                reverse=True,
            )
        distances = self.bot_object.distance_units_to_pos(self, position)
        unit_dist_dict = {unit.tag: dist for unit, dist in zip(self, distances)}
        return sorted(self, key=lambda unit2: abs(unit_dist_dict[unit2.tag] - distance), reverse=True)

    def n_closest_to_distance(self, position: Union[Point2, np.ndarray], distance: Union[int, float], n: int) -> Units:
        """
        Returns n units that are the closest to the given distance to the the given position.
        For example if the distance is set to 5 and you want 3 units,
        from units with distance [3, 4, 5, 6, 7] to position, the units with distance [4, 5, 6] will be returned
        """
        return self.subgroup(self._list_sorted_closest_to_distance(position=position, distance=distance)[:n])

    def n_furthest_to_distance(self, position: Union[Point2, np.ndarray], distance: Union[int, float], n: int) -> Units:
        """ Inverse of the function 'n_closest_to_distance', returns the furthest units instead """
        return self.subgroup(self._list_sorted_closest_to_distance(position=position, distance=distance)[-n:])

    def subgroup(self, units):
        """ Creates a new mutable Units object from Units or list object."""
        return Units(units, self.bot_object)

    def filter(self, pred: callable) -> Units:
        """
        Filters the current Units object and returns a new Units object.

        Example::

            from sc2.ids.unit_typeid import UnitTypeId
            my_marines = self.units.filter(lambda unit: unit.type_id == UnitTypeId.MARINE)

            completed_structures = self.structures.filter(lambda structure: structure.is_ready)

            queens_with_energy = self.units.filter(lambda u: u.type_id == UnitTypeId.QUEEN and u.energy >= 25)

        """
        if not callable(pred):
            raise AssertionError("Function is not callable")
        return self.subgroup(filter(pred, self))

    def sorted(self, key: callable, reverse: bool = False) -> Units:
        """ Sort it by the given function"""
        return self.subgroup(sorted(self, key=key, reverse=reverse))

    def _list_sorted_by_distance_to(self, position: Union[Unit, Point2], reverse: bool = False) -> List[Unit]:
        """ This function should be a bit faster than using units.sorted(key=lambda u: u.distance_to(position)) """
        if isinstance(position, Unit):
            return sorted(
                self, key=lambda unit: self.bot_object.distance_squared_unit_to_unit(unit, position), reverse=reverse
            )
        distances = self.bot_object.distance_units_to_pos(self, position)
        unit_dist_dict = {unit.tag: dist for unit, dist in zip(self, distances)}
        return sorted(self, key=lambda unit2: unit_dist_dict[unit2.tag], reverse=reverse)

    def sorted_by_distance_to(self, position: Union[Unit, Point2], reverse: bool = False) -> Units:
        """ This function should be a bit faster than using units.sorted(key=lambda u: u.distance_to(position)) """
        return self.subgroup(self._list_sorted_by_distance_to(position, reverse=reverse))

    def tags_in(self, other: Union[Set[int], List[int], Dict[int, Any]]) -> Units:
        """Filters all units that have their tags in the 'other' set/list/dict

        Example::

            my_inject_queens = self.units.tags_in(self.queen_tags_assigned_to_do_injects)

            # Do not use the following as it is slower because it first loops over all units to filter out if they
            are queens and loops over those again to check if their tags are in the list/set

            my_inject_queens_slow = self.units(QUEEN).tags_in(self.queen_tags_assigned_to_do_injects)

        """
        return self.filter(lambda unit: unit.tag in other)

    def tags_not_in(self, other: Union[Set[int], List[int], Dict[int, Any]]) -> Units:
        """
        Filters all units that have their tags not in the 'other' set/list/dict

        Example::

            my_non_inject_queens = self.units.tags_not_in(self.queen_tags_assigned_to_do_injects)

            # Do not use the following as it is slower because it first loops over all units to filter out if they
            are queens and loops over those again to check if their tags are in the list/set

            my_non_inject_queens_slow = self.units(QUEEN).tags_not_in(self.queen_tags_assigned_to_do_injects)

        """
        return self.filter(lambda unit: unit.tag not in other)

    def of_type(self, other: Union[UnitTypeId, Set[UnitTypeId], List[UnitTypeId], Dict[UnitTypeId, Any]]) -> Units:
        """
        Filters all units that are of a specific type

        Example::

            # Use a set instead of lists in the argument
            some_attack_units = self.units.of_type({ZERGLING, ROACH, HYDRALISK, BROODLORD})

        """
        if isinstance(other, UnitTypeId):
            other = {other}
        elif isinstance(other, list):
            other = set(other)
        return self.filter(lambda unit: unit.type_id in other)

    def exclude_type(self, other: Union[UnitTypeId, Set[UnitTypeId], List[UnitTypeId], Dict[UnitTypeId, Any]]) -> Units:
        """
        Filters all units that are not of a specific type

        Example::

            # Use a set instead of lists in the argument
            ignore_units = self.enemy_units.exclude_type({LARVA, EGG, OVERLORD})

        """
        if isinstance(other, UnitTypeId):
            other = {other}
        elif isinstance(other, list):
            other = set(other)
        return self.filter(lambda unit: unit.type_id not in other)

    def same_tech(self, other: Set[UnitTypeId]) -> Units:
        """
        Returns all structures that have the same base structure.

        Untested: This should return the equivalents for WarpPrism, Observer, Overseer, SupplyDepot and others

        Example::

            # All command centers, flying command centers, orbital commands, flying orbital commands, planetary fortress
            terran_townhalls = self.townhalls.same_tech(UnitTypeId.COMMANDCENTER)

            # All hatcheries, lairs and hives
            zerg_townhalls = self.townhalls.same_tech({UnitTypeId.HATCHERY})

            # All spires and greater spires
            spires = self.townhalls.same_tech({UnitTypeId.SPIRE})
            # The following returns the same
            spires = self.townhalls.same_tech({UnitTypeId.GREATERSPIRE})

            # This also works with multiple unit types
            zerg_townhalls_and_spires = self.structures.same_tech({UnitTypeId.HATCHERY, UnitTypeId.SPIRE})

        """
        if not isinstance(other, set):
            raise AssertionError(
                (
                    f"Please use a set as this filter function is already fairly slow. For example"
                    + " 'self.units.same_tech({UnitTypeId.LAIR})'"
                )
            )
        tech_alias_types: Set[int] = {u.value for u in other}
        unit_data = self.bot_object.game_data_local.units
        for unit_type in other:
            for same in unit_data[unit_type.value].proto.tech_alias:
                tech_alias_types.add(same)
        return self.filter(
            lambda unit: unit.proto.unit_type in tech_alias_types
            or any(alias in tech_alias_types for alias in unit.type_data.proto.tech_alias)
        )

    def same_unit(self, other: Union[UnitTypeId, Set[UnitTypeId], List[UnitTypeId], Dict[UnitTypeId, Any]]) -> Units:
        """
        Returns all units that have the same base unit while being in different modes.

        Untested: This should return the equivalents for WarpPrism, Observer, Overseer, SupplyDepot and other units
        that have different modes but still act as the same unit

        Example::

            # All command centers on the ground and flying
            ccs = self.townhalls.same_unit(UnitTypeId.COMMANDCENTER)

            # All orbital commands on the ground and flying
            ocs = self.townhalls.same_unit(UnitTypeId.ORBITALCOMMAND)

            # All roaches and burrowed roaches
            roaches = self.units.same_unit(UnitTypeId.ROACH)
            # This is useful because roach has a different type id when burrowed
            burrowed_roaches = self.units(UnitTypeId.ROACHBURROWED)

        """
        if isinstance(other, UnitTypeId):
            other = {other}
        unit_alias_types: Set[int] = {u.value for u in other}
        unit_data = self.bot_object.game_data_local.units
        for unit_type in other:
            unit_alias_types.add(unit_data[unit_type.value].proto.unit_alias)
        unit_alias_types.discard(0)
        return self.filter(
            lambda unit: unit.proto.unit_type in unit_alias_types or unit.type_data.proto.unit_alias in unit_alias_types
        )

    @property
    def center(self) -> Point2:
        """ Returns the central position of all units. """
        if not self:
            raise AssertionError("Units object is empty")
        amount = len(self)
        return Point2(
            (
                sum(unit.proto.pos.x for unit in self) / amount,
                sum(unit.proto.pos.y for unit in self) / amount,
            )
        )

    @property
    def selected(self) -> Units:
        """ Returns all units that are selected by the current player. """
        return self.filter(lambda unit: unit.is_selected)

    @property
    def tags(self) -> Set[int]:
        """ Returns all unit tags as a set. """
        return {unit.tag for unit in self}

    @property
    def ready(self) -> Units:
        """ Returns all structures that are constructed. """
        return self.filter(lambda unit: unit.is_ready)

    @property
    def not_ready(self) -> Units:
        """ Returns all structures that are not constructed. """
        return self.filter(lambda unit: not unit.is_ready)

    @property
    def idle(self) -> Units:
        """ Returns all units or structures that are doing nothing"""
        return self.filter(lambda unit: unit.is_idle)

    @property
    def flying(self) -> Units:
        """ Returns all units that are flying. """
        return self.filter(lambda unit: unit.is_flying)

    @property
    def not_flying(self) -> Units:
        """ Returns all units that are not flying. """
        return self.filter(lambda unit: not unit.is_flying)

    @property
    def gathering(self) -> Units:
        """ Returns all workers that are mining (gather command). """
        return self.filter(lambda unit: unit.is_gathering)

    @property
    def returning(self) -> Units:
        """ Returns all workers that are carrying resources and returning to a townhall. """
        return self.filter(lambda unit: unit.is_returning)

    @property
    def collecting(self) -> Units:
        """ Returns all workers that are mining or returning resources. """
        return self.filter(lambda unit: unit.is_collecting)

    @property
    def visible(self) -> Units:
        """ Returns all units or structures that are visible."""
        return self.filter(lambda unit: unit.is_visible)

    @property
    def mineral_field(self) -> Units:
        """ Returns all units that are mineral fields. """
        return self.filter(lambda unit: unit.is_mineral_field)

    @property
    def vespene_geyser(self) -> Units:
        """ Returns all units that are vespene geysers. """
        return self.filter(lambda unit: unit.is_vespene_geyser)

    @property
    def prefer_idle(self) -> Units:
        """ Sorts units based on if they are idle. Idle units come first. """
        return self.sorted(lambda unit: unit.is_idle, reverse=True)

    @property
    def prefer_healthy(self) -> Units:
        """ Sorts units based on if they are healthy. Healthier units come first. """
        return self.sorted(lambda unit: unit.health, reverse=True)


class UnitSelection(Units):
    """ Not sure what it does"""

    def __init__(self, parent, selection=None):
        if isinstance(selection, UnitTypeId):
            super().__init__((unit for unit in parent if unit.type_id == selection), parent.bot_object)
        elif isinstance(selection, set):
            if not all(isinstance(t, UnitTypeId) for t in selection):
                raise AssertionError(f"Not all ids in selection are of type UnitTypeId")
            super().__init__((unit for unit in parent if unit.type_id in selection), parent.bot_object)
        elif selection is None:
            super().__init__((unit for unit in parent), parent.bot_object)
        else:
            if not isinstance(selection, (UnitTypeId, set)):
                raise AssertionError(f"selection is not None or of type UnitTypeId or Set[UnitTypeId]")
