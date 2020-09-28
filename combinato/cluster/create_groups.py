# JN 2015-04-20 refactor
# JN 2016-09-06 introduce faster create_groups

"""
read a total sorting file and group the classes
"""
from __future__ import absolute_import, print_function, division

import tables
import numpy as np
from .. import SortingManager, options, CLID_UNMATCHED, GROUP_ART, GROUP_NOCLASS,\
    TYPE_ART, TYPE_NO, TYPE_MU
from .dist import distance_groups


def create_groups(spikes, classes, clids, sign):
    """
    more efficient group merging
    """
    crit = options['MaxDistMatchGrouping']
    groups = {}
    n_groups_in = len(clids) + 1
    means = np.empty((n_groups_in, spikes.shape[1]))
    nspks = np.empty(n_groups_in, int)
    dists = np.zeros((n_groups_in, n_groups_in))
    # initialize to inf
    dists[:, :] = np.inf
    count = 1
    
    for clid in clids:
        if clid == CLID_UNMATCHED:
            continue
        count += 1
        groups[count] = [clid]
        idx = classes == clid
        nspks[count] = idx.sum()
        means[count, :] = spikes[idx].mean(0)

    # do an initial upper triangular matrix of dists

    for i in range(n_groups_in):
        if i not in groups:
            continue
        for j in range(i + 1, n_groups_in):
            if j not in groups:
                continue
            dists[i, j] = distance_groups(means[i, :], means[j, :], sign) 

    # iteratively merge groups and update dists
    minimum = -1
    while True:
        this_argmin = dists.argmin()
        gr1, gr2 = np.unravel_index(this_argmin, (n_groups_in, n_groups_in))
        minimum = dists[gr1, gr2]
        if minimum > crit:
            break
        print('Merging {} and {}, dist: {:.4f}'.format(gr1, gr2, minimum))
        # merge groups 1 and 2 now
        groups[gr1] += groups[gr2]
        del groups[gr2] 
        # update nspks
        nspk1 = nspks[gr1]
        nspk2 = nspks[gr2]
        nspks[gr1] = nspk1 + nspk2
        # update means
        means[gr1, :] = (means[gr1, :] * nspk1 + means[gr2, :] * nspk2) / (nspk1 + nspk2)
        # update dists: everything containing gr2 is inf now
        # everything containing gr1 has to be redone
        dists[gr2, :] = np.inf
        dists[:, gr2] = np.inf
        for i in groups.keys():
            if i < gr1:
                dists[i, gr1] = distance_groups(means[i], means[gr1], sign)
            elif i > gr2:
                dists[gr1, i] = distance_groups(means[i], means[gr1], sign)
    return groups 


def main(datafname, sorting_fname, read_only=False):
    """
    main function
    """
    if read_only:
        mode = 'r'
    else:
        mode = 'r+'

    man = SortingManager(datafname)
    sort_fid = tables.open_file(sorting_fname, mode)
    sign = sort_fid.get_node_attr('/', 'sign')

    idx = sort_fid.root.index[:]
    spikes = man.get_data_by_name_and_index('spikes', idx, sign)
    del man
    print('Read {} spikes'.format(spikes.shape[0]))
    classes = sort_fid.root.classes[:]
    artifacts = sort_fid.root.artifacts[:, :]
    group_arr = artifacts.copy().astype(np.int16)
    # mark artifacts
    art_idx = (artifacts[:, 1]) != 0 & (artifacts[:, 0] != 0)
    clids = artifacts[~art_idx, 0]

    group_arr[art_idx, 1] = GROUP_ART
    print('Classes: {}'.format(clids))

    groups = create_groups(spikes, classes, clids, sign)
    
    for grid, orig_grid in enumerate(sorted(groups.keys())):
        clids = groups[orig_grid]
        for clid in clids:
            idx = group_arr[:, 0] == clid
            group_arr[idx, 1] = grid + 1  # start with 1

    # account for special group
    idx = group_arr[:, 0] == 0
    group_arr[idx, 1] = GROUP_NOCLASS

    if not read_only:

        try:
            sort_fid.remove_node('/', 'groups')
            print('Updating grouping')
        except tables.NoSuchNodeError:
            print('Creating grouping')

        sort_fid.create_array('/', 'groups', group_arr)

        try:
            sort_fid.remove_node('/', 'groups_orig')
            print('Updating original grouping')
        except tables.NoSuchNodeError:
            print('Creating original grouping')

        sort_fid.create_array('/', 'groups_orig', group_arr)

    # assign types
    group_names = np.unique(group_arr[:, 1])
    types = np.zeros((group_names.shape[0], 2), np.int16)
    types[:, 0] = group_names
    types[:, 1] = TYPE_MU

    # special types
    types[types[:, 0] == GROUP_ART, 1] = TYPE_ART
    types[types[:, 0] == GROUP_NOCLASS, 1] = TYPE_NO

    if not read_only:
        try:
            sort_fid.remove_node('/', 'types')
            print('Updating types')
        except tables.NoSuchNodeError:
            print('Creating types')

        sort_fid.create_array('/', 'types', types)

        # create backups of types
        try:
            sort_fid.remove_node('/', 'types_orig')
            print('Updating original types')
        except tables.NoSuchNodeError:
            print('Storing original types')

        sort_fid.create_array('/', 'types_orig', types)

        sort_fid.flush()

    sort_fid.close()
