"""
Groups all scoring that can be done in SC2(the comments might be all wrong, since this was never tested)
"""


class ScoreDetails:
    """Accessible in self.state.score during step function
    For more information, see https://github.com/Blizzard/s2client-proto/blob/master/s2clientprotocol/score.proto
    """

    def __init__(self, proto):
        self._data = proto
        self.proto = proto.score_details

    @property
    def summary(self):
        """
        Print summary to file with:
        In on_step:

        with open("stats.txt", "w+") as file:
            for stat in self.state.score.summary:
                file.write(f"{stat[0]:<35} {float(stat[1]):>35.3f}\n")
        """
        values = [
            "score_type",
            "score",
            "idle_production_time",
            "idle_worker_time",
            "total_value_units",
            "total_value_structures",
            "killed_value_units",
            "killed_value_structures",
            "collected_minerals",
            "collected_vespene",
            "collection_rate_minerals",
            "collection_rate_vespene",
            "spent_minerals",
            "spent_vespene",
            "food_used_none",
            "food_used_army",
            "food_used_economy",
            "food_used_technology",
            "food_used_upgrade",
            "killed_minerals_none",
            "killed_minerals_army",
            "killed_minerals_economy",
            "killed_minerals_technology",
            "killed_minerals_upgrade",
            "killed_vespene_none",
            "killed_vespene_army",
            "killed_vespene_economy",
            "killed_vespene_technology",
            "killed_vespene_upgrade",
            "lost_minerals_none",
            "lost_minerals_army",
            "lost_minerals_economy",
            "lost_minerals_technology",
            "lost_minerals_upgrade",
            "lost_vespene_none",
            "lost_vespene_army",
            "lost_vespene_economy",
            "lost_vespene_technology",
            "lost_vespene_upgrade",
            "friendly_fire_minerals_none",
            "friendly_fire_minerals_army",
            "friendly_fire_minerals_economy",
            "friendly_fire_minerals_technology",
            "friendly_fire_minerals_upgrade",
            "friendly_fire_vespene_none",
            "friendly_fire_vespene_army",
            "friendly_fire_vespene_economy",
            "friendly_fire_vespene_technology",
            "friendly_fire_vespene_upgrade",
            "used_minerals_none",
            "used_minerals_army",
            "used_minerals_economy",
            "used_minerals_technology",
            "used_minerals_upgrade",
            "used_vespene_none",
            "used_vespene_army",
            "used_vespene_economy",
            "used_vespene_technology",
            "used_vespene_upgrade",
            "total_used_minerals_none",
            "total_used_minerals_army",
            "total_used_minerals_economy",
            "total_used_minerals_technology",
            "total_used_minerals_upgrade",
            "total_used_vespene_none",
            "total_used_vespene_army",
            "total_used_vespene_economy",
            "total_used_vespene_technology",
            "total_used_vespene_upgrade",
            "total_damage_dealt_life",
            "total_damage_dealt_shields",
            "total_damage_dealt_energy",
            "total_damage_taken_life",
            "total_damage_taken_shields",
            "total_damage_taken_energy",
            "total_healed_life",
            "total_healed_shields",
            "total_healed_energy",
            "current_apm",
            "current_effective_apm",
        ]
        return [[value, getattr(self, value)] for value in values]

    @property
    def score_type(self):
        """ Returns the score type """
        return self._data.score_type

    @property
    def score(self):
        """ Returns the score """
        return self._data.score

    @property
    def idle_production_time(self):
        """ Returns the amount of time that the all production facilities stayed idle"""
        return self.proto.idle_production_time

    @property
    def idle_worker_time(self):
        """ Returns the amount of time that at least 1 worker stayed idle"""
        return self.proto.idle_worker_time

    @property
    def total_value_units(self):
        """ Returns the total value of your units"""
        return self.proto.total_value_units

    @property
    def total_value_structures(self):
        """ Returns the total value of your structures"""
        return self.proto.total_value_structures

    @property
    def killed_value_units(self):
        """ Returns the total value of the units that you killed"""
        return self.proto.killed_value_units

    @property
    def killed_value_structures(self):
        """ Returns the total value of the structures that you killed"""
        return self.proto.killed_value_structures

    @property
    def collected_minerals(self):
        """ Returns the total amount of minerals collected"""
        return self.proto.collected_minerals

    @property
    def collected_vespene(self):
        """ Returns the total amount of vespene collected"""
        return self.proto.collected_vespene

    @property
    def collection_rate_minerals(self):
        """ Returns the collection rate of minerals collected"""
        return self.proto.collection_rate_minerals

    @property
    def collection_rate_vespene(self):
        """ Returns the collection rate of vespene collected"""
        return self.proto.collection_rate_vespene

    @property
    def spent_minerals(self):
        """ Returns the total amount of minerals collected"""
        return self.proto.spent_minerals

    @property
    def spent_vespene(self):
        """ Returns the total amount of vespene collected"""
        return self.proto.spent_vespene

    @property
    def food_used_none(self):
        """ Not sure what it does"""
        return self.proto.food_used.none

    @property
    def food_used_army(self):
        """ Returns the total amount of food used creating an army"""
        return self.proto.food_used.army

    @property
    def food_used_economy(self):
        """ Returns the total amount of food used creating workers"""
        return self.proto.food_used.economy

    @property
    def food_used_technology(self):
        """ Not sure what it does"""
        return self.proto.food_used.technology

    @property
    def food_used_upgrade(self):
        """ Not sure what it does"""
        return self.proto.food_used.upgrade

    @property
    def killed_minerals_none(self):
        """ Not sure what it does"""
        return self.proto.killed_minerals.none

    @property
    def killed_minerals_army(self):
        """ Returns the total mineral value of the units that you killed"""
        return self.proto.killed_minerals.army

    @property
    def killed_minerals_economy(self):
        """ Returns the total mineral value of the workers that you killed"""
        return self.proto.killed_minerals.economy

    @property
    def killed_minerals_technology(self):
        """ Not sure what it does"""
        return self.proto.killed_minerals.technology

    @property
    def killed_minerals_upgrade(self):
        """ Not sure what it does"""
        return self.proto.killed_minerals.upgrade

    @property
    def killed_vespene_none(self):
        """ Not sure what it does"""
        return self.proto.killed_vespene.none

    @property
    def killed_vespene_army(self):
        """ Returns the total vespene value of the units that you killed """
        return self.proto.killed_vespene.army

    @property
    def killed_vespene_economy(self):
        """ Returns the total vespene value of the workers that you killed """
        return self.proto.killed_vespene.economy

    @property
    def killed_vespene_technology(self):
        """ Not sure what it does"""
        return self.proto.killed_vespene.technology

    @property
    def killed_vespene_upgrade(self):
        """ Not sure what it does"""
        return self.proto.killed_vespene.upgrade

    @property
    def lost_minerals_none(self):
        """ Not sure what it does"""
        return self.proto.lost_minerals.none

    @property
    def lost_minerals_army(self):
        """ Returns the total mineral value of the units that you lost"""
        return self.proto.lost_minerals.army

    @property
    def lost_minerals_economy(self):
        """ Returns the total mineral value of the workers that you lost"""
        return self.proto.lost_minerals.economy

    @property
    def lost_minerals_technology(self):
        """ Not sure what it does"""
        return self.proto.lost_minerals.technology

    @property
    def lost_minerals_upgrade(self):
        """ Not sure what it does"""
        return self.proto.lost_minerals.upgrade

    @property
    def lost_vespene_none(self):
        """ Not sure what it does"""
        return self.proto.lost_vespene.none

    @property
    def lost_vespene_army(self):
        """ Returns the total vespene value of the army that you killed """
        return self.proto.lost_vespene.army

    @property
    def lost_vespene_economy(self):
        """ Returns the total vespene value of the workers that you killed """
        return self.proto.lost_vespene.economy

    @property
    def lost_vespene_technology(self):
        """ Not sure what it does"""
        return self.proto.lost_vespene.technology

    @property
    def lost_vespene_upgrade(self):
        """ Not sure what it does"""
        return self.proto.lost_vespene.upgrade

    @property
    def friendly_fire_minerals_none(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_minerals.none

    @property
    def friendly_fire_minerals_army(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_minerals.army

    @property
    def friendly_fire_minerals_economy(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_minerals.economy

    @property
    def friendly_fire_minerals_technology(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_minerals.technology

    @property
    def friendly_fire_minerals_upgrade(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_minerals.upgrade

    @property
    def friendly_fire_vespene_none(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_vespene.none

    @property
    def friendly_fire_vespene_army(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_vespene.army

    @property
    def friendly_fire_vespene_economy(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_vespene.economy

    @property
    def friendly_fire_vespene_technology(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_vespene.technology

    @property
    def friendly_fire_vespene_upgrade(self):
        """ Not sure what it does"""
        return self.proto.friendly_fire_vespene.upgrade

    @property
    def used_minerals_none(self):
        """ Returns the mineral value that was not used"""
        return self.proto.used_minerals.none

    @property
    def used_minerals_army(self):
        """ Returns the mineral value of the army that you created"""
        return self.proto.used_minerals.army

    @property
    def used_minerals_economy(self):
        """ Returns the mineral value of the workers that you created"""
        return self.proto.used_minerals.economy

    @property
    def used_minerals_technology(self):
        """ Not sure what it does"""
        return self.proto.used_minerals.technology

    @property
    def used_minerals_upgrade(self):
        """ Not sure what it does"""
        return self.proto.used_minerals.upgrade

    @property
    def used_vespene_none(self):
        """ Returns the vespene value that was not used"""
        return self.proto.used_vespene.none

    @property
    def used_vespene_army(self):
        """ Returns the vespene value of the army that you created"""
        return self.proto.used_vespene.army

    @property
    def used_vespene_economy(self):
        """ Returns the vespene value of the worker(?) that you created"""
        return self.proto.used_vespene.economy

    @property
    def used_vespene_technology(self):
        """ Not sure what it does"""
        return self.proto.used_vespene.technology

    @property
    def used_vespene_upgrade(self):
        """ Not sure what it does"""
        return self.proto.used_vespene.upgrade

    @property
    def total_used_minerals_none(self):
        """ Returns the mineral value that was not used the whole game (accumulative)"""
        return self.proto.total_used_minerals.none

    @property
    def total_used_minerals_army(self):
        """ Returns the mineral value that was used on army the whole game (accumulative)"""
        return self.proto.total_used_minerals.army

    @property
    def total_used_minerals_economy(self):
        """ Returns the mineral value that was used on workers the whole game (accumulative)"""
        return self.proto.total_used_minerals.economy

    @property
    def total_used_minerals_technology(self):
        """ Not sure what it does"""
        return self.proto.total_used_minerals.technology

    @property
    def total_used_minerals_upgrade(self):
        """ Not sure what it does"""
        return self.proto.total_used_minerals.upgrade

    @property
    def total_used_vespene_none(self):
        """ Returns the vespene value that was not used the whole game (accumulative)"""
        return self.proto.total_used_vespene.none

    @property
    def total_used_vespene_army(self):
        """ Returns the vespene value that was used creating army the whole game (accumulative)"""
        return self.proto.total_used_vespene.army

    @property
    def total_used_vespene_economy(self):
        """ Returns the vespene value that was used creating workers the whole game (accumulative)"""
        return self.proto.total_used_vespene.economy

    @property
    def total_used_vespene_technology(self):
        """ Not sure what it does"""
        return self.proto.total_used_vespene.technology

    @property
    def total_used_vespene_upgrade(self):
        """ Not sure what it does"""
        return self.proto.total_used_vespene.upgrade

    @property
    def total_damage_dealt_life(self):
        """ Returns the total amount of damage to enemies hp the whole game (accumulative)"""
        return self.proto.total_damage_dealt.life

    @property
    def total_damage_dealt_shields(self):
        """ Returns the total amount of damage to enemies shield the whole game (accumulative)"""
        return self.proto.total_damage_dealt.shields

    @property
    def total_damage_dealt_energy(self):
        """ Returns the total amount of damage to enemies energy the whole game (accumulative)"""
        return self.proto.total_damage_dealt.energy

    @property
    def total_damage_taken_life(self):
        """ Returns the total amount of damage to your units hp the whole game (accumulative)"""
        return self.proto.total_damage_taken.life

    @property
    def total_damage_taken_shields(self):
        """ Returns the total amount of damage to your units shield the whole game (accumulative)"""
        return self.proto.total_damage_taken.shields

    @property
    def total_damage_taken_energy(self):
        """ Returns the total amount of damage to your units energy the whole game (accumulative)"""
        return self.proto.total_damage_taken.energy

    @property
    def total_healed_life(self):
        """ Returns the total amount of hp your units recovered the whole game (accumulative)"""
        return self.proto.total_healed.life

    @property
    def total_healed_shields(self):
        """ Returns the total amount of shield your units recovered the whole game (accumulative)"""
        return self.proto.total_healed.shields

    @property
    def total_healed_energy(self):
        """ Returns the total amount of energy your units recovered the whole game (accumulative)"""
        return self.proto.total_healed.energy

    @property
    def current_apm(self):
        """ Returns the current apm"""
        return self.proto.current_apm

    @property
    def current_effective_apm(self):
        """ Returns the current effective apm"""
        return self.proto.current_effective_apm
