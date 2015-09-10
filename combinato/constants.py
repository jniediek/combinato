"""
This software is intended for spike extraction, spike sorting,
artifact detection, and some spike data analysis purposes
Johannes Niediek (jonied@posteo.de)
"""

from __future__ import absolute_import, division, print_function

import sys
import os
import subprocess

DO_CHECKS = True

if DO_CHECKS:
    if 'linux' in sys.platform:
        if 'DISPLAY' not in os.environ:
            print('You are using linux without graphical environment. '
                  'Plotting will not work. Try ssh -X.')
        try:
            subprocess.call('montage', stdout=subprocess.PIPE)
        except OSError as error:
            print(error)
            print("'montage' from ImageMagick not found. "
                  "Plotting continuous data will not work")


TYPE_ART = -1
TYPE_NO = 0
TYPE_MU = 1
TYPE_SU = 2
CLID_UNMATCHED = 0


TYPE_NAMES = {TYPE_ART: 'Artifact',
              TYPE_NO: 'Not assigned',
              TYPE_MU: 'Multi-Unit',
              TYPE_SU: 'Single-Unit'}

GROUP_ART = -1
GROUP_NOCLASS = 0

SPIKE_MATCHED = 1
SPIKE_CLUST = 0
SPIKE_MATCHED_2 = 2 # for overall matching

SIGNS = ('pos', 'neg')
