#!/usr/bin/env python
# JN 2015-05-05

# put out clustering data in old spikes/times format for response plots

"""
convert groups to old style spikes/times files for response plotting
"""

from __future__ import division, print_function, absolute_import
import os
import numpy as np
from scipy.io import savemat
from combinato import SortingManagerGrouped, h5files

def convert_to_mat(groups, outfname):
    """
    convert groups to mat files
    """
    tot_nspk = 0

    for group in groups.values():
        tot_nspk += group['times'].shape[0]

    nsamp = group['spikes'].shape[1]

    all_times = np.zeros(tot_nspk, np.float32)
    all_spikes = np.zeros((tot_nspk, nsamp), np.float32)
    all_classes = np.zeros(tot_nspk, np.float32) # type because later hstack

    start = 0
    next_cl = 1
    for group in groups.values():
        stop = start + group['times'].shape[0]
        all_times[start:stop] = group['times']
        all_spikes[start:stop, :] = group['spikes']
        if group['type'] != 0:
            all_classes[start:stop] = next_cl
            next_cl += 1

        start = stop

    idx = np.argsort(all_times)

    all_times = all_times[idx]
    all_spikes = all_spikes[idx, :]
    all_classes = all_classes[idx]

    cluster_class = np.vstack((all_classes, all_times)).T

    spikesdict = {'spikes': all_spikes,
                 'index_ts': all_times}

    spikes_fname = outfname + '_spikes.mat'

    savemat(spikes_fname, spikesdict)

    timesdict = { 'spikes': all_spikes,
                'cluster_class': cluster_class.astype(float)}

    times_fname = 'times_' + outfname + '.mat'
    savemat(times_fname, timesdict)


def main(fname_data, fname_sorting, sign, outfname):
    """
    read groups from sorting for conversion
    """
    man = SortingManagerGrouped(fname_data)
    man.set_sign_times_spikes(sign)
    res = man.init_sorting(fname_sorting)

    if not res:
        print(fname_data, fname_sorting)
        fn1 = os.path.basename(fname_data)
        fn2 = os.path.basename(fname_sorting)
        print('Could not initialize {} {}'.format(fn1, fn2))
    else:
        convert_to_mat(man.get_groups_joined(), outfname)


def parse_args():
    """
    standard command line parsing
    """
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--label')
    parser.add_argument('--h5file' )
    parser.add_argument('--neg', action='store_true', default=False)
    args = parser.parse_args()

    label = args.label

    sign = 'neg' if args.neg else 'pos'

    if args.h5file is None:
        rel_h5files = h5files(os.getcwd())
    else:
        rel_h5files = [args.h5file]
    

    for dfile in rel_h5files:
        basedir = os.path.dirname(dfile)
        basename = os.path.basename(dfile)
        sorting_path = os.path.join(basedir, label)
        outfname = basename[5:-3]
        main(dfile, sorting_path, sign, outfname)

if __name__ == "__main__":
    parse_args()
