""" Group all parts of the bot
0.01 - First proper version (it only 12-pool now)
0.02 - Fix a bug on the ignored units implementation
0.03 - Update testing logic to allow every difficulty and style(except cheater difficulties for now) - (‭4896‬-352-2)
0.04 - Implement logic to connect to the SC2AI ladder
0.05 - Several non-functional changes to improve readability
0.06 - Make the first overlord only after the pool being placed
0.07 - Lock zergling production based on amount of supply_left
0.08 - Tweak zergling lock based on supply_left to 3 down from 5
0.09 - Make the zerglings attack without any constraint
0.10 - Make the drones target the closest mineral patch on the beginning of the game
0.11 - Prioritize static defense over other structures when attacking
0.12 - Prioritize bases over non static defense structures when attacking
0.13 - Implement a hail-mary attack logic -> if no more bases remaining, attack with everything that is left
"""
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class Mtsbot(BotAI):
    """ mtsbot"""

    async def on_end(self, game_result):
        print(game_result)

    async def split_workers_on_beginning(self):
        """ Improvements possible -> Prevent more than 2 drones going on the same mineral patch """
        for drone in self.workers:
            self.do(drone.gather(self.mineral_field.closest_to(drone)))

    async def build_pool(self):
        """ Build pool logic
        - improvements possible -> placement can be improved """
        pool = UnitTypeId.SPAWNINGPOOL  # to save line breaks
        if not self.structures(pool).ready and not self.already_pending(pool):
            await self.build(pool, self.start_location.towards(self.game_info.map_center, distance=5))

    async def build_extractor(self):
        """ Build extractor logic
        - improvements possible -> Expand it, with this function it's only possible to build the first one
        make it build more later(the requirement logic and the placement parameter will have to be expanded)"""
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
        keep adding ignored targets add micro and probably much more.
        Also, if the hail mary requirement triggers(no more bases) rebuild the base instead of attacking if possible """
        enemy_units = self.enemy_units.exclude_type({UnitTypeId.LARVA, UnitTypeId.EGG})
        enemy_structures = self.enemy_structures.not_flying
        enemy_static_defense_structures = enemy_structures.of_type(
            {
                UnitTypeId.BUNKER,
                UnitTypeId.PLANETARYFORTRESS,
                UnitTypeId.PHOTONCANNON,
                UnitTypeId.SHIELDBATTERY,
                UnitTypeId.SPINECRAWLER,
            }
        )
        enemy_bases = enemy_structures.of_type(
            {
                UnitTypeId.COMMANDCENTER,
                UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.NEXUS,
                UnitTypeId.HATCHERY,
                UnitTypeId.LAIR,
                UnitTypeId.HIVE,
            }
        )
        if not self.townhalls:
            for unit in self.all_units:
                self.do(unit.attack(self.enemy_start_locations[0]))
        else:
            for zergling in self.units(UnitTypeId.ZERGLING):
                if enemy_units.not_flying:
                    self.do(zergling.attack(enemy_units.not_flying.closest_to(zergling)))
                    continue
                if enemy_static_defense_structures:
                    self.do(zergling.attack(enemy_static_defense_structures.closest_to(zergling)))
                    continue
                if enemy_bases:
                    self.do(zergling.attack(enemy_bases.closest_to(zergling)))
                    continue
                if enemy_structures:
                    self.do(zergling.attack(enemy_structures.closest_to(zergling)))
                    continue
                self.do(zergling.attack(self.enemy_start_locations[0]))

    async def train_overlord(self):
        """Train overlord logic
        - improvements possible -> make amount pending scale with base amount,
         make supply left constraint scale with larva amount"""
        if (
            self.supply_left < 5
            and not self.already_pending(UnitTypeId.OVERLORD)
            and self.structures(UnitTypeId.SPAWNINGPOOL)
        ):
            self.train(UnitTypeId.OVERLORD)

    async def train_zergling(self):
        """Train zergling logic
        - improvements possible -> create constraints when other units starts to be built based on other unit amounts"""
        if self.structures(UnitTypeId.SPAWNINGPOOL).ready and (
            self.supply_left >= 3 or self.already_pending(UnitTypeId.OVERLORD)
        ):
            self.train(UnitTypeId.ZERGLING)

    async def train_queen(self):
        """Train queen logic
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
        if not iteration:
            await self.split_workers_on_beginning()
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
