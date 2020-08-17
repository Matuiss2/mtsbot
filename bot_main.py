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
0.13.1 - Fix bug on the hail-mary logic -> 'self.all_units' went beyond the scope wanted, exchange it with 'self.units'
0.14 - Implement the initial retreat logic, add the constructor and do some refactoring
0.14.1 - Fix a bug on the retreat logic -> 1 zergling always stayed on the rally point due to a conflict on the distance
triggers, exchange one of the trigger values from 10 to 9
0.15 - Block attacks if there is any unit retreating, to try to coordinate the units better
0.16 - Newly trained zerglings that can't attack go directly to the rally point, another small change to help coordinate
units better
0.17 - Make the attacks trigger only within a small distance from the unit, to designate units better
0.17.1 - Treat a bug on position.py and unit.py -> __eq__ was getting the wrong type as a parameter on both files,
standardize then by converting other and self to Point2 in their respective __eq__ methods.
0.18 - Implement prefer_healthy method on the API and introduce separated testing logic directory
0.19 - Implement worker rush defense (28 - 0 - 2 vs basic worker rush)
0.20 - Handle drones that go idle
0.21 - Implement attack_closest_if_any method on the API
"""
from sc2.bot_ai import BotAI, Units
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class Mtsbot(BotAI):
    """ mtsbot"""

    def __init__(self):
        super().__init__()
        self.units_retreating = Units([], self)
        self.drone_defense_squad = Units([], self)
        self.close_enemy_workers = Units([], self)
        self.bases = Units([], self)
        self.main_base = None
        self.overlords_in_queue = Units([], self)
        self.pool_in_construction = Units([], self)
        self.finished_pool = Units([], self)
        self.queens = Units([], self)
        self.zerglings = Units([], self)
        self.enemy_starting_base = None
        self.enemy_units = Units([], self)
        self.ground_enemy_structures = Units([], self)
        self.ground_enemy_units = Units([], self)
        self.drones_on_extractor_count = 0
        self.extractor = UnitTypeId.EXTRACTOR
        self.overlord = UnitTypeId.OVERLORD
        self.pool = UnitTypeId.SPAWNINGPOOL
        self.queen = UnitTypeId.QUEEN
        self.worker_types = {UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV, UnitTypeId.MULE}
        self.zergling = UnitTypeId.ZERGLING
        self.zergling_speed = UpgradeId.ZERGLINGMOVEMENTSPEED

    async def on_end(self, game_result):
        print(game_result)

    async def update_variables(self):
        """ Improvements possible -> Could be a separated class and within that, separate by type(structures or units),
        and possession """
        self.enemy_units = self.enemy_units.exclude_type({UnitTypeId.LARVA, UnitTypeId.EGG})
        self.ground_enemy_structures = self.enemy_structures.not_flying
        self.ground_enemy_units = self.enemy_units.not_flying
        self.enemy_starting_base = self.enemy_start_locations[0]
        self.bases = self.townhalls
        self.main_base = self.bases[0]
        self.overlords_in_queue = self.already_pending(self.overlord)
        self.pool_in_construction = self.already_pending(self.pool)
        self.finished_pool = self.structures(self.pool).ready
        self.queens = self.units(self.queen)
        self.zerglings = self.units(self.zergling)
        if self.bases:
            self.close_enemy_workers = self.enemy_units.closer_than(6, self.main_base).of_type(self.worker_types)

    async def split_workers_on_beginning(self):
        """ Improvements possible -> Prevent more than 2 drones going on the same mineral patch """
        for drone in self.workers:
            self.do(drone.gather(self.mineral_field.closest_to(drone)))

    async def set_hatchery_rally_point(self):
        """ Improvements possible -> This should be called every time a new base is created and not only on the start"""
        self.do(self.main_base(AbilityId.RALLY_HATCHERY_UNITS, await self.get_rally_point()))

    async def build_pool(self):
        """ Build pool logic
        - improvements possible -> placement can be improved """
        if not self.finished_pool and not self.pool_in_construction:
            await self.build(self.pool, self.start_location.towards(self.game_info.map_center, distance=5))

    async def build_extractor(self):
        """ Build extractor logic
        - improvements possible -> Expand it, with this function it's only possible to build the first one
        make it build more later(the requirement logic and the placement parameter will have to be expanded)"""
        if not self.gas_buildings and self.pool_in_construction and not self.already_pending(self.extractor):
            await self.build(self.extractor, self.vespene_geyser.closest_to(self.start_location))

    async def queen_injection_logic(self):
        """ Make queen inject logic
        - improvements possible -> None that I can think of """
        for queen in self.queens:
            if not queen.is_idle or queen.energy < 25:
                continue
            self.do(queen(AbilityId.EFFECT_INJECTLARVA, self.bases.closest_to(queen.position)))

    async def research_zergling_speed(self):
        """ Research zergling speed logic
        - improvements possible -> None that I can think of """
        if not self.already_pending_upgrade(self.zergling_speed):
            self.research(self.zergling_speed)

    async def controlling_army(self):
        """ Attacking logic
        - improvements possible -> Add new units(later), keep adding ignored targets add micro and probably much more.
        Also, if the hail mary requirement triggers(no more bases) rebuild the base instead of attacking if possible """
        enemy_static_defense = self.ground_enemy_structures.of_type(
            {
                UnitTypeId.BUNKER,
                UnitTypeId.PLANETARYFORTRESS,
                UnitTypeId.PHOTONCANNON,
                UnitTypeId.SHIELDBATTERY,
                UnitTypeId.SPINECRAWLER,
            }
        )
        enemy_bases = self.ground_enemy_structures.of_type(
            {
                UnitTypeId.COMMANDCENTER,
                UnitTypeId.ORBITALCOMMAND,
                UnitTypeId.NEXUS,
                UnitTypeId.HATCHERY,
                UnitTypeId.LAIR,
                UnitTypeId.HIVE,
            }
        )
        if not self.bases:
            for unit in self.units:
                self.do(unit.attack(self.enemy_starting_base))
        else:
            for zergling in self.zerglings:
                if zergling in self.units_retreating:
                    if await self.empty_units_retreating_subgroup(zergling):
                        continue
                    await self.retreat_unit(zergling)
                    continue
                if await self.fill_units_retreating_subgroup(zergling):
                    continue
                if await self.block_attacks_while_retreating:
                    continue
                if await zergling.attack_closest_if_any(self.ground_enemy_units):
                    continue
                if await zergling.attack_closest_if_any(enemy_static_defense):
                    continue
                if await zergling.attack_closest_if_any(enemy_bases):
                    continue
                if await zergling.attack_closest_if_any(self.ground_enemy_structures):
                    continue
                self.do(zergling.attack(self.enemy_starting_base))

    @property
    async def block_attacks_while_retreating(self):
        """ Improvements possible -> This can be expanded, a lot more stuff can be used to block attacks,
        like when transitioning or booming, also it should not be used to block defensive orders like now"""
        return bool(self.units_retreating)

    async def get_rally_point(self):
        """ Improvements possible -> The path between the unit and the chosen rally point should be the one
        with the least enemy units """
        return self.bases.closest_to(self.enemy_starting_base).position.towards(self.enemy_starting_base, 9)

    async def fill_units_retreating_subgroup(self, fleeing_unit):
        """ Improvements possible -> The condition for retreating could be improved significantly by making it
         considerate only close ally units instead of all units like now.
         Also this method is only good for zerglings so it's very specialized, try to make it more general
         or make separated logic for different units """
        ground_enemy_army_size = len(self.ground_enemy_units.exclude_type(self.worker_types))
        if not self.bases.closer_than(15, fleeing_unit) and ground_enemy_army_size >= len(self.zerglings):
            if fleeing_unit.position.distance_to_point2(await self.get_rally_point()) > 5:
                self.units_retreating.append(fleeing_unit)
                return True

    async def empty_units_retreating_subgroup(self, fled_unit):
        """ Improvements possible -> The distance trigger could be different """
        if self.bases.closer_than(10, fled_unit):
            self.units_retreating.remove(fled_unit)
            return True

    async def retreat_unit(self, fleeing_unit):
        """ Improvements possible -> None"""
        self.do(fleeing_unit.move(await self.get_rally_point()))

    async def train_overlord(self):
        """Train overlord logic
        - improvements possible -> make amount pending scale with base amount,
         make supply left constraint scale with larva amount"""
        if self.supply_left < 5 and not self.overlords_in_queue and self.structures(self.pool):
            self.train(self.overlord)

    async def train_zergling(self):
        """ Improvements possible -> Create constraints when other units than zergling
        starts to be built based on this other unit amount"""
        if self.finished_pool and (self.supply_left >= 3 or self.overlords_in_queue):
            self.train(self.zergling)

    async def train_queen(self):
        """Train queen logic
        - improvements possible -> Make the queen get created preferably on non-already-assigned bases
         and maybe create some extra for creep spread(don't limit it by bases)"""
        if (
            self.finished_pool
            and len(self.queens) < len(self.bases)
            and self.already_pending(self.queen) < len(self.bases.ready)
            and len(self.close_enemy_workers) <= 1
        ):
            self.train(self.queen)

    async def controlling_drones(self):
        """ Improvements possible -> This can become a class, the variables and actions can be split and when multiple
        bases get implemented drones will have to be split in several subgroups ->
        one group for the base that it's assigned, also the function have different levels of abstraction,
        refactor it"""
        for drone in self.workers:
            if drone in self.drone_defense_squad:
                if await self.empty_drone_rush_defense_squad(drone):
                    continue
                self.do(drone.attack(self.close_enemy_workers.closest_to(drone)))
            if await self.fill_drone_rush_defense_squad(drone):
                continue
            if await self.send_drones_to_extractor(drone):
                continue
            if await self.send_drones_to_minerals(drone):
                continue

    async def send_drones_to_extractor(self, unit):
        """ Improvements possible -> Expand it, make it trigger when the vespene - mineral ratio is to high
        (only check it when at least 2 bases are saturated)make the distance_to value 8 instead of 10,
        also change the constraints completely(separate it later - this constraints are for the zergling speed,
        make it a separated method) make it more general, also this drone_on_extractor_count solution is awful,
        find a better way to make the right number of drones go collect on the same frame"""
        if self.vespene < 100 and not self.already_pending_upgrade(self.zergling_speed):
            extractors = self.gas_buildings.ready
            if extractors:
                closest_extractor = extractors.sorted_by_distance_to(unit)[0]
                if self.drones_on_extractor_count < 3 * len(extractors) and unit.distance_to(closest_extractor) < 10:
                    self.drones_on_extractor_count += 1
                    self.do(unit.gather(closest_extractor))
                    return True

    async def send_drones_to_minerals(self, unit):
        """ Improvements possible -> Expand it, make it trigger when the mineral - vespene ratio is to high
        (only check it when at least 2 bases are saturated), also change the constraints completely
        (separate it later - this constraints are for the zergling speed, make it a separated method)
        make it more general, also maybe the idle handling can be expanded to target vespene as well depending on the
        situation, I'm not sure if it's ever needed, remove if not"""
        if self.vespene >= 100 or self.already_pending_upgrade(self.zergling_speed):
            if unit.is_carrying_vespene or unit.is_idle:
                await self.gather_from_closest_mineral_patch(unit)
                return True

    async def fill_drone_rush_defense_squad(self, unit):
        """ Improvements possible -> None that I can think of"""
        ideal_defense_force_size = int(len(self.close_enemy_workers) * 1.25)
        drones_needed_to_fill_defense_squad = ideal_defense_force_size - len(self.drone_defense_squad)
        if drones_needed_to_fill_defense_squad > 0 and unit not in self.drone_defense_squad:
            self.drone_defense_squad.append(unit)
            return True

    async def empty_drone_rush_defense_squad(self, unit):
        """ Improvements possible -> None that I can think of"""
        if not self.close_enemy_workers:
            self.drone_defense_squad.remove(unit)
            await self.gather_from_closest_mineral_patch(unit)
            return True

    async def gather_from_closest_mineral_patch(self, unit):
        """ Improvements possible -> None"""
        self.do(unit.gather(self.mineral_field.closest_to(unit)))

    async def on_step(self, iteration):
        await self.update_variables()
        if not iteration:
            await self.split_workers_on_beginning()
            await self.set_hatchery_rally_point()
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
        await self.controlling_army()
        await self.queen_injection_logic()
        # Control workers
        await self.controlling_drones()
