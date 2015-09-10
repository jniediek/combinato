# JN 2015-09-10
"""
Imports that can than be used by the packages in this folder
"""

from __future__ import absolute_import
from .options import options, artifact_criteria
from .constants import SPIKE_CLUST, SPIKE_MATCHED, SPIKE_MATCHED_2, CLID_UNMATCHED,\
    SIGNS, TYPE_NAMES, TYPE_ART

from .basics.nlxio import NcsFile
from .basics.filters import DefaultFilter
from .util.tools import h5files, get_channels, get_regions
from .artifacts.mask_artifacts import id_to_name as artifact_id_to_name
from .manager.manager import SortingManager, SessionManager, DataManager
from .manager.manager_cat import SortingManagerGrouped
from .manager.create_session import create_session
