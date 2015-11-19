#!/usr/bin/env python
# JN 2015-05-05

# put out clustering data in old spikes/times format for response plots

"""
convert groups to old style spikes/times files for response plotting
"""

from __future__ import division, print_function, absolute_import
import os
import csv
# pylint: disable=E1101
import numpy as np
import time
from scipy.io import savemat
from combinato import Combinato, h5files, TYPE_ART, TYPE_NO, GROUP_ART, GROUP_NOCLASS 


def convert_to_mat(groups, outfname, drop_artifacts=False):
    """
    convert groups to mat files
    """
    tot_nspk = 0

    for group in groups.values():
        tot_nspk += group['times'].shape[0]

    nsamp = group['spikes'].shape[1]

    all_times = np.zeros(tot_nspk, np.float64)
    all_spikes = np.zeros((tot_nspk, nsamp), np.float32)
    all_classes = np.zeros(tot_nspk, np.float64) # type because later hstack

    start = 0
    
    # info is for the csv info file
    info = {GROUP_NOCLASS: 0, GROUP_ART: 0}

    # excluding here means not assigning  a cluster number
    exclude_groups = [GROUP_NOCLASS]
    if drop_artifacts:
        exclude_groups.append(GROUP_ART)

    next_cl = 1
    for group in groups.values():
        stop = start + group['times'].shape[0]
        all_times[start:stop] = group['times']
        all_spikes[start:stop, :] = group['spikes']
        g_type = group['type']
        # this means we have unassigned spikes
        if g_type == TYPE_NO:
            info[GROUP_NOCLASS] = 1
        # this means we have artifacts
        elif g_type == TYPE_ART:
            if GROUP_ART in exclude_groups:
                info[GROUP_ART] = 2
            else:
                info[GROUP_ART] = 1
        if g_type not in exclude_groups:
            all_classes[start:stop] = next_cl
            info[next_cl] = g_type
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

    timesdict = {'spikes': all_spikes,
                 'cluster_class': cluster_class}

    times_fname = 'times_' + outfname + '.mat'
    savemat(times_fname, timesdict)

    return info


def main(fname_data, fname_sorting, sign, outfname, drop_artifacts=False):
    """
    read groups from sorting for conversion
    """
    man = Combinato(fname_data, sign, fname_sorting)
    # man.set_sign_times_spikes(sign)
    # res = man.init_sorting(fname_sorting)
    fn1 = os.path.basename(fname_data)
    # fn2 = os.path.basename(fname_sorting)

    joined = man.get_groups_joined()
    ch_name = man.header['AcqEntName']
    # ugly: this works only if you use the CSCxy convention!
    go_on = False
    try:
        ch_num = int(fn1[8:-3])
        go_on = True
    except ValueError as error:
        print(error)
        print('Cannot find channel number in'
             ' filename {}'.format(fn1))
        info_row = None
    if go_on:
        info_row = [ch_num, ch_name]
        info_dict = convert_to_mat(joined, outfname, drop_artifacts)
        info_row += [info_dict[GROUP_ART], info_dict[GROUP_NOCLASS]]
        del info_dict[GROUP_ART]
        del info_dict[GROUP_NOCLASS]
        for key in sorted(info_dict.keys()):
            info_row.append(info_dict[key])
    del man
    return info_row


def parse_args():
    """
    standard command line parsing
    """
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--h5file' )
    parser.add_argument('--neg', action='store_true', default=False)
    parser.add_argument('--no-info', action='store_true', default=False)
    parser.add_argument('--drop-artifacts', action='store_true',
                        default=False)

    args = parser.parse_args()
    label = args.label
    sign = 'neg' if args.neg else 'pos'
    do_info = not args.no_info
    drop_artifacts = args.drop_artifacts

    if args.h5file is None:
        rel_h5files = h5files(os.getcwd())
    else:
        rel_h5files = [args.h5file]

    # for cluster_info.mat:
    all_info = [[None]*len(rel_h5files), [None]*len(rel_h5files)]

    if do_info:
        session_name = os.path.dirname(rel_h5files[0])
        date = time.strftime('%Y-%m-%d_%H:%M:%S')
        csvfile = open('cluster_info.csv', 'w')
        writer = csv.writer(csvfile)
        writer.writerow(['# Session:  {}, Converted: {}'.
            format(session_name, date)])
        writer.writerow(['# For Artifacts, 0 means there are none, 1 means '
                         'they are included as clusters (type -1), 2 means '
                         'they are included as unassigned (type 0)'])
        writer.writerow(['# For Unassigned, 1 means they exist, 0 means they '
                         'do not exist.'])
        writer.writerow(['# For Clusters, 1 means multi-unit, 2 means '
                         'single-unit, -1 means artifact'])
        writer.writerow(['ChannelNumber', 'ChannelName', 'Artifacts',
                         'Unassigned', 'Cluster1', 'Cluster2', '...'])

    for dfile in rel_h5files:
        basedir = os.path.dirname(dfile)
        basename = os.path.basename(dfile)
        sorting_path = os.path.join(basedir, label)
        outfname = basename[5:-3]
        info = main(dfile, sorting_path, sign, outfname, drop_artifacts)
        if do_info and (info is not None):
            writer.writerow(info)
            all_info[0][rel_h5files.index(dfile)] = info[4:]
            all_info[1][rel_h5files.index(dfile)] = info[1]

    if do_info:
        info_dict = {'cluster_info': all_info, 'label_info':
                     ' 1 = MU\n 2 = SU\n-1 = Artif.\nRefers to '
                     '"cluster_class"-values 1 and up.\nIgnores Unassigned '
                     '(value 0)'}
        info_fname = "cluster_info"
        savemat(info_fname, info_dict)

if __name__ == "__main__":
    parse_args()
