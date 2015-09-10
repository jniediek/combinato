# JN 2015-04-18
# refactoring

"""
calculate means of given clusters
"""
from __future__ import print_function, division, absolute_import
import numpy as np
from .. import CLID_UNMATCHED

def get_means(managers, all_spikes, offset):
    """
    retrieve all cluster means and unmatched spikes
    """

    ids = []
    means = []
    for ses in sorted(managers):
        ses_man = managers[ses]
        for clid in ses_man.all_ids:
            if clid != CLID_UNMATCHED:
                idx = ses_man.get_class_index_by_classes([clid])
                ids.append((ses, clid))
                means.append(all_spikes[idx - offset].mean(0))

    mean_array = np.vstack(means)
    return ids, mean_array


