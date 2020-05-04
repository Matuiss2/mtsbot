"""
Mother class for the bot_ai and observer_ai
"""
from typing import Set

from .game_state import Blip
from .units import Units
from .ids.upgrade_id import UpgradeId


class Ai:
    def __init__(self):
        self.opponent_id: str = None
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
        self.blips: Set[Blip] = set()
        self.minerals: int = 0
        self.vespene: int = 0
        self.supply_army: float = 0
        self.supply_workers: float = 0
        self.supply_cap: float = 0
        self.supply_used: float = 0
        self.supply_left: float = 0
        self._previous_upgrades: Set[UpgradeId] = set()

    def _prepare_units(self):
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

    async def _issue_upgrade_events(self):
        difference = self.state.upgrades - self._previous_upgrades
        for upgrade_completed in difference:
            await self.on_upgrade_complete(upgrade_completed)
        self._previous_upgrades = self.state.upgrades
