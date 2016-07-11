# JN 2015-07-05
# -*- encoding: utf-8 -*-

"""
create a unit overview plots for all units
"""
from __future__ import division, print_function, absolute_import
import os

import numpy as np

import matplotlib.pyplot as mpl
from matplotlib.gridspec import GridSpec
from matplotlib import cm

from .spike_heatmap import spike_heatmap
from .. import h5files, Combinato, TYPE_NAMES

LOCAL_TYPE_NAMES = {0: 'NA', 1: 'MU', 2: 'SU', -1: 'Arti'}


FIGSIZE = (13, 7.5)
GRID = GridSpec(2, 6, left=.08, right=.95,
                top=.9, bottom=.05, wspace=.7, hspace=.25)
DENSITY_BINS = np.linspace(-150, 150, 150)
DPI = 100


FIG = mpl.figure(figsize=FIGSIZE, dpi=DPI)


def create_panels(fig):
    panels = dict()
    panels['maxima'] = fig.add_subplot(GRID[0, :4])
    panels['isi'] = fig.add_subplot(GRID[1, 4:])
    panels['cumulative'] = fig.add_subplot(GRID[1, :4])
    panels['density'] = fig.add_subplot(GRID[0, 4], xticks=[])
    panels['density2'] = fig.add_subplot(GRID[0, 5])
    panels['density2'].axis('off')
    panels['images'] = []
#    for i in range(12):
#        row = int(i/6) + 2
#        col = i % 6
#        plot = fig.add_subplot(GRID[row, col])
#        plot.axis('off')
#        panels['images'].append(plot)
#
    return panels

PANELS = create_panels(FIG)


def add_events(plot, events):
    """
    """
    for event in events:
        if isinstance(event[1], int) or event[1] in ('OFF', '1.5', 'ON'):
            va = 'top'
            color = 'k'
            ypos = 0
            xpos = event[0]
            backgroundcolor = 'none'
        else:
            va = 'bottom'
            color = 'g'
            ypos = 0
            xpos = event[0] + 20  # datetime.timedelta(seconds=20)
            backgroundcolor = 'w'

        plot.axvline(event[0]/60, color=color)
        plot.text(xpos/60, ypos, event[1], va=va, color=color,
                  backgroundcolor=backgroundcolor)


def make_colors(ncolors):
    """
    create a list of N matplotlib colors
    """
    return cm.spectral(np.linspace(0, 1, ncolors))


def plot_maxima_over_time(plot, group, start_stop, sign, thresholds=None):
    """
    plots maxima over time, with different colors for different clusters
    """
    plot.cla()
    COLOR_CUTOFF = 10
    with_colors = list()
    same_color = list()

    end_min = (start_stop[1] - start_stop[0])/1000/60

    for clid in group:
        if group[clid]['times'].shape[0] > COLOR_CUTOFF:
            with_colors.append(clid)
        else:
            same_color.append(clid)

    colors = make_colors(len(with_colors))
    out_color = 'grey'

    color_count = 0

    for clid, cluster in group.items():
        spikes = cluster['spikes']
        times = cluster['times'] - start_stop[0]

        if sign == 'neg':
            data = spikes.min(1)
        elif sign == 'pos':
            data = spikes.max(1)

        color = out_color

        if clid in with_colors:
            color = colors[color_count]
            color_count += 1

        plot.plot(times/1000/60, data, '.', ms=2, color=color)

    # now plot the thresholds
    thr_times = thresholds[:, :2].ravel()
    thrs = np.vstack((thresholds[:, 2], thresholds[:, 2])).T.ravel()
    thr_times -= start_stop[0]
    thr_times /= 60*1000
    plot.plot(thr_times, thrs)

    tickpos = np.arange(0, end_min, 60)
    ticklabels = [format(x, '.0f') for x in tickpos]
    ticklabels[-1] += ' min'
    plot.set_xticks(tickpos)
    plot.set_xticklabels(ticklabels)
    plot.set_xlim((0, end_min))
    # plot.xaxis.set_tick_params(labeltop='on', labelbottom='off')
    # plot.set_ylim(ylim)
    plot.set_ylabel(u'µV')
    plot.grid(True)


def plot_group(gid, group, group_joined, start_stop, sign,
               savefolder, thresholds):
    """
    just a simple group overview
    """

    print('Plotting group {} ({} clusters)'.format(gid, len(group)))

    panels = PANELS

    # timelim = (start_time/60, stop_time/60)

#    if sign == 'neg':
#        ylim = (-200, 0)
#    elif sign == 'pos':
#        ylim = (0, 200)
#
    # maxima over time
    plot = panels['maxima']

    plot_maxima_over_time(plot, group, start_stop, sign, thresholds)
    plot.text(.5, 1.05,
              'Group {} ({}) Firing over time'.format(gid,
                  TYPE_NAMES[group_joined['type']]),
              va='bottom', ha='center', transform=plot.transAxes,
              backgroundcolor='w')

    #plot.text(0, 1, '{} ({})'.format(gid, group['type']),
    #          transform=plot.transAxes, va='bottom', ha='left') 

    # ISI
    times = group_joined['times']
    spikes = group_joined['spikes']
    timelim = (start_stop[0]/1000/60, start_stop[1]/1000/60)

    plot = panels['isi']
    data = np.diff(times)  # to ms
    data = data[data <= 100]
    plot.cla()
    if data.shape[0] > 10:
        plot.hist(data, 100, edgecolor='none')
        plot.set_xlim([0, 100])
        under3 = (data <= 3).sum()/data.shape[0]
        plot.text(.5, 1.1, '{:.1%} < 3 ms'.format(under3),
                  va='top', ha='center', transform=plot.transAxes,
                  backgroundcolor='w')
    else:
        plot.axis('off')
    plot.set_ylabel('# lags')
    plot.set_xlabel('ms')
    plot.text(.95, .97, 'Inter-Spike Intervals',
              va='top', ha='right', transform=plot.transAxes,
              backgroundcolor='w')

    # all means?

    # count over time
    plot = panels['cumulative']
    plot.cla()
    plot.plot(times/1000/60, range(len(times)))
    plot.set_xticklabels([])
    plot.set_xlim(timelim)
    plot.set_ylabel('# spikes')
    plot.grid(True)
    #plot.set_xticks(tickpos)
#    add_events(plot, events)
#    plot.text(.5, -.15, u'Propofol concentration [µg/mL]', va='top', ha='center',
#              transform=plot.transAxes, backgroundcolor='w')
    plot.text(.5, .95, 'Cumulative spike count',
              va='top', ha='center', transform=plot.transAxes,
              backgroundcolor='w')

    # density
    plot = panels['density']
    plot.cla()
    spike_heatmap(plot, spikes)
    plot.set_xticks([])
    plot.set_ylabel(u'µV')

    # other density
    data = np.array([np.histogram(row, bins=DENSITY_BINS)[0]
                    for row in spikes.T])
    plot = panels['density2']
    plot.cla()
    plot.axis('off')
    plot.imshow(data.T, aspect='auto', origin='lower', cmap=cm.hot)

    # now the images

#    for i in range(12):
#        panels['images'][i].cla()
#        panels['images'][i].axis('off')
#
#    for cimg in range(min(len(images), 12)):
#        img = mpl.imread(images[cimg])
#        plot = panels['images'][cimg]
#        plot.imshow(img)
#
#    def add_label(plot, label):
#        plot.text(-.2, .5,  label, transform=plot.transAxes, rotation=90,
#                  ha='left', va='center',)
#
#    label = 'Subunits 1 to {}'.format(min(len(images), 6))
#    add_label(panels['images'][0], label)
#
#    if len(images) > 6:
#        label = 'Subunits 7 to {}'.format(min(len(images), 12))
#        add_label(panels['images'][6], label)
#
#
    #FIG.suptitle(title)


def run_file(fname, sign, label, savefolder):
    """
    run overview plot on one spikes file
    """

    print('Initializing {} {} {}'.format(fname, sign, label))
    # get thresholds

    manager = Combinato(fname, sign, label)
    if not manager.initialized:
        print('Could not initialize {} {}'.format(fname, label))
        return
    thresholds = manager.get_thresholds()
    start = manager.times[sign][0]
    stop = manager.times[sign][-1]
    nspk = manager.times[sign].shape[0]
    duration_min = (stop - start)/1000/60
    start_stop = (start, stop)
    entname = manager.header['AcqEntName']

    if duration_min > 120:
        dur_str = '{:.1f} h'.format(duration_min/60)
    else:
        dur_str = '{:.0f} min'.format(duration_min)

    entity = manager.header['AcqEntName']

    print('Sorting contains {} spikes from {}, duration {}'.
          format(nspk, entity, dur_str))

    if not manager.initialized:
        print('could not initialize ' + fname)
        return


    groups_joined = manager.get_groups_joined()
    groups = manager.get_groups()
    
    bname = os.path.splitext(os.path.basename(fname))[0]

    for gid in groups_joined:
        gtype = manager.get_group_type(gid)
        groups_joined[gid]['type'] = gtype
        plot_group(gid,
                   groups[gid],
                   groups_joined[gid],
                   start_stop,
                   sign,
                   savefolder,
                   thresholds)
        gtypename = LOCAL_TYPE_NAMES[gtype]
        outfname = '{}_{}_{}_{:03d}_{}.png'.\
                format(bname, entname, label, gid, gtypename)
        FIG.savefig(outfname)


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
        run_file(fname, sign, label, savefolder)
