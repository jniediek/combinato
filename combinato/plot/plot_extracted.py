# coding: utf-8

# JN 2014-12-18
"""
This script plots extracted spikes
so one can decide if clustering
is worth it or not
"""

from __future__ import division, print_function, absolute_import

import os
import numpy as np
import tables
import matplotlib.pyplot as mpl
from matplotlib.gridspec import GridSpec

from .spike_heatmap import spike_heatmap
from .plot_cumulative_time import spike_cumulative
from .. import artifact_id_to_name, get_channels, SortingManagerGrouped
from .. import h5files

SIGNS = ('pos', 'neg')
SPIKES_PER_PLOT = 5000
N_COLS = 6
FIG_WIDTH = 5.5
HEIGHT_PER_ROW = int(np.ceil(FIG_WIDTH/N_COLS))
DEBUG = True
SPIKES_PER_ROW = SPIKES_PER_PLOT*N_COLS
GRID_KEYS = {'left': 0,
             'right': 1,
             'top': 1,
             'bottom': 0,
             'hspace': 0,
             'wspace': 0}
YLIM = (-200, 200)
OVERVIEW = 'overview'
TEXT_SIZE = 'small'


def make_figure(n_rows):
    """
    returns an appropriate figure
    """
    fig_height = n_rows*HEIGHT_PER_ROW
    return mpl.figure(figsize=(FIG_WIDTH, fig_height))


def set_spines(plot):
    """
    turn off the border
    """
    for spines in plot.spines.values():
        spines.set_linewidth(.2)


def set_params(plot, x, special=False):
    """
    set parameters
    """
    plot.set_xticks(np.linspace(x[0], x[-1], 5))
    plot.set_yticks(np.linspace(YLIM[0], YLIM[1], 5))

    plot.set_ylim(YLIM)
    plot.set_xlim((x[0], x[-1]))
    plot.grid(True)
    set_spines(plot)
    plot.set_xticklabels([])
    plot.set_yticklabels([])

    if special:
        plot.text(x[2], YLIM[1], str(YLIM[1]) + u' µV',
                  va='top', size=TEXT_SIZE)


def spikes_overview(dirname, save_fname):
    """
    input: folder name
    save_fname: without .png, so that pos/neg can easily be inserted
    """
    h5fname = os.path.join(dirname, 'data_' + dirname + '.h5')
    if not os.path.exists(h5fname):
        print("{} not found".format(h5fname))
        return

    fid = tables.open_file(h5fname, 'r')

    # loop over pos and neg
    for sign in SIGNS:
        try:
            spikes = fid.get_node('/' + sign + '/spikes')[:, :]
        except tables.NoSuchNodeError as error:
            print(error)
            continue
        times = fid.get_node('/' + sign + '/times')[:]
        try:
            artifacts = fid.get_node('/' + sign + '/artifacts')[:]
            arti_types = np.unique(artifacts)
            n_all_types = len(arti_types)
        except tables.NoSuchNodeError as error:
            print(error)
            artifacts = None
            n_all_types = 1

        n_spk = spikes.shape[0]
        if n_spk == 0:
            continue

        x = np.arange(spikes.shape[1])

        if artifacts is None:
            n_plots = int(np.ceil(n_spk/SPIKES_PER_PLOT))

        else:  # if there are artifacts, iteration is a bit complex
            n_plots = 0
            for arti_type in arti_types:
                # consider each artifact as its own type
                idx = artifacts == arti_type
                n_plots += int(np.ceil(idx.sum()/SPIKES_PER_PLOT))
        if DEBUG:
            print('{} {}: {} spikes'.format(h5fname, sign, n_spk))

        n_rows = int(np.ceil(n_plots/N_COLS))
        fig = make_figure(n_rows)
        grid = GridSpec(n_rows, N_COLS, **GRID_KEYS)

        plot_count = 0
        for type_count in range(n_all_types):

            if artifacts is not None:
                current_type = arti_types[type_count]
                print(current_type)
                idx = artifacts == current_type
                current_spikes = spikes[idx, :]
                current_times = times[idx]
            else:
                current_spikes = spikes
                current_times = times
                current_type = None

            if current_spikes.shape[0] == 0:
                continue

            n_starts = int(np.ceil(current_spikes.shape[0]/SPIKES_PER_PLOT))
            for start_i in range(0, n_starts):

                plot = fig.add_subplot(grid[plot_count])
                start = start_i * SPIKES_PER_PLOT
                stop = start + SPIKES_PER_PLOT
                print(start, stop)
                spike_heatmap(plot, current_spikes[start:stop])
                set_params(plot, x, start == 0)
                if current_type in artifact_id_to_name:
                    plot.text(x[2], YLIM[0]*.75,
                              artifact_id_to_name[current_type],
                              va='bottom', ha='left', size=TEXT_SIZE)
                plot2 = plot.twiny()
                spike_cumulative(plot2, current_times[start:stop], start == 0)
                plot2.set_ylim(YLIM)
                set_spines(plot2)
                plot_count += 1

        fig.savefig(save_fname + '_' + sign + '.png')
        mpl.close(fig)

    fid.close()


def process_folder(path):
    """
    run spikes_overview on a folder that has ncs files
    """
    chans = get_channels(path)
    for chan in sorted(chans):
        ncs_fname = os.path.splitext(chans[chan])[0]
        plot_fname = 'spikes_{}_{}'.format(chan, ncs_fname)
        save_fname = os.path.join(OVERVIEW, plot_fname)
        spikes_overview(ncs_fname, save_fname)


def process_file(fname):
    """
    run overview on datafiles
    """
    # get the channel name
    # this is dirty code, come up with a better solution
    # e.g. storing the header info in the h5 file attrs
    man = SortingManagerGrouped(fname)
    try:
        entity = man.header['AcqEntName']
    except TypeError:
        entity = 'unknown'
    ncs_fname = os.path.basename(fname)[5:-3]
    print(ncs_fname)
    plot_fname = 'spikes_{}_{}'.format(entity, ncs_fname)
    save_fname = os.path.join(OVERVIEW, plot_fname)
    spikes_overview(ncs_fname, save_fname)


def parse_args():
    """
    standard arg parsing function
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--datafiles', nargs='+')

    args = parser.parse_args()

    if not os.path.exists(OVERVIEW):
        os.mkdir(OVERVIEW)

    # process_folder(os.getcwd())
    # JN 2015-10-31
    # process_folder assumes that ncs files are still in place
    # let's reform this today

    if args.datafiles is not None:
        files = args.datafiles
    else:
        files = h5files(os.getcwd())

    for fname in files:
        process_file(fname)
