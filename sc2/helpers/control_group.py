"""
Group everything about the simulation of the sc2 control groups
"""


class ControlGroup(set):
    """ Simulation of the sc2 control groups"""

    def __init__(self, units):
        super().__init__({unit.tag for unit in units})

    def __hash__(self):
        return hash(tuple(sorted(list(self))))

    def select_units(self, units):
        """ Select all units on this control group"""
        return units.filter(lambda unit: unit.tag in self)

    def missing_unit_tags(self, units):
        """ Check if the given units are on the control group and then return the ones that aren't """
        return {t for t in self if units.find_by_tag(t) is None}

    def add_unit(self, unit):
        """ Add given unit to this control group"""
        self.add(unit.tag)

    def add_units(self, units):
        """ Add given units to this control group"""
        for unit in units:
            self.add_unit(unit)

    def remove_unit(self, unit):
        """ Remove given unit to this control group"""
        self.discard(unit.tag)

    def remove_units(self, units):
        """ Remove given units to this control group"""
        for unit in units:
            self.discard(unit.tag)
