# -*- encoding: utf-8 -*-
# JN 2014-12-14
# function to plot heatmaps of clusters
from __future__ import absolute_import, division, print_function

import numpy as np
from matplotlib.pyplot import cm

cmap = cm.Blues

# idea taken from http://stackoverflow.com/a/14779462
cmaplist = [cmap(i) for i in range(int(cmap.N/4), cmap.N)]
# set first color to white
cmaplist[0] = (1, 1, 1, 1)
# set last color to black
cmaplist[-1] = (0, 0, 0, 1)

cmap = cmap.from_list('Custom cmap', cmaplist, cmap.N)
spDisplayBorder = 5  # µV additional border in display


def spike_heatmap(ax, spikes, x=None, log=False):
    """
    takes spikes, plots heatmap over samples and mean/std line
    """
    spMin = spikes.min()
    spMax = spikes.max()
    spBins = np.linspace(spMin, spMax, 2*spMax)
    if spBins.shape[0] < 3:
        spBins = np.linspace(spMin, spMax, 3)

    nSamp = spikes.shape[1]

    if x is None:
        x = range(nSamp)

    imdata = np.zeros((len(spBins) - 1, nSamp))

    for col in range(nSamp):
        data = np.histogram(spikes[:, col], bins=spBins)[0]
        if log:
            imdata[:, col] = np.log(1 + data)
        else:
            imdata[:, col] = data

    ydiff = (spBins[1] - spBins[0])/2.
    extent = [x[0], x[-1], spMin-ydiff, spMax-ydiff]

    ax.imshow(imdata,
              cmap=cmap,
              interpolation='hanning',
              aspect='auto',
              origin=0,
              extent=extent)

    spMean = spikes.mean(0)
    spStd = spikes.std(0)

    ax.plot(x, spMean, 'k', lw=1)
    ax.plot(x, spMean + spStd, color=(.2, .2, .2), lw=1)
    ax.plot(x, spMean - spStd, color=(.2, .2, .2), lw=1)

    ax.set_xlim((x[0], x[-1]))
