# -*- coding: utf-8 -*-
"""
file collects widgets that call matplotlib
"""

from __future__ import print_function, division, absolute_import
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import numpy as np
from matplotlib.backends.backend_qt4agg import\
    FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as mpl
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
import time

from .. import options, TYPE_NAMES 
from .basics import spikeDist

if options['UseCython']:
    from .cross_correlogram_cython import cross_correlogram
else:
    from .cross_correlogram import cross_correlogram
    

def delfunc(obj):
    """
    helper
    """
    while 1:
        l = len(obj)
        if not l:
            break
        obj[0].remove()
        if len(obj) == l:
            del obj[0]


class MplCanvas(FigureCanvas):
    """
    standard canvas for matplotlib figures
    """

    def __init__(self, parent=None, width=5, height=5, dpi=75):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        color = QPalette().color(QPalette.Light)
        rgb = (color.red()/255., color.green()/255., color.blue()/255.)

        self.updateGeometry()
        self.fig.patch.set_color(rgb)

    def setFixedSize(self):
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.updateGeometry()

    def delAxes(self):
        pass

    def save_as_file(self, fname, dpi):
        self.fig.savefig(fname, dpi=dpi)

    def __del__(self):
        mpl.close(self.fig)


class GroupOverviewFigure(MplCanvas):
    """
    This Figure represents an overview plot of one group
    """

    def __init__(self, parent, width=5, height=5):
        super(GroupOverviewFigure, self).__init__(parent, width, height)
        self.currentGroup = None
        grid = GridSpec(3, 3, left=.05, right=.97, top=.98, bottom=.05,
                        hspace=.15, wspace=.2)

        self.meanDensAx = self.fig.add_subplot(grid[0])
        self.meanDensLogAx = self.fig.add_subplot(grid[1])
        self.meanAx = self.fig.add_subplot(grid[2])

        self.isiAx = self.fig.add_subplot(grid[3])
        self.cumSpikeAx = self.fig.add_subplot(grid[4])
        self.maxDistrAx = self.fig.add_subplot(grid[5])
        self.overTimeAx = self.fig.add_subplot(grid[6:9])

        titles = ((self.meanDensAx, 'Density'),
                  (self.meanDensLogAx, 'Log density'),
                  (self.meanAx, 'Mean spikes'),
                  (self.isiAx, 'Inter-spike intervals'),
                  (self.maxDistrAx, 'Distr. of amplitudes'),
                  (self.overTimeAx, 'Amplitude over time'))

        for t in titles:
            t[0].text(1, 1, t[1], transform=t[0].transAxes,
                      backgroundcolor='w',
                      horizontalalignment='right',
                      verticalalignment='top')
        self.cumSpikeAx.text(0, 1, 'Cumulative spike count',
                             transform=self.cumSpikeAx.transAxes,
                             backgroundcolor='w',
                             horizontalalignment='left',
                             verticalalignment='top'),

        for p in (self.meanDensAx, self.meanDensLogAx):
            p.set_yticks([])
            p.set_xticks([])

        args = ((self.meanAx,
                 0, 1,
                 u'µV',
                 'left',
                 'top'),
                (self.maxDistrAx,
                 1, 0,
                 u'µV',
                 'right',
                 'bottom'),
                (self.overTimeAx,
                 1, 0,
                 u'min',
                 'right',
                 'bottom'),
                (self.overTimeAx,
                 0, 1,
                 u'µV',
                 'left',
                 'top'),
                (self.isiAx,
                 1, 0,
                 u'ms',
                 'right',
                 'bottom'),
                (self.cumSpikeAx,
                 1, 0,
                 'min',
                 'right',
                 'bottom'))

        for a in args:
            a[0].text(a[1], a[2], a[3], transform=a[0].transAxes,
                      backgroundcolor='w',
                      horizontalalignment=a[4],
                      verticalalignment=a[5])

        self.cumSpikeAx.set_ylim(auto=True)

    def setOptions(self, xax, times, sign='pos', thresholds=None):

        self.sign = sign

        # set the default limits

        # use threshold times if wanted
        if (thresholds is not None) and options['GuiUseThresholdTimeAxis']:
            self.startTime = thresholds[0, 0]
            self.stopTime = thresholds[-1, 0]
            print('Using times from thresholds')
        else:
            self.startTime = times[0]
            self.stopTime = times[1]

        self.meanAx.set_xlim(xax)
        self.meanAx.set_ylim(options['overview_ax_ylim'])

        self.isiAx.set_xlim((0, options['compute_isi_upto_ms']))
        self.isiAx.set_xticks(np.linspace(0,
                                          options['compute_isi_upto_ms'],
                                          6))

        # convert all times to minutes for display only
        self.overTimeAx.set_xlim((0, (self.stopTime - self.startTime)/6e4))

        self.thresholds = thresholds
        # print(self.thresholds[-1, 1] - self.thresholds[0, 0])

        self.draw()

    def deletePlots(self):

        objects = [self.meanAx.lines,
                   self.isiAx.patches,
                   self.overTimeAx.lines,
                   self.meanDensAx.images,
                   self.cumSpikeAx.lines,
                   self.meanDensLogAx.images,
                   self.maxDistrAx.patches,
                   self.maxDistrAx.lines]

        map(delfunc, objects)

    def updateInfo(self, group):
        """
        plots info for the currently selected group
        """
        t1 = time.time()
        self.deletePlots()
        self.additionalIsiPatches = []

        # group means plot
        data = group.meandata

        if len(data):
            x = range(data[0].shape[0])
            ylim_mean = 1.5 * np.max(data)
            self.meanAx.set_ylim(-ylim_mean, ylim_mean)
            for row in data:
                line = mpl.Line2D(x, row)
                self.meanAx.add_line(line)

        # ISI plot
        data = group.isidata

        if len(data) > 1:
            nBins = options['isi_n_bins']
            n, _, _ = self.isiAx.hist(data, nBins,
                                      color=options['histcolor'],
                                      histtype=options['histtype'])

            self.isiAx.set_ylim((0, max(n) + 5))
            # mark percentage
            too_short =\
                (data <= options['isi_too_short_ms']).sum()/group.times.shape[0]

            titlestr = '{:.1%} < {} ms'.format(too_short,
                                               options['isi_too_short_ms'])
        else:
            self.isiAx.cla()
            titlestr = ''

        self.isiAx.set_title(titlestr)

        # maxima and cumuluative plot
        if self.sign == 'pos':
            data = [c.spikes.max(1) for c in group.clusters]
        elif self.sign == 'neg':
            data = [c.spikes.min(1) for c in group.clusters]

        times = [(c.times - self.startTime)/6e4 for c in group.clusters]

        if len(times):
            for x, y in zip(times, data):
                self.overTimeAx.plot(x, y, 'b.',
                                     markersize=options['smallmarker'])
            tdata = np.hstack(times)
            tdata.sort()
            self.cumSpikeAx.plot(tdata, range(len(tdata)), 'b')
            self.cumSpikeAx.set_xlim(0, tdata.max())
            self.cumSpikeAx.set_ylim(0, len(tdata))
            tstr = '{} spikes'.format(len(tdata))  # show in GUI

            mdata = np.hstack(data)

            if self.sign == 'pos':
                self.overTimeAx.set_ylim((0, mdata.max() * 1.1))
            else:
                self.overTimeAx.set_ylim((mdata.min() * 1.1, 0))

            ns, _, _ = self.maxDistrAx.hist(mdata, 100,
                                            color=options['histcolor'],
                                            histtype=options['histtype'])
            self.maxDistrAx.set_xlim(min(0, mdata.min()), max(0, mdata.max()))
            self.maxDistrAx.set_ylim((0, max(ns) * 1.15))

        else:
            tstr = ''
        self.cumSpikeAx.set_title(tstr)

        # thresholds
        if self.thresholds is not None:
            # print((self.thresholds[-1, 1] - self.thresholds[0, 0])/1000/60)
            # thr_times = self.thresholds[:, :2].ravel() - self.startTime
            thr_times = self.thresholds[:, :2].ravel() - self.thresholds[0, 0] 
            thr_times /= 6e4  # now in minutes
            tthr = (self.thresholds[:, 2], self.thresholds[:, 2])
            thrs = np.vstack(tthr).T.ravel()
            if self.sign == 'neg':
                thrs *= -1
            self.overTimeAx.plot(thr_times, thrs, 'm', lw=2)
            self.overTimeAx.set_xlim((thr_times[0], thr_times[-1]))

            if len(thrs) > 1:
                self.maxDistrAx.axvline(np.median(thrs), color='m', lw=2)
                self.maxDistrAx.axvline(thrs.min(), color='m')
                self.maxDistrAx.axvline(thrs.max(), color='m')
            else:
                self.maxDistrAx.axvline(thrs[0], color='m')

        # Density plot
        data = group.densitydata
        if len(data):
            self.meanDensAx.imshow(data,
                                   cmap=options['cmap'],
                                   aspect='auto',
                                   origin='lower')
            self.meanDensLogAx.imshow(np.log(1 + data),
                                      cmap=options['cmap'],
                                      aspect='auto',
                                      origin='lower')

        self.draw()

        t2 = time.time()
        print('Update time: {:.0f} ms'.format((t2 - t1)*1000))

    def mark(self, index, histdata=None):
        """
        draws current data in red
        """
        for ax in (self.meanAx, self.overTimeAx):
            lines = ax.get_lines()
            for i, l in enumerate(lines):
                color = 'b'
                markersize = options['smallmarker']
                zorder = i
                if i == index:
                    color = 'r'
                    markersize = options['bigmarker']
                    zorder = len(lines)
                l.set_zorder(zorder)
                l.set_color(color)
                l.set_markersize(markersize)

        if histdata is not None:
            # remove additional patches
            delfunc(self.additionalIsiPatches)
            if len(histdata):
                n, _, self.additionalIsiPatches =\
                      self.isiAx.hist(histdata, 100,
                                      color='r', histtype='stepfilled')
                self.isiAx.set_ylim((0, max(n) + 5))
        ts1 = time.time()
        self.draw()
        ts2 = time.time()
        print('Drawing: {:0.1f} ms'.format((ts2 - ts1)*1000))


class ComparisonFigure(MplCanvas):
    def __init__(self, parent, width=5, height=5):
        super(ComparisonFigure, self).__init__(parent, width, height)
        # positions for the group plots
        self.positions = ((.1, .7, .2, .2),
                          (.7, .7, .2, .20))

    def xcorr(self, group1, group2):
        lag = 50  # ms
        self.fig.clf()
        times1 = np.hstack([c.times for c in group1.clusters])
        times2 = np.hstack([c.times for c in group2.clusters])
        times1.sort()
        times2.sort()

        lags = cross_correlogram(times1, times2, lag, group1 is group2)

        if lags.any():
            # ax = self.fig.add_subplot(1, 1, 1)
            lags_plot = self.fig.add_axes((.05, .05, .9, .9))

            # calculate the bins
            greater_len = max(len(times1), len(times2))

            # plot it
            bins = np.linspace(-lag, lag, min(2*lag, max(2*lag, np.sqrt(greater_len))))
            hist_data, _ = np.histogram(lags, bins)
            lags_plot.bar(bins[:-1], hist_data, linewidth=.1,
                width=(bins[1]-bins[0])) #, histtype=options['histtype'])
            bigleg = bins[hist_data.argmax()]
            lags_plot.text(bigleg,
                hist_data.max(), '{:.0f} ms'.format(bigleg), va='bottom')
            lags_plot.set_ylim((0, hist_data.max()*1.3))
            x = None
            this_max  = 0
            this_min = 0
            lags_plot.set_xlim([-lag, lag])
            axes = [] 

            for i, group in enumerate((group1, group2)):
                group_plot = self.fig.add_axes(self.positions[i])
                axes.append(group_plot)
                group_plot.patch.set_alpha(.5)
                group_plot.grid(True)
                for spikes in group.meandata:
                    this_max = np.max((this_max, spikes.max()))
                    this_min = np.min((this_min, spikes.min()))
                    if x is None:
                        x = np.arange(0, spikes.shape[0])
                    group_plot.plot(x, spikes, 'b')
                group_plot.set_xticks(range(0, len(x), 16))
                group_plot.set_xticklabels([])
                group_plot.text(.01, 1.1, '{} ({})'.format(group.name,
                    TYPE_NAMES[group.group_type]), transform=group_plot.transAxes,
                    va='bottom')
        
            for group_plot in axes:
                group_plot.set_ylim((1.1 * this_min, 1.1 * this_max))
        self.draw()


class AllGroupsFigure(MplCanvas):
    def __init__(self, parent, width=5, height=5):
        super(AllGroupsFigure, self).__init__(parent, width, height)
        self.x = None
        self.texts = []
        self.spikecounts = []

    def addAxes(self, x, session, index):
        self.x = x
        self.session = session
        fig = self.fig

        for ax in fig.get_axes():
            self.fig.delaxes(ax)

        ngroup = len(index)
        ncol = 4
        nrow = max(int(np.ceil(ngroup/ncol)), 2)
        if ncol * nrow < ngroup:
            nrow += 1

        grid = GridSpec(nrow, ncol,
                        wspace=.02, hspace=.02,
                        left=.07, bottom=.02,
                        top=.98, right=.98)

        total_max = 0
        total_min = 0
        axes = []
        for i, gId in enumerate(index):
            data = session.groupsById[gId].meandata
            if len(data):
                total_max = np.max((total_max, np.max([d.max() for d in data])))
                total_min = np.min((total_min, np.min([d.min() for d in data])))
            ax = fig.add_subplot(grid[i])
            session.groupsById[gId].assignAxis = ax
            name = session.groupsById[gId].name
            ax.set_label(name)
            # ax.text(.05, .95, name, va='top', transform=ax.transAxes)
            for row in data:
                ax.plot(x, row, 'b')
            ax.grid(True)
            ax.set_xticks(range(0, len(x), 16))
            ax.set_xticklabels([])
            if i != 0:
                ax.set_yticklabels([])
            ax.set_xlim((0, len(x)))
            axes.append(ax)
        ylim = (1.2 * total_min, 1.2* total_max)

        for ax in axes:
            ax.set_ylim(ylim)

        self.updateInfo(index)
        self.draw()

    def updateInfo(self, index):
        delfunc(self.spikecounts)
        for gId in index:
            group = self.session.groupsById[gId]
            ax = group.assignAxis
            if ax is not None:
                while(len(ax.lines)):
                    ax.lines[0].remove()
                    if len(ax.lines):
                        del ax.lines[0]
                data = group.meandata
                counts = sum([c.spikes.shape[0] for c in group.clusters])
                gtype = TYPE_NAMES[group.group_type]
                self.spikecounts.append(ax.text(.05, .9,
                                                '{} (# {}, {})'.format(gId, counts, gtype),
                                                transform=ax.transAxes))
                for row in data:
                    ax.plot(self.x, row, 'b')

        self.draw()

    def mark(self, groupName, index):
        delfunc(self.texts)

        data = self.session.groupsByName[groupName].\
            clusters[index].meanspike

        for ax in self.fig.get_axes():
            lines = ax.get_lines()
            name = ax.get_label()
            group = self.session.groupsByName[name]
            meandata = np.array(group.meandata).mean(0)
            dist = spikeDist(meandata, data)
            length = len(group.clusters)
            if len(lines) > length:
                lines[-1].remove()
                if len(lines) > length:
                    del lines[-1]
            line = mpl.Line2D(self.x, data, color='r')
            ax.add_line(line)
            self.texts.append(ax.text(.05, .05, format(dist, '.2f'),
                              transform=ax.transAxes))

        self.draw()
