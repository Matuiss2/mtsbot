"""
Groups useful data about elements of the game, very similar to game_info.py maybe merge both
"""
from __future__ import annotations

from typing import Set, Union

from .constants import FakeEffectID, FakeEffectRadii
from .data import ALLIANCE
from .ids.effect_id import EffectId
from .ids.upgrade_id import UpgradeId
from .pixel_map import PixelMap
from .position import Point2, Point3
from .score import ScoreDetails


class Blip:
    """
    It detects the visibility, ownership etc  of an unit
    """

    def __init__(self, proto):
        self.proto = proto

    @property
    def is_blip(self) -> bool:
        """Detected by sensor tower."""
        return self.proto.is_blip

    @property
    def position(self) -> Point2:
        """2d position of the blip."""
        return Point2.from_proto(self.proto.pos)

    @property
    def position3d(self) -> Point3:
        """3d position of the blip."""
        return Point3.from_proto(self.proto.pos)


class Common:
    """ It gets the common attributes"""

    ATTRIBUTES = [
        "player_id",
        "minerals",
        "vespene",
        "food_cap",
        "food_used",
        "food_army",
        "food_workers",
        "idle_worker_count",
        "army_count",
        "warp_gate_count",
    ]

    def __init__(self, proto):
        self.proto = proto

    def __getattr__(self, attr):
        if attr not in self.ATTRIBUTES:
            raise AssertionError(f"'{attr}' is not a valid attribute")
        return int(getattr(self.proto, attr))


class EffectData:
    """ Groups useful data about Effects"""

    def __init__(self, proto, fake=False):
        self.proto = proto
        self.fake = fake

    @property
    def id(self) -> Union[EffectId, str]:
        """ Returns the id of the effect"""
        if self.fake:
            # Returns the string from constants.py, e.g. "KD8CHARGE"
            return FakeEffectID[self.proto.unit_type]
        return EffectId(self.proto.effect_id)

    @property
    def positions(self) -> Set[Point2]:
        """ Returns the center of each part of the effect"""
        if self.fake:
            return {Point2.from_proto(self.proto.pos)}
        return {Point2.from_proto(p) for p in self.proto.pos}

    @property
    def alliance(self) -> ALLIANCE:
        """ Returns the team ownership of the effect"""
        return self.proto.alliance

    @property
    def owner(self) -> int:
        """ Same as above but instead of team ownership it returns the individual owner"""
        return self.proto.owner

    @property
    def radius(self) -> float:
        """ Returns the effect radius"""
        if self.fake:
            return FakeEffectRadii[self.proto.unit_type]
        return self.proto.radius

    def __repr__(self) -> str:
        """ Returns the representation of the effect showing it's id, radius and centers"""
        return f"{self.id} with radius {self.radius} at {self.positions}"


class GameState:
    """ Groups useful data about the game"""

    def __init__(self, response_observation):
        self.response_observation = response_observation
        self.actions = response_observation.actions  # successful actions since last loop
        self.action_errors = response_observation.action_errors  # error actions since last loop

        self.observation = response_observation.observation
        self.observation_raw = self.observation.raw_data
        self.alerts = self.observation.alerts
        self.player_result = response_observation.player_result
        self.chat = response_observation.chat
        self.common: Common = Common(self.observation.player_common)
        self.game_loop: int = self.observation.game_loop  # 22.4 per second on faster game speed

        self.score: ScoreDetails = ScoreDetails(self.observation.score)
        self.abilities = self.observation.abilities  # abilities of selected units
        self.upgrades: Set[UpgradeId] = {UpgradeId(upgrade) for upgrade in self.observation_raw.player.upgrade_ids}

        # Set of unit tags that died this step
        self.dead_units: Set[int] = set(self.observation_raw.event.dead_units)
        # self.visibility[position]: 0=Hidden, 1=Fogged, 2=Visible
        self.visibility: PixelMap = PixelMap(self.observation_raw.map_state.visibility, mirrored=False)
        # self.creep[position]: 0=No creep, 1=creep
        self.creep: PixelMap = PixelMap(self.observation_raw.map_state.creep, in_bits=True, mirrored=False)

        # Effects like ravager bile shot, lurker attack, everything in effect_id.py
        self.effects: Set[EffectData] = {EffectData(effect) for effect in self.observation_raw.effects}
