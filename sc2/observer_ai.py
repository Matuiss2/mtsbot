"""
Base class for the observers(almost a bot_ai copy)
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING, Dict, List, Set, Union

from sc2.cache import property_cache_once_per_frame
from sc2.data import ALERT, RACE, RESULT
from sc2.distances import DistanceCalculation
from sc2.game_data import GameData

# Imports for mypy and pycharm autocomplete as well as sphinx auto-documentation
from sc2.game_state import Blip, GameState
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

from .ai import Ai

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sc2.client import Client
    from sc2.game_info import GameInfo
    from sc2.unit_command import UnitCommand


class ObserverAI(Ai, DistanceCalculation):
    """ Base class for Observers."""

    def __init__(self):
        DistanceCalculation.__init__(self)
        Ai.__init__(self)
        self.idle_worker_count: int = None
        self.army_count: int = None
        self.warp_gate_count: int = None
        self.larva_count: int = None
        self.actions: List[UnitCommand] = []
        self.blips: Set[Blip] = set()
        self._unit_tags_seen_this_game: Set[int] = set()
        self._units_previous_map: Dict[int, Unit] = dict()
        self._structures_previous_map: Dict[int, Unit] = dict()
        self.unit_tags_received_action: Set[int] = set()
        self._client: Client = None
        self.player_id: int = None
        self._game_info: GameInfo = None
        self._game_data: GameData = None

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
    def game_info(self) -> GameInfo:
        """ See game_info.py """
        return self._game_info

    @property
    def game_data(self) -> GameData:
        """ See game_data.py """
        return self._game_data

    @property
    def client(self) -> Client:
        """ See client.py """
        return self._client

    def alert(self, alert_code: ALERT) -> bool:
        """
        Check if an alert is triggered in the current step.

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
        """ Possible start locations for enemies."""
        return self._game_info.start_locations

    async def get_available_abilities(
        self, units: Union[List[Unit], Units], ignore_resource_requirements: bool = False
    ) -> List[List[AbilityId]]:
        """
        Returns available abilities of one or more units.
        It checks cooldown, energy cost, and whether the ability has been researched.

        Examples::

            units_abilities = await self.get_available_abilities(self.units)

        or::

            units_abilities = await self.get_available_abilities([self.units.random])

        """
        return await self._client.query_available_abilities(units, ignore_resource_requirements)

    @property_cache_once_per_frame
    def _abilities_all_units(self) -> Counter:
        """
        Cache for the already_pending function, includes protoss units warping in,
        all units in production and all structures, and all morphs
        """
        abilities_amount = Counter()
        for unit in self.units + self.structures:
            for order in unit.orders:
                abilities_amount[order.ability] += 1
            if not unit.is_ready:
                if self.race != RACE.Terran or not unit.is_structure:
                    # If an SCV is constructing a building, already_pending would count this structure twice
                    # (once from the SCV order, and once from "not structure.is_ready")
                    abilities_amount[self._game_data.units[unit.type_id.value].creation_ability] += 1

        return abilities_amount

    def prepare_start(self, client, player_id, game_info, game_data, realtime: bool = False):
        """ Run until game start to set game and player data """
        self._client: Client = client
        self.player_id: int = player_id
        self._game_info: GameInfo = game_info
        self._game_data: GameData = game_data
        self.realtime: bool = realtime

    def prepare_first_step(self):
        """ First step extra preparations. Must not be called before prepare_step."""
        if self.townhalls:
            self._game_info.player_start_location = self.townhalls[0].position
        self._game_info.map_ramps, self._game_info.vision_blockers = self._game_info.find_ramps_and_vision_blockers()

    def prepare_step(self, state):
        """ Prepare all game data before every step """
        self.state: GameState = state
        self._units_previous_map: Dict = {unit.tag: unit for unit in self.units}
        self._structures_previous_map: Dict = {structure.tag: structure for structure in self.structures}

        self._prepare_units()

        for unit in self.state.observation_raw.units:
            if unit.is_blip:
                self.blips.add(Blip(unit))
            else:
                unit_obj = Unit(unit, self)
                self.units.append(unit_obj)

    async def after_step(self) -> int:
        """ Executed by main.py after each on_step function. """
        self.unit_tags_received_action.clear()
        return self.state.game_loop

    async def issue_events(self):
        """
        This function will be automatically run from main.py and triggers the following functions:
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

    async def _issue_unit_added_events(self):
        for unit in self.units:
            if unit.tag not in self._units_previous_map and unit.tag not in self._unit_tags_seen_this_game:
                self._unit_tags_seen_this_game.add(unit.tag)
                await self.on_unit_created(unit)

    async def _issue_building_events(self):
        for structure in self.structures:
            if structure.tag not in self._structures_previous_map and structure.build_progress < 1:
                await self.on_building_construction_started(structure)
                continue
            if structure.build_progress < 1:
                continue
            structure_prev = self._structures_previous_map.get(structure.tag, None)
            if structure_prev and structure_prev.build_progress < 1:
                await self.on_building_construction_complete(structure)

    async def _issue_unit_dead_events(self):
        for unit_tag in self.state.dead_units:
            await self.on_unit_destroyed(unit_tag)

    async def on_unit_destroyed(self, unit_tag):
        """
        Override this in your bot class.
        Note that this function uses unit tags and not the unit objects
        because the unit does not exist any more.
        """

    async def on_unit_created(self, unit: Unit):
        """ Override this in your bot class. This function is called when a unit is created."""

    async def on_building_construction_started(self, unit: Unit):
        """
        Override this in your bot class.
        This function is called when a building construction has started.
        """

    async def on_building_construction_complete(self, unit: Unit):
        """ Override this in your bot class. This function is called when a building construction is completed. """

    async def on_upgrade_complete(self, upgrade: UpgradeId):
        """
        Override this in your bot class. This function is called with the upgrade id of an upgrade that was not
        finished last step and is now.
        """

    async def on_start(self):
        """
        Override this in your bot class. This function is called after "on_start".
        At this position, game_data, game_info and the first iteration of game_state (self.state) are available.
        """

    async def on_step(self, iteration: int):
        """
        You need to implement this function!
        Override this in your bot class.
        This function is called on every game step (looped in realtime mode).
        """
        raise NotImplementedError

    async def on_end(self, game_result: RESULT):
        """ Override this in your bot class. This function is called at the end of a game."""
