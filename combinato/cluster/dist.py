# JN 2015-01-13
"""
collect all functions that have to do with distances
between clusters, groups etc
"""

# pylint: disable=E1101
from __future__ import division, print_function, absolute_import
import numpy as np
# import sys
from .. import options, CLID_UNMATCHED


def distances_euclidean(all_spikes, templates):
    """
    returns the distances for all spikes and all templates
    might be useful to do this loop in Cython
    """

    ret = np.empty((all_spikes.shape[0], templates.shape[0]))

    print('Calculating distances')

    for i, template in enumerate(templates):
        # print(i, end=' ')
        ret[:, i] = np.sqrt(((all_spikes - template)**2).sum(1))

    # print()
    # sys.stdout.flush()
    return ret


def template_match(spikes, sort_idx, match_idx, factor):
    """
    Assign spikes to templates
    This function is used as the first template match, inside each block of
    spikes, and then across blocks in a separate step
    The idea is that inside a block, a template match should be conservative
    so that matching across blocks gives good results
    """
    num_samples = spikes.shape[1]

    unmatched_idx = sort_idx == CLID_UNMATCHED

    class_ids = np.unique(sort_idx[~unmatched_idx])
    if not len(class_ids):
        return

    ids, mean_array, stds = get_means(sort_idx, spikes)

    if options['ExcludeVariableClustersMatch']:
        median_std = np.median(stds)
        std_too_high_idx = stds > 3 * median_std
        mean_array = mean_array[~std_too_high_idx]
        ids = ids[~std_too_high_idx]
        stds = stds[~std_too_high_idx]

    all_distances = distances_euclidean(spikes[unmatched_idx], mean_array)

    all_distances[all_distances > factor * stds] = np.inf
    minimizers_idx = all_distances.argmin(1)
    minimizers = ids[minimizers_idx]

    minima = all_distances.min(1)
    minimizers[minima >= options['FirstMatchMaxDist'] * num_samples] =\
        CLID_UNMATCHED

    sort_idx[unmatched_idx] = minimizers
    match_idx[unmatched_idx] = minimizers


def distance_groups(in1, in2, sign='pos'):
    """
    calculates a distance between mean spikes
    """
    dist = in1 - in2

    if sign == 'pos':
        dist /= min(in1.max(), in2.max())
    elif sign == 'neg':
        dist /= max(in1.min(), in2.min())
    else:
        raise Warning('Undefined sign: {}'.format(sign))

    l2_dist = np.sqrt((dist**2).sum())
    # return l2
    # purely heuristical metric!
    # should be optimized by someone...
    linf = np.abs(dist).max()
    return (l2_dist + 7 * linf)/2



def get_means(classes, all_spikes):
    """
    save means for all classes
    """
    # small check:
    assert classes.shape[0] == all_spikes.shape[0]

    cl_ids = np.unique(classes)
    ids = []
    means = []
    stds = []

    for clid in cl_ids:
        if clid == CLID_UNMATCHED:
            continue
        meandata = all_spikes[classes == clid]
        if meandata.shape[0]:
            ids.append(clid)
            means.append(meandata.mean(0))
            stds.append(np.sqrt(meandata.var(0).sum()))
            if options['Debug']:
                print('class {} has stdval: {:.3f}'.format(clid, stds[-1]))

    if not len(means):
        empty = np.array([])
        return empty, empty, empty

    mean_array = np.vstack(means)
    id_array = np.array(ids)
    std_array = np.array(stds)
    return id_array, mean_array, std_array
