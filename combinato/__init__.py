# JN 2015-09-10
"""
Imports that can than be used by the packages in this folder
"""

from __future__ import absolute_import, print_function
from .options import options, artifact_criteria

try:
    from .options import raster_options
except ImportError:
    pass

try:
    from local_options import options as local_options
    options.update(local_options)
    print('Updated {} options by local_options'.format(len(local_options)))
except ImportError:
    pass

try:
    from local_options import artifact_criteria as loc_artifact_criteria
    artifact_criteria.update(loc_artifact_criteria)
    print('Updated {} artifact criteria from local_options')
except ImportError:
    pass

from .constants import SPIKE_CLUST, SPIKE_MATCHED, SPIKE_MATCHED_2,\
    CLID_UNMATCHED, SIGNS, TYPE_NAMES, TYPE_ART, TYPE_MU, TYPE_SU,\
    TYPE_NO, GROUP_ART, GROUP_NOCLASS, TYPE_NON_NOISE, TYPE_ALL

from .basics.nlxio import NcsFile, ncs_info, nev_read
from .basics.filters import DefaultFilter
from .util.tools import h5files, get_channels, get_regions, check_status
from .util.get_folder_structure import get_relevant_folders, get_time_files
from .artifacts.mask_artifacts import id_to_name as artifact_id_to_name,\
    artifact_types
from .manager.manager import SortingManager, SessionManager, DataManager
from .manager.manager_cat import SortingManagerGrouped, SortingFile, Combinato
from .manager.create_session import create_session
