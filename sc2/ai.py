"""
Mother class for the bot_ai and observer_ai
"""
from typing import Set

from .ids.upgrade_id import UpgradeId
from sc2.units_to_prepare import UnitsToPrepare


class Ai(UnitsToPrepare):
    def __init__(self):
        super().__init__()
        self.opponent_id: str = None
        self.realtime: bool = False
        self.minerals: int = 0
        self.vespene: int = 0
        self.supply_army: float = 0
        self.supply_workers: float = 0
        self.supply_cap: float = 0
        self.supply_used: float = 0
        self.supply_left: float = 0
        self._previous_upgrades: Set[UpgradeId] = set()

    def _prepare_units(self):
        super().__init__()

    async def _issue_upgrade_events(self):
        difference = self.state.upgrades - self._previous_upgrades
        for upgrade_completed in difference:
            await self.on_upgrade_complete(upgrade_completed)
        self._previous_upgrades = self.state.upgrades
