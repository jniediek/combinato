# -*- coding: utf-8 -*-

"""
These are the default options for Combinato.

Use setup_options.py to automatically insert the path to the
clustering binary.
"""

# pylint: disable=no-member, invalid-name

from __future__ import division, print_function, absolute_import

import numpy as np
from matplotlib import cm

# set CLUS_BINARY here
CLUS_BINARY = ''

MAX_AMPLITUDE = 150
MIN_AMPLITUDE = 100

options = {
    # How many clusters can be selected at one temperature?
    'MaxClustersPerTemp': 5,  # default 5
    # How many spikes does a cluster need to be selected?
    'MinSpikesPerClusterMultiSelect': 15,  # default 15

    # How many clustering recursions should be run?
    'RecursiveDepth': 1,  # default is 1 (do not recurse)

    # Iteratively recluster big clusters?
    'ReclusterClusters': True,
    # How many spikes does a cluster need to be re-clustered?
    'MinInputSizeRecluster': 2000,  # default 2000

    # How close do spikes have to be in the first template matching step?
    'FirstMatchFactor': .75,  # default .75

    # In the second template matching step?
    'SecondMatchFactor': 3,   # default 3

    # At what cluster distance does grouping stop?
    'MaxDistMatchGrouping': 1.8,   # default 1.8

    # Folder names the GUI should include
    'folder_patterns': ('CSC*', 'test', 'L??',
                        'R??', 'L???', 'R???', 'L????', 'R????',
                        'simulation_*'),

    # Use this option to create raster plots in css-gui
    # This requires 'raster_options', see Documentation
    'RunGuiWithRaster': False,

    # Use this option to make css-gui read time stamps from
    # extraction thresholds instead of spike times (for display only)
    'GuiUseThresholdTimeAxis': False,
    'MinInputSize': 15,
    'TempStep': 0.01,
    'MarkArtifactClasses': True,
    'FractionOfBiggestCluster': .05,
    'nFeatures': 10,
    'Wavelet': 'haar',

    'ClusterPath': CLUS_BINARY,

    'ShowSPCOutput': False,
    'RecheckArtifacts': True,  # check after total match
    'plot': True,
    'plotTemps': True,
    'figsize': (2, 2),
    'dpi': 100,  # so figure is 200x200 pixels
    'ylim': (-200, 200),
    'linewidth': .4,
    'tempfigsize': (5, 5),
    'ArtifactOverview': False,
    'feature_factor': 3,
    'overwrite': True,
    'ExcludeVariableClustersMatch': True,
    'FirstMatchMaxDist': 4,   # default 4
    'SecondMatchMaxDist': 20,
    'OverwriteGroups': True,
    'smallmarker': 3,
    'bigmarker': 3,
    'max_amplitude': MAX_AMPLITUDE,
    'min_amplitude': MIN_AMPLITUDE,
    'compute_isi_upto_ms': 100,
    'isi_n_bins': 100,
    'isi_too_short_ms': 3,  # used to for isi plot, in single/multi unit crit
    'density_hist_bins': np.linspace(-MIN_AMPLITUDE,
                                     MAX_AMPLITUDE,
                                     MAX_AMPLITUDE),
    'cmap': cm.hot,
    'overview_ax_ylim': (-150, 150),
    'Debug': False,
    'histcolor': 'b',
    'histtype': 'stepfilled',
    'guistyle': 'oxygen',
    'UseCython': False
}


artifact_criteria = {
    'maxima': 5,
    'maxima_1_2_ratio': 2,
    'max_min_ratio': 1.5,
    'sem': 4,
    'ptp': 1
}
