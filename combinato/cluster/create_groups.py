# JN 2015-04-20
# refactoring

"""
read a total sorting file and group the classes
"""
from __future__ import absolute_import, print_function, division
import tables
import os
import numpy as np
from .. import SortingManager, options, CLID_UNMATCHED, GROUP_ART, GROUP_NOCLASS,\
    TYPE_ART, TYPE_NO, TYPE_MU
from .dist import find_nearest


def make_means(spikes, classes, clids):
    """
    calculate means
    """
    groups = {}
    means = {}
    nspks = {}
    count = 1

    for clid in clids:
        if clid == CLID_UNMATCHED:
            continue
        count += 1
        groups[count] = [clid]
        idx = classes == clid
        nspks[count] = idx.sum()
        # print('Adding cl {}'.format(clid))
        means[count] = spikes[idx].mean(0)

    return groups, means, nspks


def create_groups(groups, means, nspks):
    """
    join closest groups iteratively
    """
    minimum = 0
    crit = options['MaxDistMatchGrouping']

    while True:
        key1, key2, minimum = find_nearest(means)
        if minimum > crit:
            break
        if None in (key1, key2):
            continue

        groups[key1] += groups[key2]
        print('Joining {} and {} (d={:.3f})'.format(key1, key2, minimum))
        mean1 = means[key1]
        mean2 = means[key2]
        nspk1 = nspks[key1]
        nspk2 = nspks[key2]

        new_mean = (mean1 * nspk1 + mean2 * nspk2)/(nspk1 + nspk2)

        means[key1] = new_mean
        nspks[key1] = nspk1 + nspk2

        del groups[key2]
        del means[key2]
        del nspks[key2]

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
    clids = artifacts[-art_idx, 0]

    group_arr[art_idx, 1] = GROUP_ART
    print('Classes: {}'.format(clids))

    groups, means, nspks = make_means(spikes, classes, clids)
    groups = create_groups(groups, means, nspks)

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
        sort_fid.create_array('/', 'types_orig', types)

        sort_fid.flush()

    sort_fid.close()


if __name__ == "__main__":
    """
    a small test case
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--read-only', default=False, action='store_true')
    parser.add_argument('--datafile', nargs=1, required=True)
    parser.add_argument('--sorting', nargs=1, required=True)

    args = parser.parse_args()

    datafile = args.datafile[0]
    sortingfile = os.path.join(args.sorting[0], 'sort_cat.h5')

    main(datafile, sortingfile, args.read_only)
