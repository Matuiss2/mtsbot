"""
Renames several similar structures as one grouped structure(create alias for complicated and long ids)
changed last: 28/12/2019
"""
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from typing import Dict, Set

from ..ids.unit_typeid import UnitTypeId

# from ..ids.buff_id import BuffId
# from ..ids.effect_id import EffectId

UNIT_TECH_ALIAS: Dict[UnitTypeId, Set[UnitTypeId]] = {
    UnitTypeId.ASSIMILATORRICH: {UnitTypeId.ASSIMILATOR},
    UnitTypeId.BARRACKSFLYING: {UnitTypeId.BARRACKS},
    UnitTypeId.BARRACKSREACTOR: {UnitTypeId.REACTOR},
    UnitTypeId.BARRACKSTECHLAB: {UnitTypeId.TECHLAB},
    UnitTypeId.COMMANDCENTERFLYING: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.CREEPTUMORBURROWED: {UnitTypeId.CREEPTUMOR},
    UnitTypeId.CREEPTUMORQUEEN: {UnitTypeId.CREEPTUMOR},
    UnitTypeId.EXTRACTORRICH: {UnitTypeId.EXTRACTOR},
    UnitTypeId.FACTORYFLYING: {UnitTypeId.FACTORY},
    UnitTypeId.FACTORYREACTOR: {UnitTypeId.REACTOR},
    UnitTypeId.FACTORYTECHLAB: {UnitTypeId.TECHLAB},
    UnitTypeId.GREATERSPIRE: {UnitTypeId.SPIRE},
    UnitTypeId.HIVE: {UnitTypeId.HATCHERY, UnitTypeId.LAIR},
    UnitTypeId.LAIR: {UnitTypeId.HATCHERY},
    UnitTypeId.LIBERATORAG: {UnitTypeId.LIBERATOR},
    UnitTypeId.ORBITALCOMMAND: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.ORBITALCOMMANDFLYING: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.OVERLORDTRANSPORT: {UnitTypeId.OVERLORD},
    UnitTypeId.OVERSEER: {UnitTypeId.OVERLORD},
    UnitTypeId.OVERSEERSIEGEMODE: {UnitTypeId.OVERLORD},
    UnitTypeId.PLANETARYFORTRESS: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.PYLONOVERCHARGED: {UnitTypeId.PYLON},
    UnitTypeId.QUEENBURROWED: {UnitTypeId.QUEEN},
    UnitTypeId.REFINERYRICH: {UnitTypeId.REFINERY},
    UnitTypeId.SIEGETANKSIEGED: {UnitTypeId.SIEGETANK},
    UnitTypeId.STARPORTFLYING: {UnitTypeId.STARPORT},
    UnitTypeId.STARPORTREACTOR: {UnitTypeId.REACTOR},
    UnitTypeId.STARPORTTECHLAB: {UnitTypeId.TECHLAB},
    UnitTypeId.SUPPLYDEPOTLOWERED: {UnitTypeId.SUPPLYDEPOT},
    UnitTypeId.THORAP: {UnitTypeId.THOR},
    UnitTypeId.VIKINGASSAULT: {UnitTypeId.VIKING},
    UnitTypeId.VIKINGFIGHTER: {UnitTypeId.VIKING},
    UnitTypeId.WARPGATE: {UnitTypeId.GATEWAY},
    UnitTypeId.WARPPRISMPHASING: {UnitTypeId.WARPPRISM},
    UnitTypeId.WIDOWMINEBURROWED: {UnitTypeId.WIDOWMINE},
}
