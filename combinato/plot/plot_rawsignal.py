# -*- coding: utf-8 -*-
#added comment JN 2014-12-07
"""
script generates overview figures *from ncs files* to give you a first
impression of the data quality, movement artifacts and so on
"""
from __future__ import print_function, division, absolute_import

import os
import sys
import time
import subprocess
import numpy as np
import scipy.signal as sig
import matplotlib.pyplot as mpl
from matplotlib.gridspec import GridSpec

from .. import NcsFile, DefaultFilter, get_regions

MINS = 2
EVERY_MINS_MIN = 30 # difference can't be below this
PLOTTIMES = (.5, 30, MINS*60) # in sec
Q = 1000
DPI = 100
FIGSIZE = (3.5, .5)
FONTSIZE = 8
OVERVIEW_NAME = 'overview'
TEXT_BBOX = {'facecolor' : 'white', 'lw' : 0}
GRID = GridSpec(1, 1,
                left=.01,
                right=.99,
                top=.98,
                bottom=.02,
                hspace=0,
                wspace=0)
VERT_ALIGN = {1 : 'top', -1 : 'bottom'}


def overview_plot(channel):
    """
    Plot sections of the raw signal in order to give a first impression
    about what's going on during the recording
    Needs the ImageMagick program 'montage' (available even for window$)
    """
    figs = []
    plots = []
    fignames = []

    print('Opening %s' % channel)
    fid = NcsFile(channel)
    timestep = fid.timestep
    total_time = fid.num_recs * 512 * timestep # in seconds

    n_sessions = int(np.ceil(total_time/(60 * EVERY_MINS_MIN)))

    if n_sessions < 10:
        n_sessions = 10

    #basename = os.path.splitext(channel)[0]

    #if not os.path.isdir(basename):
    #    os.mkdir(basename)

    if not os.path.isdir(OVERVIEW_NAME):
        os.mkdir(OVERVIEW_NAME)

    overview_tmp = OVERVIEW_NAME
    #if not os.path.isdir(overview_tmp):
    #    os.mkdir(overview_tmp)

    timefactor = (512*timestep)/60

    voltfactor = fid.header['ADBitVolts'] * 1e6
    entname = fid.header['AcqEntName']
    cscname = os.path.basename(channel)[:-4]
    sessionstarts = np.array(np.linspace(0, fid.num_recs, n_sessions), dtype=int)
    fignames = []
    myfilter = DefaultFilter(timestep)
    n_recs_load = int(MINS*60/(512*timestep))

    for i in range(3):
        fig = mpl.figure(figsize=FIGSIZE)
        plots.append(fig.add_subplot(GRID[0]))
        figs.append(fig)

    for sescount in range(n_sessions):

        start = sessionstarts[sescount]
        stop = start + n_recs_load
        if stop >= fid.num_recs:
            start = fid.num_recs - n_recs_load - 1
            stop = fid.num_recs - 1
        data = fid.read(start, stop, 'data').astype(np.float32)
        data *= voltfactor

        for i in range(3):
            plot = plots[i]
            plot.cla()
            ptime = PLOTTIMES[i]
            n_samp = int(ptime/timestep)

            if i == 0:
                pdata = data[:n_samp]

            elif i == 1:
                pdata = myfilter.filter_detect(data[:n_samp])

            elif i == 2:
                pdata = sig.decimate(data, Q, 4, zero_phase=False)

            x = np.arange(pdata.shape[0])*timestep

            if i == 2:
                x *= Q/60

            plot.plot(x, pdata)

            plot.set_xlim((x[0], x[-1]))

            if i == 1:
                ylim = 100
            else:
                ylim = 300

            plot.set_ylim((-ylim, ylim))
            plot.set_xticklabels([])
            plot.grid(True, axis='x')
            plot.set_yticks((-ylim, 0, ylim))

            if sescount == 0:
                if i == 0:
                    text = '{} {} {:.2f} s raw'.format(entname,
                                                       cscname,
                                                       PLOTTIMES[0])
                else:
                    text = '{:.0f} s'.format(PLOTTIMES[i])

                if i == 1:
                    text += ' bandpassed'
                elif i == 2:
                    text += ' raw'

                xpos = x[-1]
                ypos = ylim*.96
                for sign in (1, -1):
                    plot.text(xpos, sign*ypos, str(sign*ylim) + u' µV', fontsize=FONTSIZE,
                              bbox=TEXT_BBOX, ha='right', va=VERT_ALIGN[sign])
            else:
                plot.set_yticklabels([])
                text = '{:.0f} min'.format(start * timefactor)

            xpos = x[-1]*.02
            ypos = ylim * .55
            plot.text(xpos, ypos, text, fontsize=FONTSIZE,
                      bbox=TEXT_BBOX)


            figname = '{}_{:1d}_{:03d}.png'.format(entname, i, sescount)
            figpath = os.path.join(overview_tmp, figname)
            fignames.append(figpath)
            figs[i].savefig(figpath, DPI=DPI)

    mpl.close('all')

    arg = ['montage', '-tile', '3', '-geometry',
           '{}x{}'.format(FIGSIZE[0]*DPI, FIGSIZE[1]*DPI)] + fignames

    outname = os.path.join('overview',
                           'overview_{}_{}.png'.format(entname, cscname))
    arg.append(outname)
    subprocess.call(arg)
    for figname in fignames:
        os.remove(figname)
    print('Completed ' + entname)

def main():
    t = time.time()
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.getcwd()

    my_regions = get_regions(path)
    rnames = sorted(my_regions.keys())
    for i in range(len(rnames)):
        channels = my_regions[rnames[i]]
        for ch in channels:
            overview_plot(ch)

    print('Plotting took {:.0f} seconds'.format(time.time() - t))
