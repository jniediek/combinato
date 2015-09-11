# -*- encoding: utf-8 -*-
# JN 2015-05-11

# what do I want in this script?
# * extraction thresholds in each region
# (and regression line, or other measure of variability)
# * rationale it's interesting to see whether highly variable channels are
# in one macro
# * firing rate stability for non-artifacts (correlated with threshold?)
# * percentage of artifacts of each category (correlated within region?)

# structure of the script
# region -> find channels -> plot extraction thr and firing rates
#                         -> write down artifact criteria

"""
plot extraction thresholds and spike counts over time
"""

from __future__ import print_function, division
import os

import numpy as np  # pylint:   disable=E1101

import tables
import matplotlib.pyplot as mpl
import matplotlib.cm as cm

from combinato import SortingManagerGrouped, get_regions


FIGSIZE = (7, 6)

REGIONS = ('A', 'AH', 'MH', 'PH', 'EC', 'PHC', 'I')

LEFT_COLORS = cm.spectral(np.linspace(0, 1, len(REGIONS)))
RIGHT_COLORS = cm.summer(np.linspace(0, 1, len(REGIONS)))
NUM_COLORS = cm.winter(np.linspace(0, 1, 8))

COLORDICT = {}

for i, region in enumerate(REGIONS):
    COLORDICT['L' + region] = LEFT_COLORS[i]
    COLORDICT['R' + region] = RIGHT_COLORS[i]

for i in range(1, 9):
    COLORDICT[str(i)] = NUM_COLORS[i-1]
JOBS = ('thr', 'arti')


def plotthr(thrplot, fireplot, thr, times, color='r'):
    """
    plot the threshold data
    """
    xdata = thr[:, :2].ravel()
    xdata -= xdata[0]
    xdata /= 6e4
    xlim = xdata[[0, -1]]

    thrs = np.vstack((thr[:, 2], thr[:, 2])).T.ravel()
    thrplot.plot(xdata, thrs, color=color)
    thrplot.set_xlim(xlim)

    xtimes = (times - times[0])/6e4
    # countdata = np.linspace(0, 1, len(xtimes))

    # fireplot.plot(xtimes, countdata, color=color)
    # fireplot.set_xlim(xlim)

    bins = np.append(thr[:, 0], thr[-1, 1])
    # bins /= 1e3
    spcount, _ = np.histogram(times, bins=bins)
    spcount = spcount.astype(float)
    spcount /= times.shape[0]
    print(spcount)
    spplotdata = np.vstack((spcount, spcount)).T.ravel()
    fireplot.plot(xdata, spplotdata, color=color)


def create_plots():
    fig = mpl.figure(figsize=FIGSIZE)
    plot = fig.add_subplot(1, 2, 1)
    plot.set_ylabel(u'µV')
    plot.set_xlabel(u'min')
    plot.set_title(u'Extraction threshold over time')
    plot2 = fig.add_subplot(1, 2, 2)
    # plot2 = plot.twinx()
    plot2.set_xlabel(u'min')
    plot2.set_ylabel('% fired')
    plot2.set_title('Spike count over time')

    return plot, plot2


def plotarti(artifacts):
    """
    plots artifact statistics
    """
    from nlxpy.artifacts.mask_artifacts import options_by_bincount,\
        options_by_diff, options_by_height

    art_types = (options_by_bincount, options_by_diff, options_by_height)
    tot = len(artifacts)

    for art in art_types:
        name = art['name']
        artid = art['art_id']
        perc = (artifacts == artid).sum()/tot
        print('{}: {:.1%}'.format(name, perc))


def main(fnames, sign='pos', title=''):
    """
    opens the file, calls plot
    """

    thrplot, fireplot = create_plots()

    thrplot.set_title(title)
    thr_legend_handles = {}

    for fname in fnames:
        if os.path.isdir(fname):
            fname = os.path.join(fname, 'data_' + fname + '.h5')

        man = SortingManagerGrouped(fname)

        thr = man.h5datafile.root.thr[:]
        times = man.h5datafile.get_node('/' + sign, 'times')[:]
        if not len(times):
            continue

        try:
            artifacts = man.h5datafile.get_node('/' + sign, 'artifacts')[:]
        except tables.NoSuchNodeError:
            print('No artifacts defined')
            artifacts = None

        if man.header is not None:
            entname = man.header['AcqEntName']
            print(entname[-1])
            color = COLORDICT[entname[-1]]
            entname = entname[-1]
        else:
            color = 'k'
            entname = 'unknown region'
        del man

        if 'thr' in JOBS:
            plotthr(thrplot, fireplot, thr, times, color)
            if entname not in thr_legend_handles:
                thr_legend_handles[entname] = mpl.Line2D([0], [0], color=color,
                                                         label=entname)

        if 'arti' in JOBS:
            if artifacts is not None:
                plotarti(artifacts)

    # thrplot.legend(handles=thr_legend_handles.values())


def loop_over_regions(path):
    """
    do the plots by region
    """
    from collections import defaultdict
    regions = get_regions(path)
    regions_to_fnames = defaultdict(list)
    for reg in regions:
        ncsfiles = regions[reg]
        for fname in ncsfiles:
            if os.path.isdir(fname[:-4]):
                regions_to_fnames[reg].append(os.path.basename(fname[:-4]))

    for reg in regions_to_fnames:
        main(regions_to_fnames[reg], 'pos', reg)


if __name__ == "__main__":
    loop_over_regions(os.getcwd())
    mpl.show()
