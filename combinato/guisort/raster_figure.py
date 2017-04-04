# JN 2016-03-02
"""
show resposes in css-gui
"""

from __future__ import print_function, division, absolute_import

import os
import numpy as np
import scipy.signal as signal
from .sort_widgets import MplCanvas
from matplotlib.pyplot import imread
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

HGAP = VGAP = BOTTOM = .02

T_PRE = 1000   # relative to onset
T_POST = 2000  # relative to onset
std = 100
nsamp_window = 10 * std

LW = 1.8   # linewidth of individual lines in raster

fr_bins = np.arange(-T_PRE-500, T_POST+500, 1)
fr_window = signal.get_window(('gaussian', std), nsamp_window)
fr_w = int(nsamp_window/2) - 1   # JN 2016-10-17 add int


def set_raster_properties(p, ylim=8):
    resp_ylim = (-1, ylim)
    for where in ('left', 'right'):
        p.spines[where].set_visible(False)
    p.axvline(0, ls='dashed', color='k')
    p.axvline(1000, ls='dashed', color='k')

    p.set_xlim([-T_PRE, T_POST])
    p.set_xticks([-T_PRE, T_POST])
    p.set_xticklabels([])

    p.set_ylim(resp_ylim)
    p.set_yticks([])


def plot_one_cluster_one_stim(plot, rows, ylim, color):
    """
    version for lists of cl_times
    """
    set_raster_properties(plot, ylim=ylim)
    colors = np.array([color] * len(rows))
    plot.eventplot(rows, colors=colors, linewidths=LW)


def plot_convolution(plot, rows, lw=1):
    """
    good if there is a raster already
    """
    all_times = np.hstack(rows)
    hist, _ = np.histogram(all_times, fr_bins)
    smooth = signal.convolve(hist, fr_window)
    smooth *= (len(rows)/smooth.max())
    smooth -= .5
    plot.plot(fr_bins, smooth[fr_w:-fr_w], 'm', alpha=.5, lw=lw)


def create_raster_rows(cl_times, onset_times):
    """
    prepare for raster plots
    """
    rows = []
    empty = [-2 * T_PRE]
    onset_times /= 1000
    do_plot = False
    for onset_time in onset_times:
        idx = (cl_times >= onset_time - T_PRE) &\
              (cl_times <= onset_time + T_POST)
        if idx.any():
            do_plot = True
            rows.append(cl_times[idx] - onset_time)
        else:
            rows.append(empty)
    return rows, do_plot


def plot_one_plot(plot, scale, spike_times, onset_times,
                  stim_name, image, scrtype, stimnum=None):
    """
    plot either image or name screening raster plot into plot
    """
    colors = ((0, 0, .8), (.7, 0, 0), (1, 1, 0))

    merged_spike_times = np.hstack(spike_times)
    merged_spike_times.sort()

    for i_sp, sptimes in enumerate(spike_times):
        rows, do_plot = create_raster_rows(sptimes,
                                           onset_times.copy())
        if do_plot:
            plot_one_cluster_one_stim(plot, rows,
                                      ylim=len(rows) + 1,
                                      color=colors[i_sp])
        # else:
        #    print('Not plotting raster!')

    rows, do_plot = create_raster_rows(merged_spike_times,
                                       onset_times.copy())
    if do_plot:
        plot_convolution(plot, rows, min(2.5, 10/scale))
    #else:
        #print('Not doing convolution!')

    # plot.text(0, .96, str(len(onset_times)), ha='left', va='top',
    #          transform=plot.transAxes, size=SIZE_STIMNAME)
    if scrtype == 'nscr':
        plot.text(.5, 1.01, stim_name, ha='center', va='bottom',
                  transform=plot.transAxes, size=20 - scale)
    elif scrtype == 'scr':
        imar = OffsetImage(image, zoom=1/scale)
        artist = AnnotationBbox(imar, (.5, 1.01), pad=0,
                                box_alignment=(.5, 0),
                                xycoords='axes fraction',
                                frameon=False)
        plot.add_artist(artist)
        if stimnum is not None:
            plot.text(0, 1.01, '#{}'.format(stimnum), ha='left',
                      va='bottom', transform=plot.transAxes,
                      size=20 - scale)


def get_stim_info(frame, stimulus):
    idx = frame['stim_num'] == stimulus
    stim_name = unicode(frame.loc[idx, 'stim_name'].get_values()[0], 'utf-8')
    fname_image = frame.loc[idx, 'filename'].get_values()[0]
    return stim_name, fname_image


def get_onset_times(frame, stimulus, daytime, paradigm):
    idx = (frame['stim_num'] == stimulus)\
           & (frame['paradigm'] == paradigm)
    if len(daytime):
        idx &= frame['daytime'] == daytime
    return frame.loc[idx, 'time'].get_values() * 1000


class RasterFigure(MplCanvas):
    def __init__(self, parent, width=5, height=5):
        super(RasterFigure, self).__init__(parent, width, height)
        self.frame = None
        self.stimuli = None
        self.images = None
        self.names = None

    def set_paradigm_data(self, frame, image_path):
        self.frame = frame
        self.stimuli = frame['stim_num'].unique()
        self.images = dict()
        self.names = dict()
        for stimulus in self.stimuli:
            stim_name, fname_image = get_stim_info(self.frame, stimulus)
            self.names[stimulus] = stim_name
            fname_image = os.path.join(image_path, fname_image)
            self.images[stimulus] = imread(fname_image)

    def update_figure(self, spiketimes, daytime, scale=5,
                      do_numbers=False):
        """
        update the plot
        """
        figure = self.fig
        figure.clf()
        stimuli = self.stimuli
        n_stim = len(stimuli)

        hgap = HGAP
        vgap = VGAP

        # number of cols is 2 starting from 4 stimuli
        if n_stim > 3:
            n_cols = 2
            plot_width = (1 - 8*hgap)/4
            if len(set(self.frame.paradigm))<2:
                plot_width *= 2
            n_rows = int((n_stim + 1)/2)
        else:
            n_cols = 1
            plot_width = (1 - 4*hgap)/2
            n_rows = n_stim

        row_height = (1 - 2*vgap)/n_rows
        plot_height = row_height * .6
        iterator = zip((0, plot_width + hgap), ('scr', 'nscr'))

        col_shift = 0
        for istim, stimulus in enumerate(stimuli):

            if (n_cols > 1) and (istim >= n_stim/2):
                col_shift = .5

            row_bottom = 1 - vgap - (istim % n_rows)*row_height -\
                row_height + BOTTOM/2 + .01

            for shift, paradigm in iterator:
                if paradigm in set(self.frame.paradigm):
                    pos = (col_shift + hgap + shift, row_bottom,
                       plot_width, plot_height)

                    plot = figure.add_axes(pos)
                    onset_times = get_onset_times(self.frame, stimulus,
                                              daytime, paradigm)
                    if do_numbers:
                        number = stimulus + 1
                    else:
                        number = None
                        plot_one_plot(plot, scale, spiketimes, onset_times,
                              self.names[stimulus], self.images[stimulus],
                              paradigm, number)

                    if (istim + 1 == n_rows) or (istim + 1 == n_stim):
                        plot.set_xticks([0, 1000])
                        plot.set_xticklabels([0, 1000])

        self.draw()
