from .units import Units
from typing import Set


class UnitsToPrepare:
    def __init__(self):
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