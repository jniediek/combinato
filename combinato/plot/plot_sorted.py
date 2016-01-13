#!/usr/bin/env python
# JN 2015-02-18

#   pylint: disable=E1101,star-args

"""
plot all clusters from a channel in one overview figure
"""
from __future__ import print_function, division, absolute_import

import os
import numpy as np

import matplotlib.pyplot as mpl
from matplotlib.gridspec import GridSpec

from .. import Combinato, TYPE_NAMES, h5files
from .plot_cumulative_time import spike_cumulative
from .spike_heatmap import spike_heatmap

SIGNS = ('pos', 'neg')
BOXSIZE = 1
NCOLS = 7
FONTSIZE = 8
GRID_ARGS = {'left': .005,
             'right': .995,
             'bottom': .005,
             'top': .995,
             'wspace': 0,
             'hspace': 0}


def clust_overview_plot(groups, outname):
    """
    create an overview plot constructed from groups
    """
    nrows = 0

    if not len(groups):
        return

    # calculate number of rows
    for group in groups.values():
        nrows += np.ceil((len(group['images']) + 2.1)/NCOLS)
        # print(len(group['images']), nrows)

    nrows = max(nrows, 1)
    grid = GridSpec(int(nrows), NCOLS, **GRID_ARGS)

    fig = mpl.figure(figsize=(NCOLS*BOXSIZE, nrows*BOXSIZE))

    row = 0

    for gid in sorted(groups.keys()):
        print(gid, end=' ')
        group = groups[gid]
        gtype = TYPE_NAMES[group['type']]

        col = 0
        print('row {}/{}, col {}/{}'.format(row, nrows, col, NCOLS))
        plot = fig.add_subplot(grid[row, col])
        # summary plot
        spike_heatmap(plot, group['spikes'])
        plot.set_xticks([])
        plot.set_yticks([])
        plot.axis('off')
        plot = plot.twiny()
        spike_cumulative(plot, np.sort(group['times']), special=False)
        plot.set_xticks([])
        plot.set_yticks([])

        # label it
        label = '{} {} {}'.format(gid, len(group['times']), gtype)
        print(label)
        pos = (plot.get_xlim()[0], plot.get_ylim()[0])
        plot.text(pos[0], pos[1], label, backgroundcolor='w',
                  va='bottom', fontsize=FONTSIZE)

        # plot all subclusters
        col = 1
        for img_name in group['images']:
            try:
                print(img_name)
                image = mpl.imread(img_name)
            except IOError as err:
                print(err)
                continue

            if col == NCOLS:
                col = 0
                row += 1

            print('row {}/{}, col {}/{}'.format(row, nrows, col, NCOLS))
            plot = fig.add_subplot(grid[row, col])
            plot.imshow(image)
            plot.axis('off')
            plot.set_xticks([])
            plot.set_yticks([])
            col += 1

        row += 1

    # suptitle = '{} {} ... {}'.format(fname, sessions[0], sessions[-1])
    # fig.suptitle(suptitle)
    print('saving to ' + outname)
    fig.savefig(outname)
    mpl.close(fig)


def run_file(fname, savefolder, sign, label):
    """
    run overview plot on one file
    """
    manager = Combinato(fname, sign, label)

    if manager.header is not None:
        entity = manager.header['AcqEntName']
    else:
        entity = 'unnamed'

    if not manager.initialized:
        print('could not initialize ' + fname)
        return

    # basedir = os.path.dirname(fname)
    groups = manager.get_groups_joined()
    image_dict = manager.get_groups(times=False, spikes=False)

    for gid in groups:
        groups[gid]['images'] = []
        gtype = manager.get_group_type(gid)
        groups[gid]['type'] = gtype
        for clid in image_dict[gid]:
            try:
                groups[gid]['images'].append(image_dict[gid][clid]['image'])
            except KeyError as error:
                print(error)
                continue

    wext = os.path.splitext(os.path.basename(fname))[0]
    ncs_fname = wext[5:]

    # sessions = manager.session_groups['pos']
    # groups = get_data_from_sessions(manager, sessions,
    #                                sign, ['times', 'spikes'],
    #                                skip_artifacts=False)
    if groups is None:
        return

    outname_base = 'sorted_{}_{}_{}_{}.png'.\
        format(entity, ncs_fname, sign, label)
    outname = os.path.join(savefolder, outname_base)
    clust_overview_plot(groups, outname)


def parse_args():
    """
    standard arg parser
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--files', nargs='+')
    parser.add_argument('--label', required=True)
    parser.add_argument('--neg', action='store_true', default=False)

    args = parser.parse_args()

    if os.path.isdir('overview'):
        savefolder = 'overview'
    else:
        savefolder = os.getcwd()

    if args.files:
        fnames = args.files
    else:
        fnames = h5files(os.getcwd())

    sign = 'neg' if args.neg else 'pos'
    label = args.label

    for fname in fnames:
        print(fname)
        run_file(fname, savefolder, sign, label)
