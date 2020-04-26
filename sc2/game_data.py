"""
Groups useful data from units, abilities and game
"""
from __future__ import annotations

from bisect import bisect_left
from functools import lru_cache
from typing import Dict, List, Optional

from .data import ATTRIBUTE, RACE
from .ids.ability_id import AbilityId
from .ids.unit_typeid import UnitTypeId
from .unit_command import UnitCommand

FREE_ABILITIES = {"Lower", "Raise", "Land", "Lift", "Hold", "Harvest"}


class GameData:
    """ Calculates cost info for the abilities, units and upgrades"""

    def __init__(self, data):
        """
        :param data:
        """
        ids = set(a.value for a in AbilityId if a.value)
        self.abilities = {a.ability_id: AbilityData(self, a) for a in data.abilities if a.ability_id in ids}
        self.units = {u.unit_id: UnitTypeData(self, u) for u in data.units if u.available}
        self.upgrades = {u.upgrade_id: UpgradeData(self, u) for u in data.upgrades}
        self.unit_types: Dict[int, UnitTypeId] = {}

    @lru_cache(maxsize=256)
    def calculate_ability_cost(self, ability) -> Cost:
        """ Calculates cost info for the abilities, units and upgrades"""
        if isinstance(ability, AbilityId):
            ability = self.abilities[ability.value]
        elif isinstance(ability, UnitCommand):
            ability = self.abilities[ability.ability.value]

        if not isinstance(ability, AbilityData):
            raise AssertionError(f"C: {ability}")

        for unit in self.units.values():
            if unit.creation_ability is None:
                continue

            if not AbilityData.id_exists(unit.creation_ability.id.value):
                continue

            if unit.creation_ability.is_free_morph:
                continue

            if unit.creation_ability == ability:
                if unit.id == UnitTypeId.ZERGLING:
                    return Cost(unit.cost.minerals * 2, unit.cost.vespene * 2, unit.cost.time)
                morph_cost = unit.morph_cost
                if morph_cost:
                    return morph_cost
                return unit.cost_zerg_corrected

        for upgrade in self.upgrades.values():
            if upgrade.research_ability == ability:
                return upgrade.cost

        return Cost(0, 0)


class AbilityData:
    """ Some info about abilities"""

    ability_ids: List[int] = [ability_id.value for ability_id in AbilityId][1:]

    @classmethod
    def id_exists(cls, ability_id):
        """Check if the given AbilityID exists"""
        if not isinstance(ability_id, int):
            raise AssertionError(f"Wrong type: {ability_id} is not int")
        if ability_id == 0:
            return False
        i = bisect_left(cls.ability_ids, ability_id)
        return i != len(cls.ability_ids) and cls.ability_ids[i] == ability_id

    def __init__(self, game_data, proto):
        self._game_data = game_data
        self.proto = proto
        if self.id == 0:
            raise AssertionError()

    def __repr__(self) -> str:
        return f"AbilityData(name={self.proto.button_name})"

    @property
    def id(self) -> AbilityId:
        """ Returns the generic remap ID. See sc2/dicts/generic_redirect_abilities.py """
        if self.proto.remaps_to_ability_id:
            return AbilityId(self.proto.remaps_to_ability_id)
        return AbilityId(self.proto.ability_id)

    @property
    def exact_id(self) -> AbilityId:
        """ Returns the exact ID of the ability """
        return AbilityId(self.proto.ability_id)

    @property
    def link_name(self) -> str:
        """ For Stimpack this returns 'BarracksTechLabResearch' """
        return self.proto.link_name

    @property
    def button_name(self) -> str:
        """ For Stimpack this returns 'Stimpack' """
        return self.proto.button_name

    @property
    def friendly_name(self) -> str:
        """ For Stimpack this returns 'Research Stimpack' """
        return self.proto.friendly_name

    @property
    def is_free_morph(self) -> bool:
        """ This returns True if the ability is in {"Lower", "Raise", "Land", "Lift", "Hold", "Harvest"}"""
        if any(free in self.proto.link_name for free in FREE_ABILITIES):
            return True
        return False

    @property
    def cost(self) -> Cost:
        """returns the ability cost"""
        return self._game_data.calculate_ability_cost(self.id)


class UnitTypeData:
    """ Some info about units"""

    def __init__(self, game_data: GameData, proto):
        """
        :param game_data:
        :param proto:
        """
        # The ability_id for lurkers is
        # LURKERASPECTMPFROMHYDRALISKBURROWED_LURKERMPFROMHYDRALISKBURROWED
        # instead of the correct MORPH_LURKER.
        if proto.unit_id == UnitTypeId.LURKERMP.value:
            proto.ability_id = AbilityId.MORPH_LURKER.value

        self._game_data = game_data
        self.proto = proto

    def __repr__(self) -> str:
        return f"UnitTypeData(name={self.name})"

    @property
    def id(self) -> UnitTypeId:
        """ Returns the unit id"""
        return UnitTypeId(self.proto.unit_id)

    @property
    def name(self) -> str:
        """ Returns the unit name"""
        return self.proto.name

    @property
    def creation_ability(self) -> Optional[AbilityData]:
        """ Returns the ability responsible to create the unit """
        if self.proto.ability_id == 0:
            return None
        if self.proto.ability_id not in self._game_data.abilities:
            return None
        return self._game_data.abilities[self.proto.ability_id]

    @property
    def attributes(self) -> List[ATTRIBUTE]:
        """ Returns the unit attributes """
        return self.proto.attributes

    def has_attribute(self, attr) -> bool:
        """ Returns True if the unit has given attribute """
        if not isinstance(attr, ATTRIBUTE):
            raise AssertionError()
        return attr in self.attributes

    @property
    def has_minerals(self) -> bool:
        """ Returns True if the unit has minerals, only True for different types of mineral patches """
        return self.proto.has_minerals

    @property
    def has_vespene(self) -> bool:
        """ Returns True if the unit has vespene, only True for different types of geysers """
        return self.proto.has_vespene

    @property
    def cargo_size(self) -> int:
        """ How much cargo this unit uses up in cargo_space """
        return self.proto.cargo_size

    @property
    def tech_requirement(self) -> Optional[UnitTypeId]:
        """ Tech-building requirement of buildings - may work for units but unreliably """
        if self.proto.tech_requirement == 0:
            return None
        if self.proto.tech_requirement not in self._game_data.units:
            return None
        return UnitTypeId(self.proto.tech_requirement)

    @property
    def tech_alias(self) -> Optional[List[UnitTypeId]]:
        """ Building tech equality, e.g. OrbitalCommand is the same as CommandCenter
        Building tech equality, e.g. Hive is the same as Lair and Hatchery
        For Hive, this returns [UnitTypeId.Hatchery, UnitTypeId.Lair]
        For SCV, this returns None """
        return_list = [
            UnitTypeId(tech_alias) for tech_alias in self.proto.tech_alias if tech_alias in self._game_data.units
        ]
        return return_list if return_list else None

    @property
    def unit_alias(self) -> Optional[UnitTypeId]:
        """ Building type equality, e.g. FlyingOrbitalCommand is the same as OrbitalCommand """
        if self.proto.unit_alias == 0:
            return None
        if self.proto.unit_alias not in self._game_data.units:
            return None
        # For flying OrbitalCommand, this returns UnitTypeId.OrbitalCommand
        return UnitTypeId(self.proto.unit_alias)

    @property
    def race(self) -> RACE:
        """ Returns the race of the unit"""
        return RACE(self.proto.race)

    @property
    def cost(self) -> Cost:
        """ Returns the cost of the unit"""
        return Cost(self.proto.mineral_cost, self.proto.vespene_cost, self.proto.build_time)

    @property
    def cost_zerg_corrected(self) -> Cost:
        """ This returns 25 for extractor and 200 for spawning pool instead of 75 and 250 respectively """
        if self.race == RACE.Zerg and ATTRIBUTE.Structure.value in self.attributes:
            return Cost(self.proto.mineral_cost - 50, self.proto.vespene_cost, self.proto.build_time)
        return self.cost

    @property
    def morph_cost(self) -> Optional[Cost]:
        """ This returns 150 minerals for OrbitalCommand instead of 550 """
        if self.tech_alias is None or self.tech_alias[0] in {UnitTypeId.TECHLAB, UnitTypeId.REACTOR}:
            return None
        tech_alias_cost_minerals = max(
            self._game_data.units[tech_alias.value].cost.minerals for tech_alias in self.tech_alias
        )
        tech_alias_cost_vespene = max(
            self._game_data.units[tech_alias.value].cost.vespene for tech_alias in self.tech_alias
        )
        return Cost(
            self.proto.mineral_cost - tech_alias_cost_minerals,
            self.proto.vespene_cost - tech_alias_cost_vespene,
            self.proto.build_time,
        )


class UpgradeData:
    """ Some info about Upgrades"""

    def __init__(self, game_data: GameData, proto):
        """
        :param game_data:
        :param proto:
        """
        self._game_data = game_data
        self.proto = proto

    def __repr__(self):
        return f"UpgradeData({self.name} - research ability: {self.research_ability}, {self.cost})"

    @property
    def name(self) -> str:
        """ Returns the name of the upgrade"""
        return self.proto.name

    @property
    def research_ability(self) -> Optional[AbilityData]:
        """ Returns the ability responsible to research the upgrade"""
        if self.proto.ability_id == 0:
            return None
        if self.proto.ability_id not in self._game_data.abilities:
            return None
        return self._game_data.abilities[self.proto.ability_id]

    @property
    def cost(self) -> Cost:
        """ Returns the cost of the upgrade"""
        return Cost(self.proto.mineral_cost, self.proto.vespene_cost, self.proto.research_time)


class Cost:
    """ Groups the cost of everything(vespene, minerals, and completion time) it misses the food cost tho"""

    def __init__(self, minerals: int, vespene: int, time: float = None):
        self.minerals = minerals
        self.vespene = vespene
        self.time = time

    def __repr__(self) -> str:
        return f"Cost({self.minerals}, {self.vespene})"

    def __eq__(self, other: Cost) -> bool:
        return self.minerals == other.minerals and self.vespene == other.vespene

    def __ne__(self, other: Cost) -> bool:
        return self.minerals != other.minerals or self.vespene != other.vespene

    def __bool__(self) -> bool:
        return bool(self.minerals) or bool(self.vespene)

    def __add__(self, other) -> Cost:
        if not other:
            return self
        if not self:
            return other
        if self.time is None:
            time = other.time
        elif other.time is None:
            time = self.time
        else:
            time = self.time + other.time
        return self.__class__(self.minerals + other.minerals, self.vespene + other.vespene, time=time)

    def __sub__(self, other) -> Cost:
        if not isinstance(other, Cost):
            raise AssertionError()
        if self.time is None:
            time = other.time
        elif other.time is None:
            time = self.time
        else:
            time = self.time - other.time
        return self.__class__(self.minerals - other.minerals, self.vespene - other.vespene, time=time)

    def __mul__(self, other: int) -> Cost:
        return self.__class__(self.minerals * other, self.vespene * other, time=self.time)

    def __rmul__(self, other: int) -> Cost:
        return self.__class__(self.minerals * other, self.vespene * other, time=self.time)
