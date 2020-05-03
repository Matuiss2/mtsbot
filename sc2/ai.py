"""
Mother class for the bot_ai and observer_ai
"""
from .units import Units


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
