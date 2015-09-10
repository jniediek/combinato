# JN 2015-01-11
# refactoring

"""
given a cluster tree, define clusters and return their index
"""

from __future__ import division, print_function, absolute_import
import numpy as np
from .. import options

def find_relevant_tree_points(tree, min_spikes):
    """
    find the points where to select classes
    """
    # local options
    max_clusters_per_temp = options['MaxClustersPerTemp']

    # find peaks in relevant lines
    ret = []
    for shift in range(max_clusters_per_temp):
        col_idx = 5 + shift
        col = tree[:, col_idx]
        # bigger than predecessor
        rise = (col[1:] > col[:-1]).nonzero()[0] + 1
        # as big as successor
        fall = (col[:-1] >= col[1:]).nonzero()[0]
        peaks = set(rise) & set(fall)

        # special case for falling line at beginning
        # typical situation for high amplitude clusters
        if 1 in fall:
            peaks.add(1)

        for peak in peaks:
            nspk = tree[peak, col_idx]
            if nspk >= min_spikes:
                ret.append((peak, tree[peak, col_idx], shift + 1))

    return ret



def define_clusters(clu, tree):
    """
    extract indices of relevant clusters
    this goes over all temperatures
    imitating the "clicking and fixing" procedure in `wave_clus`
    """
    min_spikes = options['MinSpikesPerClusterMultiSelect']
    fraction_of_biggest = options['FractionOfBiggestCluster']
    mode = 'highest' # or 'fraction'

    relevant_rows = find_relevant_tree_points(tree, min_spikes)

    num_features = clu.shape[1] - 2

    idx = np.zeros(num_features, dtype=np.uint8)

    used_points = []
    current_id = 2
    max_row = 0
    for row, _, col in relevant_rows:
        row_idx = (clu[row, 2:] == col) & (idx == 0)
        if row_idx.any():
            idx[row_idx] = current_id
            current_id += 1
            p_type = 'k'
            max_row = max(max_row, row)
        else:
            p_type = 'r'

        used_points.append((row, col + 4, p_type))

    if mode == 'fraction':
        # take fraction of biggest cluster
        num_biggest = tree[0, 4]

        row = (tree[:, 4] >= fraction_of_biggest * num_biggest).nonzero()[0][-1]
        row_idx = (clu[row, 2:] == 0) & (idx == 0)
        if row_idx.any():
            idx[row_idx] = 1
            used_points.append((row, 4, 'c'))

    else:
        # take biggest cluster at highest used temperature
        if len(used_points):
            row_idx = clu[max_row, 2:] == 0
            used_points.append((max_row, 4, 'm'))
        else:
            row_idx = clu[1, 2:] == 0
            used_points.append((1, 4, 'c'))

        idx[row_idx] = 1

    return idx, tree, used_points


def testit():
    """
    simple test
    """
    from .cluster_features import testit as test_features
    clu, tree = test_features()
    idx = define_clusters(clu, tree)
    print(idx)

if __name__ == "__main__":
    testit()
