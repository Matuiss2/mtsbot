"""
Base class for the bots
"""
from __future__ import annotations

import itertools
import logging
import math
import random
import time
from collections import Counter
from contextlib import suppress
from typing import Dict, List, Optional, Set, Tuple, Union, TYPE_CHECKING

from s2clientprotocol import sc2api_pb2 as sc_pb

from .cache import property_cache_forever, property_cache_once_per_frame_no_copy
from .constants import (
    FakeEffectID,
    abilityid_to_unittypeid,
    geyser_ids,
    mineral_ids,
    TERRAN_TECH_REQUIREMENT,
    PROTOSS_TECH_REQUIREMENT,
    ZERG_TECH_REQUIREMENT,
    ALL_GAS,
    EQUIVALENTS_FOR_TECH_PROGRESS,
    TERRAN_STRUCTURES_REQUIRE_SCV,
)
from .data import ACTION_RESULT, ALERT, RACE, RESULT, TARGET, race_townhalls, race_worker
from .dicts.unit_research_abilities import RESEARCH_INFO
from .dicts.unit_train_build_abilities import TRAIN_INFO
from .dicts.unit_trained_from import UNIT_TRAINED_FROM
from .dicts.upgrade_researched_from import UPGRADE_RESEARCHED_FROM
from .distances import DistanceCalculation
from .game_data import AbilityData, GameData
from .game_data import Cost

# Imports for mypy and pycharm autocomplete as well as sphinx auto-documentation
from .game_state import Blip, EffectData, GameState
from .ids.ability_id import AbilityId
from .ids.unit_typeid import UnitTypeId
from .ids.upgrade_id import UpgradeId
from .pixel_map import PixelMap
from .position import Point2, Point3
from .unit import Unit
from .unit_command import UnitCommand
from .units import Units

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .game_info import GameInfo, Ramp
    from .client import Client


class BotAI(DistanceCalculation):
    """Base class for bots."""

    def __init__(self):
        super().__init__()
        self.opponent_id: str = None
        self.realtime: bool = False
        self.realtime: bool = False
        self.all_units: Units = Units([], self)
        self.units: Units = Units([], self)
        self.workers: Units = Units([], self)
        self.townhalls: Units = Units([], self)
        self.structures: Units = Units([], self)
        self.gas_buildings: Units = Units([], self)
        self.enemy_units: Units = Units([], self)
        self.enemy_structures: Units = Units([], self)
        self.resources: Units = Units([], self)
        self.destructible: Units = Units([], self)
        self.watchtowers: Units = Units([], self)
        self.mineral_field: Units = Units([], self)
        self.vespene_geyser: Units = Units([], self)
        self.larva: Units = Units([], self)
        self.techlab_tags: Set[int] = set()
        self.reactor_tags: Set[int] = set()
        self.distance_calculation_method: int = 2
        self.minerals: int = 0
        self.vespene: int = 0
        self.supply_army: float = 0
        self.supply_workers: float = 0
        self.supply_cap: float = 0
        self.supply_used: float = 0
        self.supply_left: float = 0
        self.idle_worker_count: int = None
        self.army_count: int = 0
        self.warp_gate_count: int = 0
        self.actions: List[UnitCommand] = []
        self.blips: Set[Blip] = set()
        self.cached_main_base_ramp = None
        self._units_created: Counter = Counter()
        self._unit_tags_seen_this_game: Set[int] = set()
        self._units_previous_map: Dict[int, Unit] = dict()
        self._structures_previous_map: Dict[int, Unit] = dict()
        self._enemy_units_previous_map: Dict[int, Unit] = dict()
        self._enemy_structures_previous_map: Dict[int, Unit] = dict()
        self._previous_upgrades: Set[UpgradeId] = set()
        self._time_before_step: float = None
        self._time_after_step: float = None
        self._min_step_time: float = math.inf
        self._max_step_time: float = 0
        self._last_step_step_time: float = 0
        self._total_time_in_on_step: float = 0
        self._total_steps_iterations: int = 0
        self.unit_tags_received_action: Set[int] = set()
        self._client: Client = None
        self.player_id: int = None
        self._game_info: GameInfo = None
        self.game_data_local: GameData = None
        self.race: RACE = None
        self.enemy_race: RACE = None

    def initialize_variables(self):
        """ Called from main.py internally """
        super().__init__()
        # The bot ID will stay the same each game so your bot can "adapt" to the opponent
        if not hasattr(self, "opponent_id"):
            self.opponent_id: str = None
        # Select distance calculation method, see distances.py: _distances_override_functions function
        if not hasattr(self, "distance_calculation_method"):
            self.distance_calculation_method: int = 2
        # This value will be set to True by main.py in self.prepare_start if game is played in realtime
        # (if true, the bot will have limited time per step)
        self.realtime: bool = False
        self.all_units: Units = Units([], self)
        self.units: Units = Units([], self)
        self.workers: Units = Units([], self)
        self.townhalls: Units = Units([], self)
        self.structures: Units = Units([], self)
        self.gas_buildings: Units = Units([], self)
        self.enemy_units: Units = Units([], self)
        self.enemy_structures: Units = Units([], self)
        self.resources: Units = Units([], self)
        self.destructible: Units = Units([], self)
        self.watchtowers: Units = Units([], self)
        self.mineral_field: Units = Units([], self)
        self.vespene_geyser: Units = Units([], self)
        self.larva: Units = Units([], self)
        self.techlab_tags: Set[int] = set()
        self.reactor_tags: Set[int] = set()
        self.minerals: int = None
        self.vespene: int = None
        self.supply_army: float = None
        self.supply_workers: float = None  # Doesn't include workers in production
        self.supply_cap: float = None
        self.supply_used: float = None
        self.supply_left: float = None
        self.idle_worker_count: int = None
        self.army_count: int = None
        self.warp_gate_count: int = None
        self.actions: List[UnitCommand] = []
        self.blips: Set[Blip] = set()
        self._units_created: Counter = Counter()
        self._unit_tags_seen_this_game: Set[int] = set()
        self._units_previous_map: Dict[int, Unit] = dict()
        self._structures_previous_map: Dict[int, Unit] = dict()
        self._enemy_units_previous_map: Dict[int, Unit] = dict()
        self._enemy_structures_previous_map: Dict[int, Unit] = dict()
        self._previous_upgrades: Set[UpgradeId] = set()
        self._time_before_step: float = None
        self._time_after_step: float = None
        self._min_step_time: float = math.inf
        self._max_step_time: float = 0
        self._last_step_step_time: float = 0
        self._total_time_in_on_step: float = 0
        self._total_steps_iterations: int = 0
        # does not give the same larva two orders - cleared every frame
        self.unit_tags_received_action: Set[int] = set()

    @property
    def time(self) -> float:
        """ Returns time in seconds, assumes the game is played on 'faster' """
        return self.state.game_loop / 22.4

    @property
    def time_formatted(self) -> str:
        """ Returns time as string in min:sec format """
        seconds = self.time
        return f"{int(seconds // 60):02}:{int(seconds % 60):02}"

    @property
    def step_time(self) -> Tuple[float, float, float, float]:
        """ Returns a tuple of step duration in milliseconds.
        First value is the minimum step duration - the shortest the bot ever took
        Second value is the average step duration
        Third value is the maximum step duration - the longest the bot ever took (including on_start())
        Fourth value is the step duration the bot took last iteration
        If called in the first iteration, it returns (inf, 0, 0, 0) """
        avg_step_duration = (
            (self._total_time_in_on_step / self._total_steps_iterations) if self._total_steps_iterations else 0
        )
        return (
            self._min_step_time * 1000,
            avg_step_duration * 1000,
            self._max_step_time * 1000,
            self._last_step_step_time * 1000,
        )

    @property
    def game_info(self) -> GameInfo:
        """ See game_info.py """
        return self._game_info

    @property
    def game_data(self) -> GameData:
        """ See game_data.py """
        return self.game_data_local

    @property
    def client(self) -> Client:
        """ See client.py """
        return self._client

    def alert(self, alert_code: ALERT) -> bool:
        """
        Check if alert is triggered in the current step. Possible alerts are listed here
        https://github.com/Blizzard/s2client-proto/blob/e38efed74c03bec90f74b330ea1adda9215e655f/s2clientprotocol
        /sc2api.proto#L679-L702

        Example use:

            from sc2.data import Alert
            if self.alert(Alert.AddOnComplete):
                print("Addon Complete")

        Alert codes::

            AlertError
            AddOnComplete
            BuildingComplete
            BuildingUnderAttack
            LarvaHatched
            MergeComplete
            MineralsExhausted
            MorphComplete
            MothershipComplete
            MULEExpired
            NuclearLaunchDetected
            NukeComplete
            NydusWormDetected
            ResearchComplete
            TrainError
            TrainUnitComplete
            TrainWorkerComplete
            TransformationComplete
            UnitUnderAttack
            UpgradeComplete
            VespeneExhausted
            WarpInComplete

        :param alert_code:
        """
        if not isinstance(alert_code, ALERT):
            raise AssertionError(f"alert_code {alert_code} is no Alert")
        return alert_code.value in self.state.alerts

    @property
    def start_location(self) -> Point2:
        """
        Returns the spawn location of the bot, using the position of the first created townhall.
        This will be None if the bot is run on an arcade or custom map that does not feature townhalls at game start.
        """
        return self._game_info.player_start_location

    @property
    def enemy_start_locations(self) -> List[Point2]:
        """Possible start locations for enemies."""
        return self._game_info.start_locations

    @property
    def main_base_ramp(self) -> Ramp:
        """ Returns the Ramp instance of the closest main-ramp to start location.
        Look in game_info.py for more information about the Ramp class

        Example: See terran ramp wall bot
        """
        if hasattr(self, "cached_main_base_ramp"):
            return self.cached_main_base_ramp
        # The reason for len(ramp.upper) in {2, 5} is:
        # ParaSite map has 5 upper points, and most other maps have 2 upper points at the main ramp.
        # The map Acolyte has 4 upper points at the wrong ramp (which is closest to the start position).
        try:
            self.cached_main_base_ramp = min(
                (ramp for ramp in self.game_info.map_ramps if len(ramp.upper) in {2, 5}),
                key=lambda r: self.start_location.distance_to(r.top_center),
            )
        except ValueError:
            # Hardcoded hotfix for Honorgrounds LE map, as that map has a large main base ramp with in-base natural
            self.cached_main_base_ramp = min(
                (ramp for ramp in self.game_info.map_ramps if len(ramp.upper) in {4, 9}),
                key=lambda r: self.start_location.distance_to(r.top_center),
            )
        return self.cached_main_base_ramp

    @property_cache_forever
    def expansion_locations(self) -> Dict[Point2, Units]:
        """
        Returns dict with the correct expansion position Point2 object as key,
        resources (mineral field and vespene geyser) as value.
        """
        resource_spread_threshold = 8.5
        geysers = self.vespene_geyser
        resource_groups = [
            [resource]
            for resource in self.resources
            if resource.name != "MineralField450"
        ]
        merged_group = True
        while merged_group:
            merged_group = False
            for group_a, group_b in itertools.combinations(resource_groups, 2):
                if any(
                    resource_a.distance_to(resource_b) <= resource_spread_threshold
                    for resource_a, resource_b in itertools.product(group_a, group_b)
                ):
                    resource_groups.remove(group_a)
                    resource_groups.remove(group_b)
                    resource_groups.append(group_a + group_b)
                    merged_group = True
                    break
        offset_range = 7
        offsets = [
            (x, y)
            for x, y in itertools.product(range(-offset_range, offset_range + 1), repeat=2)
            if math.hypot(x, y) <= 8
        ]
        centers = {}
        for resources in resource_groups:
            amount = len(resources)
            center_x = int(sum(resource.position.x for resource in resources) / amount) + 0.5
            center_y = int(sum(resource.position.y for resource in resources) / amount) + 0.5
            possible_points = (Point2((offset[0] + center_x, offset[1] + center_y)) for offset in offsets)
            possible_points = (
                point
                for point in possible_points
                if self._game_info.placement_grid[point.rounded] == 1
                and all(point.distance_to(resource) > (7 if resource in geysers else 6) for resource in resources)
            )
            result = min(possible_points, key=lambda point: sum(point.distance_to(resource) for resource in resources))
            centers[result] = resources
        return centers

    @property
    def units_created(self) -> Counter:
        """ Returns a Counter for all your units and buildings you have created so far.

        This may be used for statistics (at the end of the game) or for strategic decision making.

        CAUTION: This does not properly work at the moment for morphing units and structures. Please use the
        'on_unit_type_changed' event to add these morphing unit types manually to 'self._units_created'. Issues would
        arise in e.g. siege tank morphing to sieged tank, and then morphing back (suddenly the counter counts 2 tanks
        have been created).

        Examples::

            # Give attack command to enemy base every time 10 marines have been trained
            async def on_unit_created(self, unit: Unit):
                if unit.type_id == UnitTypeId.MARINE:
                    if self.units_created[MARINE] % 10 == 0:
                        for marine in self.units(UnitTypeId.MARINE):
                            self.do(marine.attack(self.enemy_start_locations[0]))
        """
        return self._units_created

    def _correct_zerg_supply(self):
        """ The client incorrectly rounds zerg supply down instead of up (see
            https://github.com/Blizzard/s2client-proto/issues/123), so self.supply_used
            and friends return the wrong value when there are an odd number of zerglings
            and banelings. This function corrects the bad values. """
        half_supply_units = {
            UnitTypeId.ZERGLING,
            UnitTypeId.ZERGLINGBURROWED,
            UnitTypeId.BANELING,
            UnitTypeId.BANELINGBURROWED,
            UnitTypeId.BANELINGCOCOON,
        }
        correction = len(self.units(half_supply_units)) % 2
        self.supply_used += correction
        self.supply_army += correction
        self.supply_left -= correction

    async def get_available_abilities(
        self, units: Union[List[Unit], Units], ignore_resource_requirements: bool = False
    ) -> List[List[AbilityId]]:
        """ Returns available abilities of one or more units. Right now only checks cooldown, energy cost,
        and whether the ability has been researched.

        Examples::

            units_abilities = await self.get_available_abilities(self.units)

        or::

            units_abilities = await self.get_available_abilities([self.units.random])

        :param units:
        :param ignore_resource_requirements: """
        return await self._client.query_available_abilities(units, ignore_resource_requirements)

    async def expand_now(
        self, building: UnitTypeId = None, max_distance: float = 10, location: Optional[Point2] = None
    ):
        """ Finds the next possible expansion via 'self.get_next_expansion()'. If the target expansion is blocked (
        e.g. an enemy unit), it will misplace the expansion.

        :param building:
        :param max_distance:
        :param location: """

        if not building:
            # self.race is never Race.Random
            start_townhall_type = {
                RACE.Protoss: UnitTypeId.NEXUS,
                RACE.Terran: UnitTypeId.COMMANDCENTER,
                RACE.Zerg: UnitTypeId.HATCHERY,
            }
            building = start_townhall_type[self.race]

        if not isinstance(building, UnitTypeId):
            raise AssertionError(f"{building} is no UnitTypeId")

        if not location:
            location = await self.get_next_expansion()
        if not location:
            LOGGER.warning("Trying to expand_now() but bot is out of locations to expand to")
            return
        await self.build(building, near=location, max_distance=max_distance, random_alternative=False, placement_step=1)

    async def get_next_expansion(self) -> Optional[Point2]:
        """Find next expansion location."""

        closest = None
        distance = math.inf
        for expansion_location in self.expansion_locations:

            taken_expansion = [th for th in self.townhalls if th.distance_to(expansion_location) < 15]
            if any(taken_expansion):
                continue

            start_position = self._game_info.player_start_location
            distance_to_starting_base = await self._client.query_pathway(start_position, expansion_location)
            if distance_to_starting_base is None:
                continue

            if distance_to_starting_base < distance:
                distance = distance_to_starting_base
                closest = expansion_location

        return closest

    @property
    def owned_expansions(self) -> Dict[Point2, Unit]:
        """List of expansions owned by the player."""
        owned = {}
        for expansion_location in self.expansion_locations:
            taken_expansion = next((x for x in self.townhalls if x.distance_to(expansion_location) < 15), None)
            if taken_expansion:
                owned[expansion_location] = taken_expansion
        return owned

    def calculate_supply_cost(self, unit_type: UnitTypeId) -> float:
        """
        This function calculates the required supply to train or morph a unit. The total supply of a baneling is 0.5,
        but a zergling already uses up 0.5 supply, so the morph supply cost is 0. The total supply of a ravager is 3,
        but a roach already uses up 2 supply, so the morph supply cost is 1. The required supply to build zerglings
        is 1 because they pop in pairs, so this function returns 1 because the larva morph command requires 1 free
        supply.

        Example::

            roach_supply_cost = self.calculate_supply_cost(UnitTypeId.ROACH) # Is 2
            ravager_supply_cost = self.calculate_supply_cost(UnitTypeId.RAVAGER) # Is 1
            baneling_supply_cost = self.calculate_supply_cost(UnitTypeId.BANELING) # Is 0

        :param unit_type: """
        if unit_type in {UnitTypeId.ZERGLING}:
            return 1
        unit_supply_cost = self.game_data_local.units[unit_type.value].proto.food_required
        if unit_supply_cost > 0 and unit_type in UNIT_TRAINED_FROM and len(UNIT_TRAINED_FROM[unit_type]) == 1:
            for producer in UNIT_TRAINED_FROM[unit_type]:
                producer_unit_data = self.game_data.units[producer.value]
                if producer_unit_data.proto.food_required <= unit_supply_cost:
                    producer_supply_cost = producer_unit_data.proto.food_required
                    unit_supply_cost -= producer_supply_cost
        return unit_supply_cost

    def can_feed(self, unit_type: UnitTypeId) -> bool:
        """ Checks if you have enough free supply to build the unit

        Example::

            cc = self.townhalls.idle.random_or(None)
            # self.townhalls can be empty or there are no idle townhalls
            if cc and self.can_feed(UnitTypeId.SCV):
                self.do(cc.train(UnitTypeId.SCV))

        :param unit_type: """
        required = self.calculate_supply_cost(unit_type)
        return required <= 0 or self.supply_left >= required

    def calculate_unit_value(self, unit_type: UnitTypeId) -> Cost:
        """
        Unlike the function below, this function returns the value of a unit given by the API (e.g. the resources
        lost value on kill).

        Examples::

            self.calculate_value(UnitTypeId.ORBITALCOMMAND) == Cost(550, 0)
            self.calculate_value(UnitTypeId.RAVAGER) == Cost(100, 100)
            self.calculate_value(UnitTypeId.ARCHON) == Cost(175, 275)

        :param unit_type:
        """
        unit_data = self.game_data.units[unit_type.value]
        return Cost(unit_data.proto.mineral_cost, unit_data.proto.vespene_cost)

    def calculate_cost(self, item_id: Union[UnitTypeId, UpgradeId, AbilityId]) -> Cost:
        """
        Calculate the required build, train or morph cost of a unit. It is recommended to use the UnitTypeId instead
        of the ability to create the unit. The total cost to create a ravager is 100/100, but the actual morph cost
        from roach to ravager is only 25/75, so this function returns 25/75.

        It is advised to use the UnitTypeId instead of the AbilityId. Instead of::

            self.calculate_cost(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

        use::

            self.calculate_cost(UnitTypeId.ORBITALCOMMAND)

        More examples::

            from sc2.game_data import Cost

            self.calculate_cost(UnitTypeId.BROODLORD) == Cost(150, 150)
            self.calculate_cost(UnitTypeId.RAVAGER) == Cost(25, 75)
            self.calculate_cost(UnitTypeId.BANELING) == Cost(25, 25)
            self.calculate_cost(UnitTypeId.ORBITALCOMMAND) == Cost(150, 0)
            self.calculate_cost(UnitTypeId.REACTOR) == Cost(50, 50)
            self.calculate_cost(UnitTypeId.TECHLAB) == Cost(50, 25)
            self.calculate_cost(UnitTypeId.QUEEN) == Cost(150, 0)
            self.calculate_cost(UnitTypeId.HATCHERY) == Cost(300, 0)
            self.calculate_cost(UnitTypeId.LAIR) == Cost(150, 100)
            self.calculate_cost(UnitTypeId.HIVE) == Cost(200, 150)

        :param item_id:
        """
        if isinstance(item_id, UnitTypeId):
            if item_id in {UnitTypeId.REACTOR, UnitTypeId.TECHLAB, UnitTypeId.ARCHON}:
                if item_id == UnitTypeId.REACTOR:
                    return Cost(50, 50)
                if item_id == UnitTypeId.TECHLAB:
                    return Cost(50, 25)
                if item_id == UnitTypeId.ARCHON:
                    return self.calculate_unit_value(UnitTypeId.ARCHON)
            unit_data = self.game_data_local.units[item_id.value]
            cost = self.game_data_local.calculate_ability_cost(unit_data.creation_ability)
            unit_supply_cost = unit_data.proto.food_required
            if unit_supply_cost > 0 and item_id in UNIT_TRAINED_FROM and len(UNIT_TRAINED_FROM[item_id]) == 1:
                for producer in UNIT_TRAINED_FROM[item_id]:
                    producer_unit_data = self.game_data.units[producer.value]
                    if 0 < producer_unit_data.proto.food_required <= unit_supply_cost:
                        if producer == UnitTypeId.ZERGLING:
                            producer_cost = Cost(25, 0)
                        else:
                            producer_cost = self.game_data.calculate_ability_cost(producer_unit_data.creation_ability)
                        cost = cost - producer_cost

        elif isinstance(item_id, UpgradeId):
            cost = self.game_data_local.upgrades[item_id.value].cost
        else:
            cost = self.game_data_local.calculate_ability_cost(item_id)
        return cost

    def can_afford(self, item_id: Union[UnitTypeId, UpgradeId, AbilityId], check_supply_cost: bool = True) -> bool:
        """ Tests if the player has enough resources to build a unit or structure.

        Example::

            cc = self.townhalls.idle.random_or(None)
            # self.townhalls can be empty or there are no idle townhalls
            if cc and self.can_afford(UnitTypeId.SCV):
                self.do(cc.train(UnitTypeId.SCV))

        Example::

            # Current state: we have 150 minerals and one command center and a barracks can_afford_morph =
            self.can_afford(UnitTypeId.ORBITALCOMMAND, check_supply_cost=False) # Will be 'True' although the API
            reports that an orbital is worth 550 minerals, but the morph cost is only 150 minerals

        :param item_id:
        :param check_supply_cost: """
        cost = self.calculate_cost(item_id)
        if cost.minerals > self.minerals or cost.vespene > self.vespene:
            return False
        if check_supply_cost and isinstance(item_id, UnitTypeId):
            supply_cost = self.calculate_supply_cost(item_id)
            if supply_cost and supply_cost > self.supply_left:
                return False
        return True

    async def can_cast(
        self,
        unit: Unit,
        ability_id: AbilityId,
        target: Optional[Union[Unit, Point2, Point3]] = None,
        only_check_energy_and_cooldown: bool = False,
        cached_abilities_of_unit: List[AbilityId] = None,
    ) -> bool:
        """ Tests if a unit has an ability available and enough energy to cast it.

        Example::

            stalkers = self.units(UnitTypeId.STALKER) stalkers_that_can_blink = stalkers.filter(lambda unit:
            unit.type_id == UnitTypeId.STALKER and (await self.can_cast(unit, AbilityId.EFFECT_BLINK_STALKER,
            only_check_energy_and_cooldown=True)))

        See data_pb2.py (line 161) for the numbers 1-5 to make sense

        :param unit:
        :param ability_id:
        :param target:
        :param only_check_energy_and_cooldown:
        :param cached_abilities_of_unit: """
        if not isinstance(unit, Unit):
            raise AssertionError(f"{unit} is no Unit object")
        if not isinstance(ability_id, AbilityId):
            raise AssertionError(f"{ability_id} is no AbilityId")
        if not isinstance(target, (type(None), Unit, Point2, Point3)):
            raise AssertionError()
        if cached_abilities_of_unit:
            abilities = cached_abilities_of_unit
        else:
            abilities = (await self.get_available_abilities([unit], ignore_resource_requirements=False))[0]

        if ability_id in abilities:
            if only_check_energy_and_cooldown:
                return True
            cast_range = self.game_data_local.abilities[ability_id.value].proto.cast_range
            ability_target = self.game_data_local.abilities[ability_id.value].proto.target
            if (
                ability_target == 1
                or ability_target == TARGET.PointOrNone.value
                and isinstance(target, (Point2, Point3))
                and unit.distance_to(target) <= unit.radius + target.radius + cast_range
            ):
                return True
            if (
                ability_target in {TARGET.Unit.value, TARGET.PointOrUnit.value}
                and isinstance(target, Unit)
                and unit.distance_to(target) <= unit.radius + target.radius + cast_range
            ):
                return True
            if (
                ability_target in {TARGET.Point.value, TARGET.PointOrUnit.value}
                and isinstance(target, (Point2, Point3))
                and unit.distance_to(target) <= unit.radius + cast_range
            ):
                return True
        return False

    def select_build_worker(self, pos: Union[Unit, Point2, Point3], force: bool = False) -> Optional[Unit]:
        """Select a worker to build a building with.

        Example::

            barracks_placement_position = self.main_base_ramp.barracks_correct_placement
            worker = self.select_build_worker(barracks_placement_position)
            # Can return None
            if worker:
                self.do(worker.build(UnitTypeId.BARRACKS, barracks_placement_position))

        :param pos:
        :param force: """
        workers = (
            self.workers.filter(lambda w: (w.is_gathering or w.is_idle) and w.distance_to(pos) < 20) or self.workers
        )
        if workers:
            for worker in workers.sorted_by_distance_to(pos).prefer_idle:
                if (
                    worker not in self.unit_tags_received_action
                    and not worker.orders
                    or len(worker.orders) == 1
                    and worker.orders[0].ability.id in {AbilityId.MOVE, AbilityId.HARVEST_GATHER}
                ):
                    return worker

            return workers.random_unit if force else None
        return None

    async def can_place(self, building: Union[AbilityData, AbilityId, UnitTypeId], position: Point2) -> bool:
        """ Tests if a building can be placed in the given location.

        Example::

            barracks_placement_position = self.main_base_ramp.barracks_correct_placement
            worker = self.select_build_worker(barracks_placement_position)
            # Can return None
            if worker and (await self.can_place(UnitTypeId.BARRACKS, barracks_placement_position):
                self.do(worker.build(UnitTypeId.BARRACKS, barracks_placement_position))

        :param building:
        :param position: """
        building_type = type(building)
        if building_type not in {AbilityData, AbilityId, UnitTypeId}:
            raise AssertionError()
        if building_type == UnitTypeId:
            building = self.game_data_local.units[building.value].creation_ability
        elif building_type == AbilityId:
            building = self.game_data_local.abilities[building.value]

        action_result = await self._client.query_building_placement(building, [position])
        return action_result[0] == ACTION_RESULT.Success

    async def find_placement(
        self,
        building: UnitTypeId,
        near: Union[Unit, Point2, Point3],
        max_distance: int = 20,
        random_alternative: bool = True,
        placement_step: int = 2,
    ) -> Optional[Point2]:
        """ Finds a placement location for building.

        Example::

            if self.townhalls:
                cc = self.townhalls[0]
                depot_position = await self.find_placement(UnitTypeId.SUPPLYDEPOT, near=cc)

        :param building:
        :param near:
        :param max_distance:
        :param random_alternative:
        :param placement_step: """

        if not isinstance(building, (AbilityId, UnitTypeId)):
            raise AssertionError()
        if not isinstance(near, Point2):
            raise AssertionError(f"{near} is no Point2 object")

        if isinstance(building, UnitTypeId):
            building = self.game_data_local.units[building.value].creation_ability
        else:
            building = self.game_data_local.abilities[building.value]

        if await self.can_place(building, near):
            return near

        if max_distance == 0:
            return None

        for distance in range(placement_step, max_distance, placement_step):
            possible_positions = [
                Point2(p).offset(near).to2
                for p in (
                    [(dx, -distance) for dx in range(-distance, distance + 1, placement_step)]
                    + [(dx, distance) for dx in range(-distance, distance + 1, placement_step)]
                    + [(-distance, dy) for dy in range(-distance, distance + 1, placement_step)]
                    + [(distance, dy) for dy in range(-distance, distance + 1, placement_step)]
                )
            ]
            res = await self._client.query_building_placement(building, possible_positions)
            possible = [p for r, p in zip(res, possible_positions) if r == ACTION_RESULT.Success]
            if not possible:
                continue

            if random_alternative:
                return random.SystemRandom().choice(possible)
            return min(possible, key=lambda p: p.distance_to_point2(near))
        return None

    def already_pending_upgrade(self, upgrade_type: UpgradeId) -> float:
        """ Check if an upgrade is being researched

        Returns values are::

            0 # not started
            0 < x < 1 # researching
            1 # completed

        Example::

            stim_completion_percentage = self.already_pending_upgrade(UpgradeId.STIMPACK)

        :param upgrade_type:
        """
        if not isinstance(upgrade_type, UpgradeId):
            raise AssertionError(f"{upgrade_type} is no UpgradeId")
        if upgrade_type in self.state.upgrades:
            return 1
        creation_ability_id = self.game_data_local.upgrades[upgrade_type.value].research_ability.exact_id
        for structure in self.structures.filter(lambda unit: unit.is_ready):
            for order in structure.orders:
                if order.ability.exact_id == creation_ability_id:
                    return order.progress
        return 0

    @property_cache_once_per_frame_no_copy
    def _abilities_all_units(self) -> Tuple[Counter, Dict[UnitTypeId, float]]:
        """ Cache for the already_pending function, includes protoss units warping in,
        all units in production and all structures, and all morphs """
        abilities_amount = Counter()
        max_build_progress: Dict[UnitTypeId, float] = {}
        for unit in self.units + self.structures:  # type: Unit
            for order in unit.orders:
                abilities_amount[order.ability] += 1
            if not unit.is_ready:
                if self.race != RACE.Terran or not unit.is_structure:
                    # If an SCV is constructing a building, already_pending would count this structure twice
                    # (once from the SCV order, and once from "not structure.is_ready")
                    creation_ability: AbilityData = self.game_data_local.units[unit.type_id.value].creation_ability
                    abilities_amount[creation_ability] += 1
                    max_build_progress[creation_ability] = max(
                        max_build_progress.get(creation_ability, 0), unit.build_progress
                    )

        return abilities_amount, max_build_progress

    def structure_type_build_progress(self, structure_type: Union[UnitTypeId, int]) -> float:
        """
        Returns the build progress of a structure type.

        Return range: 0 <= x <= 1 where 0: no such structure exists 0 < x < 1: at least one structure is under
        construction, returns the progress of the one with the highest progress 1: we have at least one such
        structure complete

        Example::

            # Assuming you have one barracks building at 0.5 build progress:
            progress = self.structure_type_build_progress(UnitTypeId.BARRACKS)
            print(progress)
            # This prints out 0.5

            # If you want to save up money for mutalisks, you can now save up once the spire is nearly completed:
            spire_almost_completed: bool = self.structure_type_build_progress(UnitTypeId.SPIRE) > 0.75

            # If you have a Hive completed but no lair, this function returns 1.0 for the following:
            self.structure_type_build_progress(UnitTypeId.LAIR)

            # Assume you have 2 command centers in production, one has 0.5 build_progress and the other 0.2,
            the following returns 0.5 highest_progress_of_command_center: float = self.structure_type_build_progress(
            UnitTypeId.COMMANDCENTER)

        :param structure_type:
        """
        if not isinstance(structure_type, (int, UnitTypeId)):
            raise AssertionError(f"Needs to be int or UnitTypeId, but was: {type(structure_type)}")
        if isinstance(structure_type, int):
            structure_type_value: int = structure_type
            structure_type = UnitTypeId(structure_type_value)
        else:
            structure_type_value = structure_type.value
        if not structure_type_value:
            raise AssertionError(f"structure_type can not be 0 or NOTAUNIT, but was: {structure_type_value}")
        equiv_values: Set[int] = {structure_type_value} | {
            s_type.value for s_type in EQUIVALENTS_FOR_TECH_PROGRESS.get(structure_type, set())
        }
        creation_ability: AbilityData = self.game_data_local.units[structure_type_value].creation_ability
        max_value = max(
            [s.build_progress for s in self.structures if s.proto.unit_type in equiv_values]
            + [self._abilities_all_units[1].get(creation_ability, 0)]
        )
        return max_value

    def tech_requirement_progress(self, structure_type: UnitTypeId) -> float:
        """ Returns the tech requirement progress for a specific building

        Example::

            # Current state: supply depot is at 50% completion
            tech_requirement = self.tech_requirement_progress(UnitTypeId.BARRACKS)
            print(tech_requirement) # Prints 0.5 because supply depot is half way done

        Example::

            # Current state: your bot has one hive, no lair
            tech_requirement = self.tech_requirement_progress(UnitTypeId.HYDRALISKDEN)
            print(tech_requirement) # Prints 1 because a hive exists even though only a lair is required

        Example::

            # Current state: One factory is flying and one is half way done tech_requirement =
            self.tech_requirement_progress(UnitTypeId.STARPORT) print(tech_requirement) # Prints 1 because even
            though the type id of the flying factory is different, it still has build progress of 1 and thus tech
            requirement is completed

        :param structure_type: """
        race_dict = {
            RACE.Protoss: PROTOSS_TECH_REQUIREMENT,
            RACE.Terran: TERRAN_TECH_REQUIREMENT,
            RACE.Zerg: ZERG_TECH_REQUIREMENT,
        }
        unit_info_id = race_dict[self.race][structure_type]
        unit_info_id_value = unit_info_id.value
        if not unit_info_id_value:
            return 1
        progresses: List[int] = [self.structure_type_build_progress(unit_info_id_value)]
        for equiv_structure in EQUIVALENTS_FOR_TECH_PROGRESS.get(unit_info_id, []):
            progresses.append(self.structure_type_build_progress(equiv_structure.value))
        return max(progresses)

    def already_pending(self, unit_type: Union[UpgradeId, UnitTypeId]) -> float:
        """
        Returns a number of buildings or units already in progress, or if a
        worker is en route to build it. This also includes queued orders for
        workers and build queues of buildings.

        Example::

            amount_of_scv_in_production: int = self.already_pending(UnitTypeId.SCV)
            amount_of_CCs_in_queue_and_production: int = self.already_pending(UnitTypeId.COMMANDCENTER)
            amount_of_lairs_morphing: int = self.already_pending(UnitTypeId.LAIR)


        :param unit_type:
        """
        if isinstance(unit_type, UpgradeId):
            return self.already_pending_upgrade(unit_type)
        ability = self.game_data_local.units[unit_type.value].creation_ability
        return self._abilities_all_units[0][ability]

    @property_cache_once_per_frame_no_copy
    def _worker_orders(self) -> Counter:
        """ This function is used internally, do not use! It is to store all worker abilities. """
        abilities_amount = Counter()
        structures_in_production: Set[Union[Point2, int]] = set()
        for structure in self.structures:
            if structure.type_id in TERRAN_STRUCTURES_REQUIRE_SCV:
                structures_in_production.add(structure.position)
                structures_in_production.add(structure.tag)
        for worker in self.workers:
            for order in worker.orders:
                is_int = isinstance(order.target, int)
                if (
                    is_int
                    and order.target in structures_in_production
                    or not is_int
                    and Point2.from_proto(order.target) in structures_in_production
                ):
                    continue
                abilities_amount[order.ability] += 1
        return abilities_amount

    def worker_en_route_to_build(self, unit_type: UnitTypeId) -> float:
        """ This function counts how many workers are on the way to start the construction a building.
        Warning: this function may change its name in the future!
        New function. Please report any bugs!

        :param unit_type: """
        ability = self.game_data_local.units[unit_type.value].creation_ability
        return self._worker_orders[ability]

    async def build(
        self,
        building: UnitTypeId,
        near: Union[Unit, Point2, Point3],
        max_distance: int = 20,
        build_worker: Optional[Unit] = None,
        random_alternative: bool = True,
        placement_step: int = 2,
    ) -> bool:
        """ Not recommended as this function checks many positions if it "can place" on them until it found a valid
        position. Also if the given position is not buildable, this function tries to find a nearby position to place
        the structure. Then uses 'self.do' to give the worker the order to start the construction.

        :param building:
        :param near:
        :param max_distance:
        :param build_worker:
        :param random_alternative:
        :param placement_step: """

        if not isinstance(near, (Unit, Point2, Point3)):
            raise AssertionError()
        if not self.can_afford(building):
            return False
        placement = None
        gas_buildings = {UnitTypeId.EXTRACTOR, UnitTypeId.ASSIMILATOR, UnitTypeId.REFINERY}
        if isinstance(near, Unit) and building not in gas_buildings:
            near = near.position
        if isinstance(near, (Point2, Point3)):
            near = near.to2
        if isinstance(near, (Point2, Point3)):
            placement = await self.find_placement(building, near, max_distance, random_alternative, placement_step)
            if placement is None:
                return False
        builder = build_worker or self.select_build_worker(near)
        if builder is None:
            return False
        if building in gas_buildings:
            self.do(builder.build_gas(near), subtract_cost=True)
            return True
        self.do(builder.build(building, placement), subtract_cost=True)
        return True

    def train(
        self, unit_type: UnitTypeId, amount: int = 1, closest_to: Point2 = None, train_only_idle_buildings: bool = True
    ) -> int:
        """ Trains a specified number of units. Trains only one if amount is not specified.
        Warning: currently has issues with warp gate warp ins

        New function. Please report any bugs!

        Example Zerg::

            self.train(UnitTypeId.QUEEN, 5) # This should queue 5 queens in 5 different townhalls if you have enough
            townhalls, enough minerals and enough free supply left

        Example Terran::

            # Assuming you have 2 idle barracks with reactors, one barracks without addon and one with techlab
            # It should only queue 4 marines in the 2 idle barracks with reactors
            self.train(UnitTypeId.MARINE, 4)

        Example distance to::

            # If you want to train based on distance to a certain position, you can use "closest_to"
            self.train(UnitTypeId.MARINE, 4, closest_to = self.game_info.map_center)


        :param unit_type:
        :param amount:
        :param closest_to:
        :param train_only_idle_buildings: """
        if self.tech_requirement_progress(unit_type) < 1:
            race_dict = {
                RACE.Protoss: PROTOSS_TECH_REQUIREMENT,
                RACE.Terran: TERRAN_TECH_REQUIREMENT,
                RACE.Zerg: ZERG_TECH_REQUIREMENT,
            }
            unit_info_id = race_dict[self.race][unit_type]
            LOGGER.warning(
                f"{self.time_formatted} Trying to produce unit {unit_type} "
                f"in self.train() but tech requirement is not met: {unit_info_id}"
            )
            return 0

        if not self.can_afford(unit_type):
            return 0

        trained_amount = 0
        train_structure_type: Set[UnitTypeId] = UNIT_TRAINED_FROM[unit_type]
        train_structures = self.structures if self.race != RACE.Zerg else self.structures | self.larva
        requires_techlab = any(
            TRAIN_INFO[structure_type][unit_type].get("requires_techlab", False)
            for structure_type in train_structure_type
        )
        is_protoss = self.race == RACE.Protoss
        is_terran = self.race == RACE.Terran
        can_have_addons = any(
            u in train_structure_type for u in {UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT}
        )
        if closest_to is not None:
            train_structures = train_structures.sorted_by_distance_to(closest_to)
        elif can_have_addons:
            # This should sort the structures in ascending order:
            # first structures with reactor, then naked, then with techlab
            train_structures = train_structures.sorted(
                key=lambda building: -1 * (building.add_on_tag in self.reactor_tags)
                + 1 * (building.add_on_tag in self.techlab_tags)
            )

        structure: Unit
        for structure in train_structures:
            if not self.can_afford(unit_type):
                return trained_amount
            if (
                structure.tag not in self.unit_tags_received_action
                and structure.type_id in train_structure_type
                and structure.build_progress == 1
                and (not is_protoss or structure.is_powered)
                and (
                    not train_only_idle_buildings
                    or len(structure.orders) < 1 + int(structure.add_on_tag in self.reactor_tags)
                )
                and (not requires_techlab or structure.add_on_tag in self.techlab_tags)
            ):
                if structure.type_id == UnitTypeId.WARPGATE:
                    pylons = self.structures(UnitTypeId.PYLON)
                    location = pylons.random_unit.position.random_on_distance(4)
                    successfully_trained = self.do(
                        structure.warp_in(unit_type, location), subtract_cost=True, subtract_supply=True
                    )
                else:
                    successfully_trained = self.do(structure.train(unit_type), subtract_cost=True, subtract_supply=True)
                    if (
                        is_terran
                        and self.can_afford(unit_type)
                        and not structure.orders
                        and trained_amount + 1 < amount
                        and not requires_techlab
                        and structure.add_on_tag in self.reactor_tags
                    ):
                        trained_amount += 1
                        # With one command queue=False and one queue=True,
                        # you can queue 2 marines in a barrack with reactor in one frame
                        successfully_trained = self.do(
                            structure.train(unit_type, queue=True), subtract_cost=True, subtract_supply=True
                        )

                if successfully_trained:
                    trained_amount += 1
                    if trained_amount == amount:
                        return trained_amount
                else:
                    return trained_amount
        return trained_amount

    def research(self, upgrade_type: UpgradeId) -> bool:
        """
        Researches an upgrade from a structure that can research it, if it is idle and powered (protoss).
        Returns True if the research was started.
        Return False if the requirement was not met, or the bot did not have enough resources to start the upgrade,
        or the building to research the upgrade was missing or not idle.

        New function. Please report any bugs!

        Example::

            # Try to research zergling movement speed if we can afford it # and if at least one pool is at
            build_progress == 1 # and we are not researching it yet if self.already_pending_upgrade(
            UpgradeId.ZERGLINGMOVEMENTSPEED) == 0 and self.can_afford(UpgradeId.ZERGLINGMOVEMENTSPEED):
            spawning_pools_ready = self.structures(UnitTypeId.SPAWNINGPOOL).ready if spawning_pools_ready:
            self.research(UpgradeId.ZERGLINGMOVEMENTSPEED)

        :param upgrade_type:
        """
        if upgrade_type not in UPGRADE_RESEARCHED_FROM:
            raise AssertionError(f"Could not find upgrade {upgrade_type} in 'research from'-dictionary")

        if not self.can_afford(upgrade_type):
            return False

        research_structure_types: UnitTypeId = UPGRADE_RESEARCHED_FROM[upgrade_type]
        required_tech_building: Optional[UnitTypeId] = RESEARCH_INFO[research_structure_types][upgrade_type].get(
            "required_building", None
        )

        requirement_met = (
            required_tech_building is None or self.structure_type_build_progress(required_tech_building) == 1
        )
        if not requirement_met:
            return False

        is_protoss = self.race == RACE.Protoss

        equiv_structures = {
            UnitTypeId.GREATERSPIRE: {UnitTypeId.SPIRE, UnitTypeId.GREATERSPIRE},
            UnitTypeId.HIVE: {UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE},
        }
        # Convert to a set, or equivalent structures are chosen
        # Overlord speed upgrade can be researched from hatchery, lair or hive
        research_structure_types: Set[UnitTypeId] = equiv_structures.get(
            research_structure_types, {research_structure_types}
        )

        structure: Unit
        for structure in self.structures:
            if (
                # If structure hasn't received an action/order this frame
                structure.tag not in self.unit_tags_received_action
                # Structure can research this upgrade
                and structure.type_id in research_structure_types
                # Structure is idle
                and structure.is_idle
                # Structure belongs to protoss and is powered (near pylon)
                and (not is_protoss or structure.is_powered)
            ):
                # Can_afford check was already done earlier in this function
                successful_action: bool = self.do(structure.research(upgrade_type), subtract_cost=True)
                return successful_action
        return False

    def do(
        self,
        action: UnitCommand,
        subtract_cost: bool = False,
        subtract_supply: bool = False,
        can_afford_check: bool = False,
    ) -> bool:
        """ Adds a unit action to the 'self.actions' list which is then executed at the end of the frame.

        Training a unit::

            # Train an SCV from a random idle command center
            cc = self.townhalls.idle.random_or(None)
            # self.townhalls can be empty or there are no idle townhalls
            if cc and self.can_afford(UnitTypeId.SCV):
                self.do(cc.train(UnitTypeId.SCV), subtract_cost=True, subtract_supply=True)

        Building a building::

            # Building a barracks at the main ramp, requires 150 minerals and a depot
            worker = self.workers.random_or(None)
            barracks_placement_position = self.main_base_ramp.barracks_correct_placement
            if worker and self.can_afford(UnitTypeId.BARRACKS):
                self.do(worker.build(UnitTypeId.BARRACKS, barracks_placement_position), subtract_cost=True)

        Moving a unit::

            # Move a random worker to the center of the map
            worker = self.workers.random_or(None)
            # worker can be None if all are dead
            if worker:
                self.do(worker.move(self.game_info.map_center))

        :param action:
        :param subtract_cost:
        :param subtract_supply:
        :param can_afford_check:
        """
        if not isinstance(action, UnitCommand):
            raise AssertionError(f"Given unit command is not a command, but instead of type {type(action)}")
        if subtract_cost:
            cost: Cost = self.game_data_local.calculate_ability_cost(action.ability)
            if can_afford_check and not (self.minerals >= cost.minerals and self.vespene >= cost.vespene):
                # Don't do action if can't afford
                return False
            self.minerals -= cost.minerals
            self.vespene -= cost.vespene
        if subtract_supply and action.ability in abilityid_to_unittypeid:
            unit_type = abilityid_to_unittypeid[action.ability]
            required_supply = self.calculate_supply_cost(unit_type)
            # Overlord has -8
            if required_supply > 0:
                self.supply_used += required_supply
                self.supply_left -= required_supply
        self.actions.append(action)
        self.unit_tags_received_action.add(action.unit.tag)
        return True

    async def synchronous_do(self, action: UnitCommand):
        """
        Not recommended. Use self.do instead to reduce lag.
        This function is only useful for realtime=True in the first frame of the game to instantly produce a worker
        and split workers on the mineral patches.
        """
        if not isinstance(action, UnitCommand):
            raise AssertionError(f"Given unit command is not a command, but instead of type {type(action)}")
        if not self.can_afford(action.ability):
            LOGGER.warning(f"Cannot afford action {action}")
            return ACTION_RESULT.Error
        action_request = await self._client.actions(action)
        if not action_request:  # success
            cost = self.game_data_local.calculate_ability_cost(action.ability)
            self.minerals -= cost.minerals
            self.vespene -= cost.vespene
            self.unit_tags_received_action.add(action.unit.tag)
        else:
            LOGGER.error(f"Error: {action_request} (action: {action})")
        return action_request

    async def _do_actions(self, actions: List[UnitCommand], prevent_double: bool = True):
        """ Used internally by main.py automatically, use self.do() instead!

        :param actions:
        :param prevent_double: """
        if not actions:
            return None
        if prevent_double:
            actions = list(filter(self.prevent_double_actions, actions))
        result = await self._client.actions(actions)
        return result

    @staticmethod
    def prevent_double_actions(action) -> bool:
        """
        :param action:
        """
        # Always add actions if queued
        if action.queue:
            return True
        if action.unit.orders:
            # action: UnitCommand
            # current_action: UnitOrder
            current_action = action.unit.orders[0]
            if current_action.ability.id != action.ability:
                # Different action, return True
                return True
            with suppress(AttributeError):
                if current_action.target == action.target.tag:
                    # Same action, remove action if same target unit
                    return False
            with suppress(AttributeError):
                if action.target.x == current_action.target.x and action.target.y == current_action.target.y:
                    # Same action, remove action if same target position
                    return False
            return True
        return True

    async def chat_send(self, message: str):
        """ Send a chat message to the SC2 Client.

        Example::

            await self.chat_send("Hello, this is a message from my bot!")

        :param message: """
        if not isinstance(message, str):
            raise AssertionError(f"{message} is not a string")
        await self._client.chat_send(message, False)

    def in_map_bounds(self, pos: Union[Point2, tuple]) -> bool:
        """ Tests if a 2 dimensional position is within the map boundaries of the pixelmaps.
        :param pos: """
        return (
            self._game_info.playable_area.x
            <= pos[0]
            < self._game_info.playable_area.x + self.game_info.playable_area.width
            and self._game_info.playable_area.y
            <= pos[1]
            < self._game_info.playable_area.y + self.game_info.playable_area.height
        )

    # For the functions below, make sure you are inside the boundaries of the map size.
    def get_terrain_height(self, pos: Union[Point2, Point3, Unit]) -> int:
        """ Returns terrain height at a position.
        Caution: terrain height is different from a unit's z-coordinate.

        :param pos: """
        if not isinstance(pos, (Point2, Point3, Unit)):
            raise AssertionError(f"pos is not of type Point2, Point3 or Unit")
        pos = pos.position.to2.rounded
        return self._game_info.terrain_height[pos]

    def get_terrain_z_height(self, pos: Union[Point2, Point3, Unit]) -> int:
        """ Returns terrain z-height at a position.

        :param pos: """
        if not isinstance(pos, (Point2, Point3, Unit)):
            raise AssertionError(f"pos is not of type Point2, Point3 or Unit")
        pos = pos.position.to2.rounded
        return -16 + 32 * self._game_info.terrain_height[pos] / 255

    def in_placement_grid(self, pos: Union[Point2, Point3, Unit]) -> bool:
        """ Returns True if you can place something at a position.
        Remember, buildings usually use 2x2, 3x3 or 5x5 of these grid points.
        Caution: some x and y offset might be required, see ramp code in game_info.py

        :param pos: """
        if not isinstance(pos, (Point2, Point3, Unit)):
            raise AssertionError(f"pos is not of type Point2, Point3 or Unit")
        pos = pos.position.to2.rounded
        return self._game_info.placement_grid[pos] == 1

    def in_pathway_grid(self, pos: Union[Point2, Point3, Unit]) -> bool:
        """ Returns True if a ground unit can pass through a grid position.

        :param pos: """
        if not isinstance(pos, (Point2, Point3, Unit)):
            raise AssertionError(f"pos is not of type Point2, Point3 or Unit")
        pos = pos.position.to2.rounded
        return self._game_info.pathway_grid[pos] == 1

    def is_visible(self, pos: Union[Point2, Point3, Unit]) -> bool:
        """ Returns True if you have vision on a grid position.

        :param pos: """
        if not isinstance(pos, (Point2, Point3, Unit)):
            raise AssertionError(f"pos is not of type Point2, Point3 or Unit")
        pos = pos.position.to2.rounded
        return self.state.visibility[pos] == 2

    def has_creep(self, pos: Union[Point2, Point3, Unit]) -> bool:
        """ Returns True if there is creep on the grid position.

        :param pos: """
        if not isinstance(pos, (Point2, Point3, Unit)):
            raise AssertionError(f"pos is not of type Point2, Point3 or Unit")
        pos = pos.position.to2.rounded
        return self.state.creep[pos] == 1

    def prepare_start(self, client, player_id, game_info, game_data, realtime: bool = False):
        """
        Ran until game start to set game and player data.

        :param client:
        :param player_id:
        :param game_info:
        :param game_data:
        :param realtime:
        """
        self._client: Client = client
        self.player_id: int = player_id
        self._game_info: GameInfo = game_info
        self.game_data_local: GameData = game_data
        self.realtime: bool = realtime

        self.race: RACE = RACE(self._game_info.player_races[self.player_id])

        if len(self._game_info.player_races) == 2:
            self.enemy_race: RACE = RACE(self._game_info.player_races[3 - self.player_id])

        self._distances_override_functions(self.distance_calculation_method)

    def prepare_first_step(self):
        """First step extra preparations. Must not be called before prepare_step."""
        if self.townhalls:
            self._game_info.player_start_location = self.townhalls[0].position
            # Calculate and cache expansion locations forever inside 'self._cache_expansion_locations',
            # this is done to prevent a bug when this is run and cached later in the game
            _ = self.expansion_locations
        self._game_info.map_ramps, self._game_info.vision_blockers = self._game_info.find_ramps_and_vision_blockers()
        self._time_before_step: float = time.perf_counter()

    def prepare_step(self, state, proto_game_info):
        """
        :param state:
        :param proto_game_info:
        """
        # Set attributes from new state before on_step."""
        self.state: GameState = state  # See game_state.py
        # update pathway grid
        self._game_info.pathway_grid = PixelMap(
            proto_game_info.game_info.start_raw.pathing_grid, in_bits=True, mirrored=False
        )
        # Required for events, needs to be before self.units are initialized so the old units are stored
        self._units_previous_map: Dict = {unit.tag: unit for unit in self.units}
        self._structures_previous_map: Dict = {structure.tag: structure for structure in self.structures}
        self._enemy_units_previous_map: Dict = {unit.tag: unit for unit in self.enemy_units}
        self._enemy_structures_previous_map: Dict = {structure.tag: structure for structure in self.enemy_structures}

        self._prepare_units()
        self.minerals: int = state.common.minerals
        self.vespene: int = state.common.vespene
        self.supply_army: int = state.common.food_army
        self.supply_workers: int = state.common.food_workers  # Doesn't include workers in production
        self.supply_cap: int = state.common.food_cap
        self.supply_used: int = state.common.food_used
        self.supply_left: int = self.supply_cap - self.supply_used

        if self.race == RACE.Zerg:
            # Workaround Zerg supply rounding bug
            self._correct_zerg_supply()
        elif self.race == RACE.Protoss:
            self.warp_gate_count: int = state.common.warp_gate_count

        self.idle_worker_count: int = state.common.idle_worker_count
        self.army_count: int = state.common.army_count
        self._time_before_step: float = time.perf_counter()

    def _prepare_units(self):
        # Set of enemy units detected by own sensor tower, as blips have less unit information than normal visible units
        self.blips: Set[Blip] = set()
        self.units: Units = Units([], self)
        self.structures: Units = Units([], self)
        self.enemy_units: Units = Units([], self)
        self.enemy_structures: Units = Units([], self)
        self.mineral_field: Units = Units([], self)
        self.vespene_geyser: Units = Units([], self)
        self.resources: Units = Units([], self)
        self.destructible: Units = Units([], self)
        self.watchtowers: Units = Units([], self)
        self.all_units: Units = Units([], self)
        self.workers: Units = Units([], self)
        self.townhalls: Units = Units([], self)
        self.gas_buildings: Units = Units([], self)
        self.larva: Units = Units([], self)
        self.techlab_tags: Set[int] = set()
        self.reactor_tags: Set[int] = set()

        for unit in self.state.observation_raw.units:
            if unit.is_blip:
                self.blips.add(Blip(unit))
            else:
                unit_type: int = unit.unit_type
                # Convert these units to effects: reaper grenade, parasitic bomb dummy, forcefield
                if unit_type in FakeEffectID:
                    self.state.effects.add(EffectData(unit, fake=True))
                    continue
                unit_obj = Unit(unit, self)
                self.all_units.append(unit_obj)
                alliance = unit.alliance
                # Alliance.Neutral.value = 3
                if alliance == 3:
                    # XELNAGATOWER = 149
                    if unit_type == 149:
                        self.watchtowers.append(unit_obj)
                    # mineral field enums
                    elif unit_type in mineral_ids:
                        self.mineral_field.append(unit_obj)
                        self.resources.append(unit_obj)
                    # geyser enums
                    elif unit_type in geyser_ids:
                        self.vespene_geyser.append(unit_obj)
                        self.resources.append(unit_obj)
                    # all destructible rocks
                    else:
                        self.destructible.append(unit_obj)
                # Alliance.Self.value = 1
                elif alliance == 1:
                    unit_id = unit_obj.type_id
                    if unit_obj.is_structure:
                        self.structures.append(unit_obj)
                        if unit_id in race_townhalls[self.race]:
                            self.townhalls.append(unit_obj)
                        elif unit_id in ALL_GAS or unit_obj.vespene_contents:
                            self.gas_buildings.append(unit_obj)
                        elif unit_id in {
                            UnitTypeId.TECHLAB,
                            UnitTypeId.BARRACKSTECHLAB,
                            UnitTypeId.FACTORYTECHLAB,
                            UnitTypeId.STARPORTTECHLAB,
                        }:
                            self.techlab_tags.add(unit_obj.tag)
                        elif unit_id in {
                            UnitTypeId.REACTOR,
                            UnitTypeId.BARRACKSREACTOR,
                            UnitTypeId.FACTORYREACTOR,
                            UnitTypeId.STARPORTREACTOR,
                        }:
                            self.reactor_tags.add(unit_obj.tag)
                    else:
                        self.units.append(unit_obj)
                        if unit_id == race_worker[self.race]:
                            self.workers.append(unit_obj)
                        elif unit_id == UnitTypeId.LARVA:
                            self.larva.append(unit_obj)
                # Alliance.Enemy.value = 4
                elif alliance == 4:
                    if unit_obj.is_structure:
                        self.enemy_structures.append(unit_obj)
                    else:
                        self.enemy_units.append(unit_obj)

        # Force distance calculation and caching on all units using scipy pdist or cdist
        if self.distance_calculation_method == 1:
            _ = self._unit_index_dict
            _ = self._pdist
        elif self.distance_calculation_method == 2:
            _ = self._unit_index_dict
            _ = self._cdist
        elif self.distance_calculation_method == 3:
            _ = self._unit_index_dict
            _ = self._cdist

    async def after_step(self) -> int:
        """ Executed by main.py after each on_step function. """
        # Keep track of the bot on_step duration
        self._time_after_step: float = time.perf_counter()
        step_duration = self._time_after_step - self._time_before_step
        self._min_step_time = min(step_duration, self._min_step_time)
        self._max_step_time = max(step_duration, self._max_step_time)
        self._last_step_step_time = step_duration
        self._total_time_in_on_step += step_duration
        self._total_steps_iterations += 1
        # Commit and clear bot actions
        if self.actions:
            await self._do_actions(self.actions)
            self.actions.clear()
        # Clear set of unit tags that were given an order this frame by self.do()
        self.unit_tags_received_action.clear()
        # Commit debug queries
        await self._client.send_debug()

        return self.state.game_loop

    async def _advance_steps(self, steps: int):
        """ Advances the game loop by amount of 'steps'. This function is meant to be used as a debugging and testing
        tool only. If you are using this, please be aware of the consequences, e.g. 'self.units' will be filled with
        completely new data. """
        await self.after_step()
        # Advance simulation by exactly "steps" frames
        await self.client.step(steps)
        state = await self.client.observation()
        game_state = GameState(state.observation)
        proto_game_info = await self.client.execute(game_info=sc_pb.RequestGameInfo())
        self.prepare_step(game_state, proto_game_info)
        await self.issue_events()
        # await self.on_step(-1)

    async def issue_events(self):
        """ This function will be automatically run from main.py and triggers the following functions:
        - on_unit_created
        - on_unit_destroyed
        - on_building_construction_started
        - on_building_construction_complete
        - on_upgrade_complete
        """
        await self._issue_unit_dead_events()
        await self._issue_unit_added_events()
        await self._issue_building_events()
        await self._issue_upgrade_events()
        await self._issue_vision_events()

    async def _issue_unit_added_events(self):
        for unit in self.units:
            if unit.tag not in self._units_previous_map and unit.tag not in self._unit_tags_seen_this_game:
                self._unit_tags_seen_this_game.add(unit.tag)
                self._units_created[unit.type_id] += 1
                await self.on_unit_created(unit)
            elif unit.tag in self._units_previous_map:
                previous_frame_unit: Unit = self._units_previous_map[unit.tag]
                # Check if a unit took damage this frame and then trigger event
                if unit.health < previous_frame_unit.health or unit.shield < previous_frame_unit.shield:
                    damage_amount = previous_frame_unit.health - unit.health + previous_frame_unit.shield - unit.shield
                    await self.on_unit_took_damage(unit, damage_amount)
                # Check if a unit type has changed
                if previous_frame_unit.type_id != unit.type_id:
                    await self.on_unit_type_changed(unit, previous_frame_unit.type_id)

    async def _issue_upgrade_events(self):
        difference = self.state.upgrades - self._previous_upgrades
        for upgrade_completed in difference:
            await self.on_upgrade_complete(upgrade_completed)
        self._previous_upgrades = self.state.upgrades

    async def _issue_building_events(self):
        for structure in self.structures:
            if structure.tag not in self._structures_previous_map:
                if structure.build_progress < 1:
                    await self.on_building_construction_started(structure)
                else:
                    # Include starting townhall
                    self._units_created[structure.type_id] += 1
                    await self.on_building_construction_complete(structure)
            elif structure.tag in self._structures_previous_map:
                # Check if a structure took damage this frame and then trigger event
                previous_frame_structure: Unit = self._structures_previous_map[structure.tag]
                if (
                    structure.health < previous_frame_structure.health
                    or structure.shield < previous_frame_structure.shield
                ):
                    damage_amount = (
                        previous_frame_structure.health
                        - structure.health
                        + previous_frame_structure.shield
                        - structure.shield
                    )
                    await self.on_unit_took_damage(structure, damage_amount)
                # Check if a structure changed its type
                if previous_frame_structure.type_id != structure.type_id:
                    await self.on_unit_type_changed(structure, previous_frame_structure.type_id)
                # Check if structure completed
                if structure.build_progress == 1 and previous_frame_structure.build_progress < 1:
                    self._units_created[structure.type_id] += 1
                    await self.on_building_construction_complete(structure)

    async def _issue_vision_events(self):
        # Call events for enemy unit entered vision
        for enemy_unit in self.enemy_units:
            if enemy_unit.tag not in self._enemy_units_previous_map:
                await self.on_enemy_unit_entered_vision(enemy_unit)
        for enemy_structure in self.enemy_structures:
            if enemy_structure.tag not in self._enemy_structures_previous_map:
                await self.on_enemy_unit_entered_vision(enemy_structure)

        # Call events for enemy unit left vision
        if self.enemy_units:
            visible_enemy_units = self.enemy_units.tags
            for enemy_unit_tag in self._enemy_units_previous_map.keys():
                if enemy_unit_tag not in visible_enemy_units:
                    await self.on_enemy_unit_left_vision(enemy_unit_tag)
        if self.enemy_structures:
            visible_enemy_structures = self.enemy_structures.tags
            for enemy_structure_tag in self._enemy_units_previous_map.keys():
                if enemy_structure_tag not in visible_enemy_structures:
                    await self.on_enemy_unit_left_vision(enemy_structure_tag)

    async def _issue_unit_dead_events(self):
        for unit_tag in self.state.dead_units:
            await self.on_unit_destroyed(unit_tag)

    async def on_unit_destroyed(self, unit_tag: int):
        """
        Override this in your bot class.
        Note that this function uses unit tags and not the unit objects
        because the unit does not exist any more.

        :param unit_tag:
        """

    async def on_unit_created(self, unit: Unit):
        """ Override this in your bot class. This function is called when a unit is created.

        :param unit: """

    async def on_unit_type_changed(self, unit: Unit, previous_type: UnitTypeId):
        """ Override this in your bot class. This function is called when a unit type has changed. To get the current
        UnitTypeId of the unit, use 'unit.type_id'

        This may happen when a larva morphed to an egg, siege tank sieged, a zerg unit burrowed, a hatchery morphed
        to lair, a corruptor morphed to broodlord cocoon, etc..

        Examples::

            print(f"My unit changed type: {unit} from {previous_type} to {unit.type_id}")

        :param unit:
        :param previous_type:
        """

    async def on_building_construction_started(self, unit: Unit):
        """
        Override this in your bot class.
        This function is called when a building construction has started.

        :param unit:
        """

    async def on_building_construction_complete(self, unit: Unit):
        """
        Override this in your bot class. This function is called when a building
        construction is completed.

        :param unit:
        """

    async def on_upgrade_complete(self, upgrade: UpgradeId):
        """
        Override this in your bot class. This function is called with the upgrade id of an upgrade that was not
        finished last step and is now.

        :param upgrade:
        """

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float):
        """
        Override this in your bot class. This function is called when your own unit (unit or structure) took damage.
        It will not be called if the unit died this frame.

        This may be called frequently for terran structures that are burning down, or zerg buildings that are off creep,
        or terran bio units that just used stimpack ability.

        Examples::

            print(f"My unit took damage: {unit} took {amount_damage_taken} damage")

        Parameters
        ----------
        unit
        amount_damage_taken
        """

    async def on_enemy_unit_entered_vision(self, unit: Unit):
        """
        Override this in your bot class. This function is called when an enemy unit (unit or structure) entered
        vision (which was not visible last frame).

        :param unit:
        """

    async def on_enemy_unit_left_vision(self, unit_tag: int):
        """
        Override this in your bot class. This function is called when an enemy unit (unit or structure) left vision (
        which was visible last frame). Same as the self.on_unit_destroyed event, this function is called with the
        unit's tag because the unit is no longer visible anymore. If you want to store a snapshot of the unit,
        use self._enemy_units_previous_map[unit_tag] for units or self._enemy_structures_previous_map[unit_tag] for
        structures.

        Examples::

            last_known_unit = self._enemy_units_previous_map.get(unit_tag, None) or
            self._enemy_structures_previous_map[unit_tag] print(f"Enemy unit left vision, last known location: {
            last_known_unit.position}")

        :param unit_tag:
        """

    async def on_before_start(self):
        """
        Override this in your bot class. This function is called before "on_start"
        and before "prepare_first_step" that calculates expansion locations.
        Not all data is available yet.
        This function is useful in realtime=True mode to split your workers or start producing the first worker.
        """

    async def on_start(self):
        """
        Override this in your bot class.
        At this position, game_data, game_info and the first iteration of game_state (self.state) are available.
        """

    async def on_step(self, iteration: int):
        """
        You need to implement this function!
        Override this in your bot class.
        This function is called on every game step (looped in realtime mode).

        :param iteration:
        """
        raise NotImplementedError

    async def on_end(self, game_result: RESULT):
        """ Override this in your bot class. This function is called at the end of a game. Unsure if this function
        will be called on the laddermanager client as the bot process may forcefully be terminated.

        :param game_result: """
