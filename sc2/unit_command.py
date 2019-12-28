"""
Allows the combining of all possible abilities that every unit can do,
in short all possible unit commands, I'm not sure a new file for this is needed
changed last: 28/12/2019
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Union

from . import unit as unit_module
from .constants import COMBINABLE_ABILITIES
from .ids.ability_id import AbilityId
from .position import Point2

if TYPE_CHECKING:
    from .unit import Unit


class UnitCommand:
    """ Allows combining all possible abilities that every unit can do on every possible target"""
    def __init__(self, ability: AbilityId, unit: Unit, target: Union[Unit, Point2] = None, queue: bool = False):
        """
        :param ability:
        :param unit:
        :param target:
        :param queue:
        """
        if ability not in AbilityId:
            raise AssertionError(f"ability {ability} is not in AbilityId")
        if not isinstance(unit, unit_module.Unit):
            raise AssertionError(f"unit {unit} is of type {type(unit)}")
        if not (target is None or isinstance(target, (Point2, unit_module.Unit))):
            raise AssertionError(f"target {target} is of type {type(target)}")
        if not isinstance(queue, bool):
            raise AssertionError(f"queue flag {queue} is of type {type(queue)}")
        self.ability = ability
        self.unit = unit
        self.target = target
        self.queue = queue

    @property
    def combining_tuple(self):
        """ Combines the wanted ability, target, queue and ability for the bot """
        return self.ability, self.target, self.queue, self.ability in COMBINABLE_ABILITIES

    def __repr__(self):
        return f"UnitCommand({self.ability}, {self.unit}, {self.target}, {self.queue})"
