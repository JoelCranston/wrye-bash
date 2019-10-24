# -*- coding: utf-8 -*-
#
# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""This package contains the Oblivion specific patchers. This module
contains the data structures that are dynamically set on a per game basis in
bush."""
from ....patcher import PatcherInfo as pi
from .importers import RoadImporter, CBash_RoadImporter
from .special import AlchemicalCatalogs, CBash_AlchemicalCatalogs, \
    SEWorldEnforcer, CBash_SEWorldEnforcer, CoblExhaustion, \
    CBash_CoblExhaustion, MFactMarker, CBash_MFactMarker

gameSpecificPatchers = {
    # special
    "AlchemicalCatalogs": pi(AlchemicalCatalogs, 'CBash_AlchemicalCatalogs', AlchemicalCatalogs.patcher_text),
    "CBash_AlchemicalCatalogs": pi(CBash_AlchemicalCatalogs, 'AlchemicalCatalogs', CBash_AlchemicalCatalogs.patcher_text),
    "SEWorldEnforcer": pi(SEWorldEnforcer, 'CBash_SEWorldEnforcer', SEWorldEnforcer.patcher_text),
    "CBash_SEWorldEnforcer": pi(CBash_SEWorldEnforcer, 'SEWorldEnforcer', CBash_SEWorldEnforcer.patcher_text),
}
gameSpecificListPatchers = {
    # special
    "CoblExhaustion": pi(CoblExhaustion, 'CBash_CoblExhaustion', CoblExhaustion.patcher_text),
    "CBash_CoblExhaustion": pi(CBash_CoblExhaustion, 'CoblExhaustion', CBash_CoblExhaustion.patcher_text),
    "MFactMarker": pi(MFactMarker, 'CBash_MFactMarker', MFactMarker.patcher_text),
    "CBash_MFactMarker": pi(CBash_MFactMarker, 'MFactMarker', CBash_MFactMarker.patcher_text),
}
game_specific_import_patchers = {
    # importers
    'RoadImporter': pi(RoadImporter, 'CBash_RoadImporter', RoadImporter.patcher_text),
    'CBash_RoadImporter': pi(CBash_RoadImporter, 'RoadImporter', CBash_RoadImporter.patcher_text),
}
