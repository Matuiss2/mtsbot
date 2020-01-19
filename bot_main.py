""" Group all parts of the bot
0.01 - first proper version (it only 12-pool now)"""
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class Mtsbot(BotAI):
    """ mtsbot"""

    async def on_end(self, game_result):
        print(game_result)

    async def build_pool(self):
        """ Build pool logic
        - improvements possible -> placement can be improved """
        pool = UnitTypeId.SPAWNINGPOOL  # to save line breaks
        if not self.structures(pool).ready and not self.already_pending(pool):
            await self.build(pool, self.start_location.towards(self.game_info.map_center, distance=5))

    async def build_extractor(self):
        """ Build extractor logic
        - improvements possible -> None that I can think of """
        if (
            not self.gas_buildings
            and self.already_pending(UnitTypeId.SPAWNINGPOOL)
            and not self.already_pending(UnitTypeId.EXTRACTOR)
        ):
            await self.build(UnitTypeId.EXTRACTOR, self.vespene_geyser.closest_to(self.start_location))

    async def queen_injection_logic(self):
        """ Make queen inject logic
        - improvements possible -> None that I can think of """
        for queen in self.units(UnitTypeId.QUEEN):
            if not queen.is_idle or queen.energy < 25:
                continue
            self.do(queen(AbilityId.EFFECT_INJECTLARVA, self.townhalls.closest_to(queen.position)))

    async def research_zergling_speed(self):
        """ Research zergling speed logic
        - improvements possible -> None that I can think of """
        if not self.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED):
            self.research(UpgradeId.ZERGLINGMOVEMENTSPEED)

    async def attacking_logic(self):
        """ Attacking logic
        - improvements possible -> Add new units(later), add retreat logic(other function),
        keep adding ignored targets add micro and probably much more"""
        enemy_units = self.enemy_units.exclude_type({UnitTypeId.LARVA, UnitTypeId.EGG})
        if len(self.units(UnitTypeId.ZERGLING)) >= 6:
            for zergling in self.units(UnitTypeId.ZERGLING):
                if enemy_units.not_flying:
                    self.do(zergling.attack(enemy_units.not_flying.closest_to(zergling)))
                    continue
                if self.enemy_structures.not_flying:
                    self.do(zergling.attack(self.enemy_structures.not_flying.closest_to(zergling)))
                    continue
                self.do(zergling.attack(self.enemy_start_locations[0]))

    async def train_overlord(self):
        """Train overlord logic
        - improvements possible -> make amount pending scale with base amount,
         make supply left constraint scale with larva amount"""
        if self.supply_left < 3 and not self.already_pending(UnitTypeId.OVERLORD):
            self.train(UnitTypeId.OVERLORD)

    async def train_zergling(self):
        """Train zergling logic
        - improvements possible -> create constraints when other units starts to be built based on other unit amounts"""
        if self.structures(UnitTypeId.SPAWNINGPOOL).ready:
            self.train(UnitTypeId.ZERGLING)

    async def train_queen(self):
        """Train zergling logic
        - improvements possible -> Make the queen get created preferably on non-already-assigned bases
         and maybe create some extra for creep spread(don't limit it by bases)"""
        if (
            self.structures(UnitTypeId.SPAWNINGPOOL).ready
            and len(self.units(UnitTypeId.QUEEN)) < len(self.townhalls)
            and self.already_pending(UnitTypeId.QUEEN) < len(self.townhalls.ready)
        ):
            self.train(UnitTypeId.QUEEN)

    async def send_drones_to_extractor(self):
        """ Send drones to extractor from minerals
        - improvements possible -> Expand it, make it trigger when the vespene - mineral ratio is to high
        (only check it when at least 2 bases are saturated)make the closer_than distance 8 instead of 10,
        also change the constraints completely(separate it later - this constraints are for the zergling speed,
        make it a separated method) make it more general"""
        if self.vespene < 100 and not self.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED):
            for extractor in self.gas_buildings:
                drones_needed_to_fill_extractor = extractor.ideal_harvesters - extractor.assigned_harvesters
                if drones_needed_to_fill_extractor > 0:
                    for drone in self.workers.closer_than(10, extractor).take(drones_needed_to_fill_extractor):
                        self.do(drone.gather(extractor))

    async def send_drones_to_minerals(self):
        """ Send drones from extractor to minerals
        - improvements possible -> Expand it, make it trigger when the mineral - vespene ratio is to high
        (only check it when at least 2 bases are saturated)make the closer_than distance 8 instead of 10,
        also change the constraints completely(separate it later - this constraints are for the zergling speed,
        make it a separated method) make it more general"""
        if self.vespene >= 100 or self.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED):
            for drone in self.workers.filter(lambda w: w.is_carrying_vespene):
                self.do(drone.gather(self.mineral_field.closer_than(10, drone).closest_to(drone)))

    async def on_step(self, iteration):
        # Build structures
        await self.build_extractor()
        await self.build_pool()
        # Train units
        await self.train_overlord()
        await self.train_queen()
        await self.train_zergling()
        # Research upgrades
        await self.research_zergling_speed()
        # Control army units
        await self.attacking_logic()
        await self.queen_injection_logic()
        # Control workers
        await self.send_drones_to_extractor()
        await self.send_drones_to_minerals()
