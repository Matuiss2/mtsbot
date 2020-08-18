"""
Houses combine_actions, can maybe be absorbed by client.py
"""
from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING, Union

from s2clientprotocol import common_pb2 as common_pb
from s2clientprotocol import raw_pb2 as raw_pb

from .position import Point2
from .unit import Unit

if TYPE_CHECKING:
    from .ids.ability_id import AbilityId
    from .unit_command import UnitCommand


def combine_actions(action_iter):
    """
    Example input:
    [
        # Each entry in the list is a unit command, with an ability, unit, target, and queue=boolean
        UnitCommand(AbilityId.TRAINQUEEN_QUEEN, Unit(name='Hive', tag=4353687554), None, False),
        UnitCommand(AbilityId.TRAINQUEEN_QUEEN, Unit(name='Lair', tag=4359979012), None, False),
        UnitCommand(AbilityId.TRAINQUEEN_QUEEN, Unit(name='Hatchery', tag=4359454723), None, False),
    ]
    Return one action for each unit; this is required for certain commands that would otherwise be
    grouped, and only executed once Examples: Select 3 hatcheries, build a queen with each hatch - the
    grouping function would group these unit tags and only issue one train command once to all 3 unit tags -
    resulting in one total train command I imagine the same thing would happen to certain other abilities:
    Battlecruiser yamato on same target, queen transfuse on same target, ghost snipe on same target,
    all build commands with the same unit type and also all morphs (zergling to banelings) However,
    other abilities can and should be grouped, see constants.py 'COMBINABLE_ABILITIES' """
    for key, items in groupby(action_iter, key=lambda a: a.combining_tuple):
        ability: AbilityId
        target: Union[None, Point2, Unit]
        queue: bool
        # See constants.py for combinable abilities
        combinable: bool
        ability, target, queue, combinable = key

        if combinable:
            if target is None:
                cmd = raw_pb.ActionRawUnitCommand(
                    ability_id=ability.value, unit_tags={u.unit.tag for u in items}, queue_command=queue
                )
            elif isinstance(target, Point2):
                cmd = raw_pb.ActionRawUnitCommand(
                    ability_id=ability.value,
                    unit_tags={u.unit.tag for u in items},
                    queue_command=queue,
                    target_world_space_pos=common_pb.Point2D(x=target.x, y=target.y),
                )
            elif isinstance(target, Unit):
                cmd = raw_pb.ActionRawUnitCommand(
                    ability_id=ability.value,
                    unit_tags={u.unit.tag for u in items},
                    queue_command=queue,
                    target_unit_tag=target.tag,
                )
            else:
                raise RuntimeError(f"Must target a unit, point or None, found '{target !r}'")

            yield raw_pb.ActionRaw(unit_command=cmd)

        else:

            item: UnitCommand
            if target is None:
                for item in items:
                    cmd = raw_pb.ActionRawUnitCommand(
                        ability_id=ability.value, unit_tags={item.unit.tag}, queue_command=queue
                    )
                    yield raw_pb.ActionRaw(unit_command=cmd)
            elif isinstance(target, Point2):
                for item in items:
                    cmd = raw_pb.ActionRawUnitCommand(
                        ability_id=ability.value,
                        unit_tags={item.unit.tag},
                        queue_command=queue,
                        target_world_space_pos=common_pb.Point2D(x=target.x, y=target.y),
                    )
                    yield raw_pb.ActionRaw(unit_command=cmd)

            elif isinstance(target, Unit):
                for item in items:
                    cmd = raw_pb.ActionRawUnitCommand(
                        ability_id=ability.value,
                        unit_tags={item.unit.tag},
                        queue_command=queue,
                        target_unit_tag=target.tag,
                    )
                    yield raw_pb.ActionRaw(unit_command=cmd)
            else:
                raise RuntimeError(f"Must target a unit, point or None, found '{target !r}'")
