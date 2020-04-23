"""
Renames units that are on a different state(burrowed, flying)as the original unit
(it makes sense since it's the same unit)
"""
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from typing import Dict

from ..ids.unit_typeid import UnitTypeId

# from ..ids.buff_id import BuffId
# from ..ids.effect_id import EffectId

UNIT_UNIT_ALIAS: Dict[UnitTypeId, UnitTypeId] = {
    UnitTypeId.ADEPTPHASESHIFT: UnitTypeId.ADEPT,
    UnitTypeId.ASSIMILATORRICH: UnitTypeId.ASSIMILATOR,
    UnitTypeId.BANELINGBURROWED: UnitTypeId.BANELING,
    UnitTypeId.BARRACKSFLYING: UnitTypeId.BARRACKS,
    UnitTypeId.CHANGELINGMARINE: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGMARINESHIELD: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGZEALOT: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGZERGLING: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGZERGLINGWINGS: UnitTypeId.CHANGELING,
    UnitTypeId.COMMANDCENTERFLYING: UnitTypeId.COMMANDCENTER,
    UnitTypeId.CREEPTUMORBURROWED: UnitTypeId.CREEPTUMOR,
    UnitTypeId.CREEPTUMORQUEEN: UnitTypeId.CREEPTUMOR,
    UnitTypeId.DRONEBURROWED: UnitTypeId.DRONE,
    UnitTypeId.EXTRACTORRICH: UnitTypeId.EXTRACTOR,
    UnitTypeId.FACTORYFLYING: UnitTypeId.FACTORY,
    UnitTypeId.GHOSTNOVA: UnitTypeId.GHOST,
    UnitTypeId.HERCPLACEMENT: UnitTypeId.HERC,
    UnitTypeId.HYDRALISKBURROWED: UnitTypeId.HYDRALISK,
    UnitTypeId.INFESTORBURROWED: UnitTypeId.INFESTOR,
    UnitTypeId.INFESTORTERRANBURROWED: UnitTypeId.INFESTORTERRAN,
    UnitTypeId.LIBERATORAG: UnitTypeId.LIBERATOR,
    UnitTypeId.LOCUSTMPFLYING: UnitTypeId.LOCUSTMP,
    UnitTypeId.LURKERMPBURROWED: UnitTypeId.LURKERMP,
    UnitTypeId.OBSERVERSIEGEMODE: UnitTypeId.OBSERVER,
    UnitTypeId.ORBITALCOMMANDFLYING: UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.OVERSEERSIEGEMODE: UnitTypeId.OVERSEER,
    UnitTypeId.PYLONOVERCHARGED: UnitTypeId.PYLON,
    UnitTypeId.QUEENBURROWED: UnitTypeId.QUEEN,
    UnitTypeId.RAVAGERBURROWED: UnitTypeId.RAVAGER,
    UnitTypeId.REFINERYRICH: UnitTypeId.REFINERY,
    UnitTypeId.ROACHBURROWED: UnitTypeId.ROACH,
    UnitTypeId.SIEGETANKSIEGED: UnitTypeId.SIEGETANK,
    UnitTypeId.SPINECRAWLERUPROOTED: UnitTypeId.SPINECRAWLER,
    UnitTypeId.SPORECRAWLERUPROOTED: UnitTypeId.SPORECRAWLER,
    UnitTypeId.STARPORTFLYING: UnitTypeId.STARPORT,
    UnitTypeId.SUPPLYDEPOTLOWERED: UnitTypeId.SUPPLYDEPOT,
    UnitTypeId.SWARMHOSTBURROWEDMP: UnitTypeId.SWARMHOSTMP,
    UnitTypeId.THORAP: UnitTypeId.THOR,
    UnitTypeId.ULTRALISKBURROWED: UnitTypeId.ULTRALISK,
    UnitTypeId.VIKINGASSAULT: UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.WARPPRISMPHASING: UnitTypeId.WARPPRISM,
    UnitTypeId.WIDOWMINEBURROWED: UnitTypeId.WIDOWMINE,
    UnitTypeId.ZERGLINGBURROWED: UnitTypeId.ZERGLING,
}
