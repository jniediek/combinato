#!/usr/bin/env python
# -*- coding: utf-8 -*-
# JN 2015-01-04
"""
script creates an artifact column in data_ h5 files
different functions can be called to mark artifacts
"""


from __future__ import print_function, division, absolute_import
import os
from argparse import ArgumentParser

import numpy as np
import tables

from .. import h5files

SIGNS = ('pos', 'neg')
DEBUG = True
RESET = True  # set artifacts to 0 before analysis
READONLY = False
MODE = 'first'  # MODE can be 'first', 'last', or 'OR'


options_by_diff = {'art_id': 1,   # to identify this type of artifact
                   'name': 'high_firing',
                   'binlength': 500,  # msec
                   'max_spk_per_bin': 100}  # means 200 Hz maximum

options_by_height = {'art_id': 2,
                     'name': 'amplitude',
                     'max_height': 1000}  # µV

options_by_bincount = {'art_id': 4,
                       'name': 'bincount',
                       'max_frac_ch': .5}

options_double = {'art_id': 8,
                  'name': 'double',
                  'relevant_idx': 18,  # look here for decision, very specific!
                  'min_dist': 1.5}  # means 1.5 ms minimum distance

options_ranges = {'art_id': 16,
                  'name': 'range'}

artifact_types = (options_by_diff, options_by_height,
                  options_by_bincount, options_double, options_ranges)

id_to_name = {}

for options in artifact_types:
    id_to_name[options['art_id']] = options['name']


def add_id(artifacts, index, art_id, sign):
    """
    use either logical OR or reset to mask artifacts
    """
    if DEBUG:
        detected = index.sum()
        if MODE == 'first':
            masked = ((index != 0) & (artifacts[:] == 0)).sum()
        else:
            masked = detected
        print('{}: detected {} {} spikes, masked {} in mode "{}"'.
              format(id_to_name[art_id], detected, sign, masked, MODE))

    if READONLY:
        return

    if MODE == 'last':
        # only the last one counts
        artifacts[index] = art_id
    elif MODE == 'OR':
        # do a logical OR
        artifacts[index] |= art_id
    elif MODE == 'first':
        # only the first one counts
        artifacts[index & (artifacts[:] == 0)] = art_id
    else:
        raise ValueError('Unknown artifact storage mode: {}'.format(MODE))

    print('Total: ', (artifacts[:] != 0).sum())


def mark_range_detection(times, ranges):
    """
    Ranges contains a list of 2-tuples. All timestamps within
    such a 2-tuple are excluded.
    """
    artifacts = np.zeros(times.shape[0], dtype=bool)
    for this_range in ranges:
        idx = (times >= this_range[0]) & (times <= this_range[1])
        print(this_range, times[0], times[-1])
        print(idx.sum())
        artifacts[idx] |= True

    return artifacts, options_ranges['art_id']


def mark_double_detection(times, spikes, sign):
    """
    for spikes that are too close together,
    keep only the one with the bigger amplitude
    """

    def mycmp(a, b, sign):
        if sign == 'pos':
            return a > b
        elif sign == 'neg':
            return a < b

    artifacts = np.zeros(times.shape[0], dtype=bool)
    min_dist = options_double['min_dist']
    rel_idx = options_double['relevant_idx']
    diff = np.diff(times)
    double_idx = diff < min_dist

    for i in double_idx.nonzero()[0]:
        sp1 = spikes[i, rel_idx]
        sp2 = spikes[i + 1, rel_idx]
        if mycmp(sp1, sp2, sign):
            kill = i + 1
        else:
            kill = i
        artifacts[kill] = True

    print('{} dist < {}'.format((double_idx).sum(), min_dist))
    return artifacts, options_double['art_id']


def mark_by_diff(times):
    """
    marks bins with too many events
    """
    bin_len = options_by_diff['binlength']
    max_per_bin = options_by_diff['max_spk_per_bin']

    artifacts = np.zeros(times.shape[0], dtype=bool)

    for shift in (0, bin_len/2):
        bins = np.arange(times[0] + shift, times[-1] + shift, bin_len)
        if len(bins) < 2:
            continue
        counts, _ = np.histogram(times, bins)
        left_edges_too_many = bins[:-1][counts > max_per_bin]
        # try a loop, but maybe too slow?
        if DEBUG:
            print('looping over {} edges'.format(left_edges_too_many.shape[0]))
        for edge in left_edges_too_many:
            idx = (times >= edge) & (times <= edge + bin_len)
            artifacts[idx] = True

    return artifacts, options_by_diff['art_id']


def bincount_to_edges(concurrent_fname):
    """
    helper, transforms bincount to edges
    """
    conc_fid = tables.open_file(concurrent_fname, 'r')
    count = conc_fid.root.count[:]
    attrs = conc_fid.root.count.attrs
    num_channels = attrs['nch']
    start = attrs['start']
    stop = attrs['stop']
    bin_len = attrs['binms']
    conc_fid.close()
    bins = np.arange(start, stop, bin_len)
    cutoff = options_by_bincount['max_frac_ch'] * num_channels
    if DEBUG:
        print('Using cutoff of {:.0f} channels'.format(cutoff))
    exclusion_left_edges = bins[:-1][count > cutoff]
    return exclusion_left_edges, bin_len


def mark_by_bincount(times, left_edges, bin_len):
    """
    marks bins with events in too many other channels (specified by counts)
    """
    if DEBUG:
        print('all channel rejection, looping over {} edges'.
              format(left_edges.shape[0]))

    artifacts = np.zeros(times.shape[0], dtype=bool)

    for edge in left_edges:
        idx = (times >= edge) & (times <= edge + bin_len)
        artifacts[idx] = True

    return artifacts, options_by_bincount['art_id']


def mark_by_height(spikes, sign):
    """
    marks spikes that exceed a height criterion
    """
    max_height = options_by_height['max_height']

    if sign == 'pos':
        artifacts = spikes.max(1) >= max_height
    elif sign == 'neg':
        artifacts = spikes.min(1) <= -max_height
    else:
        raise ValueError('Unknown sign: ' + sign)

    return artifacts, options_by_height['art_id']


def main(fname, concurrent_edges=None, concurrent_bin=None,
         exlude_ranges=None):
    """
    creates table to store artifact information
    """
    for sign in SIGNS:

        # why is this here?
        if READONLY:
            mode = 'r'
        else:
            mode = 'r+'
        h5fid = tables.open_file(fname, mode)

        try:
            node = h5fid.get_node('/' + sign + '/times')
        except tables.NoSuchNodeError:
            print('{} has no {} spikes'.format(fname, sign))
            continue

        if len(node.shape) == 0:
            continue

        elif node.shape[0] == 0:
            continue

        times = node[:]
        num_spk = times.shape[0]

        spikes = h5fid.get_node('/' + sign, 'spikes')[:, :]

        assert num_spk == spikes.shape[0]

        try:
            artifacts = h5fid.get_node('/' + sign + '/artifacts')
        except tables.NoSuchNodeError:
            h5fid.create_array('/' + sign, 'artifacts',
                               atom=tables.Int8Atom(), shape=(num_spk, ))
            artifacts = h5fid.get_node('/' + sign + '/artifacts')
        if RESET:
            artifacts[:] = 0

        arti_by_diff, arti_by_diff_id = mark_by_diff(times)
        add_id(artifacts, arti_by_diff, arti_by_diff_id, sign)
        # artifacts[arti_by_diff != 0] = arti_by_diff_id

        # if DEBUG:
        #    print('Marked {} {} spikes by diff'.
        #          format(arti_by_diff.sum(), sign))

        arti_by_height, arti_by_height_id = mark_by_height(spikes, sign)
        add_id(artifacts, arti_by_height, arti_by_height_id, sign)

        # artifacts[arti_by_height != 0] = arti_by_height_id
        # if DEBUG:
        #    print('Marked {} {} spikes by height'.
        #          format(arti_by_height.sum(), sign))

        arti_by_double, double_id = mark_double_detection(times, spikes, sign)
        add_id(artifacts, arti_by_double, double_id, sign)
        # artifacts[arti_by_double != 0] = double_id
        # if DEBUG:
        #    print('Marked {} {} spikes as detected twice'.
        #          format(arti_by_double.sum(), sign))

        if concurrent_edges is not None:
            arti_by_conc, arti_by_conc_id = mark_by_bincount(times,
                                                             concurrent_edges,
                                                             concurrent_bin)
            add_id(artifacts, arti_by_conc, arti_by_conc_id, sign)

            # artifacts[arti_by_conc != 0] = arti_by_conc_id
            # if DEBUG:
            #    print('Marked {} {} spikes by concurrent occurence'.
            #          format(arti_by_conc.sum(), sign))

        if exlude_ranges is not None:
            arti_by_ranges, range_id = mark_range_detection(times,
                                                            exlude_ranges)
            add_id(artifacts, arti_by_ranges, range_id, sign)
            # artifacts[arti_by_ranges != 0] = range_id

            # if DEBUG:
            #    print('Marked {} {} spikes within supplied range '.
            #          format(arti_by_ranges.sum(), sign))

        h5fid.close()


def parse_args():
    CONC_FNAME = 'concurrent_times.h5'
    parser = ArgumentParser()
    parser.add_argument('--file', '--datafile', nargs=1)
    parser.add_argument('--concurrent-file', nargs=1)
    parser.add_argument('--exclude-ranges', nargs=1,
                        help='supply a file with timestamp ranges to exclude')
    args = parser.parse_args()

    if args.concurrent_file:
        conc_fname = args.concurrent_file[0]
    else:
        conc_fname = CONC_FNAME

    if os.path.isfile(conc_fname):
        concurrent_edges, concurrent_bin =\
            bincount_to_edges(conc_fname)
    else:
        print('Not using concurrent spike detection')
        concurrent_edges = concurrent_bin = None

    if args.file:
        fname = args.file[0]
    else:
        fname = os.getcwd()

    if os.path.isdir(fname):
        files = h5files(fname)
    else:
        files = [fname]

    if args.exclude_ranges:
        fname = args.exclude_ranges[0]
        exclude_ranges = []
        with open(fname, 'r') as fid:
            for line in fid.readlines():
                ranges = [float(x) for x in line.strip().split()]
                exclude_ranges.append(ranges)
    else:
        exclude_ranges = None

    # main loop, could be done with parallel
    # processing (bad because of high I/O)
    for fname in files:
        if DEBUG:
            print('Starting ' + fname)
        main(fname, concurrent_edges, concurrent_bin, exclude_ranges)

if __name__ == "__main__":
    parse_args()
