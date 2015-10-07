# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

import numpy as np
from matplotlib import cm

CLUS_BINARY = '/home/johannes/combinato/spc/cluster_linux.exe'


max_amplitude = 150
min_amplitude = 100


options = {
    'TempStep': 0.01,  # try 0.005 if more clusters necessary
    'MinSpikesPerClusterMultiSelect': 15,
    'MinInputSize': 15,
    'MarkArtifactClasses': True,
    'MinInputSizeRecluster': 2000,
    'FractionOfBiggestCluster': .05,
    'MaxClustersPerTemp': 5,  # try different values
    'nFeatures': 10,
    'ClusterPath': CLUS_BINARY,
    'Wavelet': 'haar',

    'MaxDistMatchGrouping': 2.2,   # default is 1.8
    # depends on distance definition of course

    'RecursiveDepth': 1,  # default is 1, try 2 if separation needed
    'ReclusterClusters': True,
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
    'ExcludeVariableClustersMatch': True,  # default False
    'FirstMatchFactor': .75,  # try .75
    'SecondMatchFactor': 3,  # default 3
    'FirstMatchMaxDist': 4, # default 4
    'SecondMatchMaxDist': 20, 
    'OverwriteGroups': True,
    'smallmarker': 3,
    'bigmarker': 3,
    'max_amplitude': max_amplitude,
    'min_amplitude': min_amplitude,
    'compute_isi_upto_ms': 100,
    'isi_n_bins': 100,
    'isi_too_short_ms': 3,  # used to for isi plot, in single/multi unit crit
    'density_hist_bins': np.linspace(-min_amplitude,
                                     max_amplitude,
                                     max_amplitude),
    'cmap': cm.hot,
    'overview_ax_ylim': (-150, 150),
    'Debug': True,
    'histcolor': 'b',
    'histtype': 'stepfilled',
    'folder_patterns': ('CSC?', 'CSC??', 'CSC???', 'test', 'L??',
                        'R??', 'L???', 'R???', 'L????', 'R????',
                        'simulation_*')
}

artifact_criteria = {
   'maxima': 5,
   'maxima_1_2_ratio': 2,
   'max_min_ratio': 1.5,
   'sem': 4,
   'ptp': 1
}
