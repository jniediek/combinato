#!env /usr/bin/python
# -*- coding: utf-8 -*-
# JN 2016-01-12 ncs data viewer
from __future__ import division, print_function, absolute_import
import sys
import os
from glob import glob
from time import time
from collections import defaultdict

import PyQt4.QtGui as qtgui

import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.dates import AutoDateLocator, num2date
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Rectangle

from .ui_viewer import Ui_MainWindow

from .sWidgets import MplCanvas
# from .sWidgets import
from .. import H5Manager, debug, options
# from sleepstg import SleepStg
from .spikes import SpikeView


stylesheet = 'QListView:focus { background-color: rgb(240, 255, 255)}'

COLORS = ['darkblue', 'red', 'magenta', 'black', 'green']
gs = GridSpec(1, 1, top=.95, bottom=.05, left=.05, right=.95)
DEBUG = True


def fmtfunc(x, pos=None):
    d = num2date(x)
    out = d.strftime('%H:%M:%S.')
    out += format(np.round(d.microsecond/1000, 1), '03.0f')
    return out


class SimpleViewer(qtgui.QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(SimpleViewer, self).__init__(parent)
        self.setupUi(self)
        self.figure = MplCanvas(self.centralwidget)
        self.ax = None
        self.ylim = None
        self.lfpfactor = 1

        self.ts_start_nlx = None
        self.ts_start_mpl = None
        self.use_date = False
        self.checked_channels = []
        self.montage = None
        self.positions = None
        self.locator = AutoDateLocator()
        self.formatter = FuncFormatter(fmtfunc)
        self.offset = 150
        self.actionsdir = {self.actionLFP: 'rawdata'}
        self.setup_gui()
        t1 = time()
        self.init_h5man()
        dt = time() - t1
        debug('Init h5 took {:.1f} s'.format(dt))
        # self.sleepstg = SleepStg()
        # self.use_date = self.sleepstg.use_date
        self.setopts()
        self.labelFolder.setText(os.path.split(os.getcwd())[1])
        self.init_events('')
        self.init_montages()

    def setup_gui(self):
        self.verticalLayout.addWidget(self.figure)
        self.addAction(self.actionBack)
        self.addAction(self.actionAdvance)
        self.pushButtonGo.clicked.connect(self.update)
        self.pushButtonAdvance.clicked.connect(self.advance)
        self.pushButtonBack.clicked.connect(self.back)
        self.pushButtonSet.clicked.connect(self.setopts)
        self.pushButtonSpikes.clicked.connect(self.open_spike_dialog)
        self.pushButtonSave.clicked.connect(self.save_image)
        self.actionBack.triggered.connect(self.back)
        self.actionAdvance.triggered.connect(self.advance)
        self.sstglabel = qtgui.QLabel(self)
        self.statusBar().addWidget(self.sstglabel)

    def init_events(self, pattern):
        """
        read events from a text or h5 file
        can be plotted as boxes
        """
        self.event_times = {}
        for name in self.h5man.chs:
            fname = name + pattern + '.txt'
            if os.path.exists(fname):
                self.event_times[name] = np.loadtxt(fname)

    def init_h5man(self):
        cands = glob('*_ds.h5')
        self.h5man = H5Manager(cands)

        for chn in self.h5man.chs:
            action = self.menuChannels.addAction(chn)
            action.setCheckable(True)
            action.triggered.connect(self.setch)

        debug('Available channels: {}'.format(self.h5man.chs))
        for a in self.actionsdir:
            a.triggered.connect(self.set_traces)

    def init_montages(self):
        """
        Make a list of montage files
        """
        cands = glob('*_montage.txt')
        for cand in cands:
            name = cand[:-4]
            action = self.menuRefs.addAction(name)
            action.triggered.connect(lambda x=cand: self.set_montage(cand))

    def set_montage(self, montage_file):
        """
        Read a montage file and activate it
        """
        print(montage_file)
        self.checked_channels = []
        montage = defaultdict(list)
        positions = dict()
        with open(montage_file, 'r') as fid:
            lines = fid.readlines()
            for il, line in enumerate(lines):
                line = line.strip()
                res = line.split('-')
                if len(res) == 2:
                    main, ref = res
                elif len(res) == 1:
                    main = res[0]
                    ref = 0
                if (main in self.h5man.chs):
                    if (ref in self.h5man.chs) or (ref == 0):
                        montage[ref].append(main)
                        positions[main] = il

        self.montage = montage
        self.positions = positions

    def set_traces(self):
        traces = []
        for a, s in self.actionsdir.items():
            if a.isChecked():
                traces.append(s)
        # self.traces = traces
        self.traces = ['rawdata', 'simple']

    def setch(self):
        checked_actions = [a for a in self.menuChannels.children()
                           if a.isChecked()]
        self.checked_channels = [str(a.text()) for a in checked_actions]

    def readlineEdits(self):
        try:
            self.start = int(self.lineEditStart.text())
        except ValueError:
            return False
        try:
            self.recs = int(self.lineEditRecords.text())
        except ValueError:
            return False

        return True

    def save_image(self):
        fname = str(qtgui.QFileDialog.getSaveFileName(self,
                    'Save Image', '~', 'Images (*.jpg, *.pdf, *.png)'))
        self.figure.fig.savefig(fname, dpi=150)

    def convert_time(self, time):
        """
        this will be used to convert to real times etc
        """
        return time/1000

    def plotit(self, start, nblocks):
        # try to deal with references here, later
        allstart = 0
        allstop = np.inf

        if self.montage is None:
            for ich, ch in enumerate(self.checked_channels):
                ioff = self.offset * ich
                start_ch = self.h5man.translate(ch, start)
                stop_ch = start_ch + self.h5man.translate(ch, nblocks)
                d, adbitvolts = self.h5man.get_data(ch, start_ch, stop_ch,
                                                    self.traces)
                data = d * adbitvolts * self.lfpfactor
                time = self.h5man.get_time(ch, start_ch, stop_ch)
                allstart = max(allstart, time[0])
                allstop = min(allstop, time[-1])

                time = self.convert_time(time)

                for itr, trace in enumerate(data):
                    self.ax.plot(time, trace + ioff, COLORS[itr], lw=1)
                self.ax.text(time[0], ioff, ch, backgroundcolor='w')
        else:
            for ref_ch in self.montage:
                ref_data = 0
                ref_time = None
                print('Reference now: ' + str(ref_ch))

                if ref_ch != 0:
                    start_ch_ref = self.h5man.translate(ref_ch, start)
                    stop_ch_ref = start_ch_ref + self.h5man.translate(ref_ch,
                                                                      nblocks)
                    ref_d, adbitvolts = self.h5man.get_data(ref_ch,
                                                            start_ch_ref,
                                                            stop_ch_ref,
                                                            self.traces)
                    ref_data = ref_d * adbitvolts
                    time = self.h5man.get_time(ref_ch, start_ch_ref,
                                               stop_ch_ref)

                for ch in self.montage[ref_ch]:
                    print('Updating {}-{}'.format(ch, ref_ch))
                    start_ch = self.h5man.translate(ch, start)
                    stop_ch = start_ch + self.h5man.translate(ch, nblocks)

                    if ref_ch != 0:
                        assert start_ch == start_ch_ref
                        assert stop_ch == stop_ch_ref
                    d, adbitvolts = self.h5man.get_data(ch, start_ch, stop_ch,
                                                        self.traces)

                    data = ((d * adbitvolts) - ref_data) * self.lfpfactor

                    if ref_time is not None:
                        time = ref_time
                    else:
                        time = self.h5man.get_time(ch, start_ch,
                                                   stop_ch)
                    allstart = max(allstart, time[0])
                    allstop = min(allstop, time[-1])

                    plot_time = self.convert_time(time)
                    shift = self.positions[ch] * self.offset
                    self.ax.plot(plot_time, shift + data, 'darkblue', lw=1)
                    # print(plot_time[0:10], shift+data[0:10])

                    if ref_ch == 0:
                        label = ch
                    else:
                        label = '{}-{}'.format(ch, ref_ch)
                    self.ax.text(plot_time[0], shift, label,
                                 backgroundcolor='w')

        self.ax.set_xlabel('seconds')
        conv_start, conv_stop = [self.convert_time(t) for t in (allstart, allstop)]
        self.ax.set_xlim((conv_start, conv_stop))

        self.allstart = allstart
        self.allstop = allstop

        if self.actionShowBoxes.isChecked():
            for ich, ch in enumerate(self.checked_channels):
                if ch in self.event_times:
                    ioff = self.offset * ich
                    self.plot_boxes(ch, ioff)

    def plot_boxes(self, ch, offset):
        """
        If there are events, plot them
        """
        events = self.event_times[ch]
        idx = (events[:, 0] >= self.allstart) & (events[:, 1] <= self.allstop)
        print(idx.sum())

        for row in events[idx, :]:
            start = self.convert_time(row[0])
            stop = self.convert_time(row[1])
            rec = Rectangle((start, offset - self.offset/2),
                            stop - start,
                            self.offset,
                            edgecolor='none',
                            alpha=options['alpha'],
                            facecolor='y')
            self.ax.add_artist(rec)

    def plot_spikes(self, ch, offset):
        self.h5man.spm.set_beg_end(ch,
                                   self.current_start_time,
                                   self.current_stop_time)
        ptimes = []
        if ch in self.h5man.spm.sortedfiles:
            print('getting sorted data!')
            clu = self.h5man.spm.get_sorted_data(ch, self.current_start_time,
                                                 self.current_stop_time)

            for c, cl in clu.items():
                print(c, cl['times'].shape[0])
                if len(cl['times']):
                    ptimes.append(self.sleepstg.convert_time(cl['times']/1000))
                    print (self.current_start_time,
                           self.current_stop_time, cl['times'][0])

        else:
            sptimes = self.h5man.spm.get_sp_data(ch)
            ptimes.append(self.sleepstg.convert_time(sptimes/1000))

        color = 'brgymkkkkkkkkkkkkkk'
        for i, cluster in enumerate(ptimes):
            print(num2date(ptimes[0]))
            y = offset * np.ones(len(cluster), 'int8')
            self.ax.plot(cluster, y, color[i] + '|',
                         ms=options['ms'], mew=options['mew'])

    def update(self):
        if not self.readlineEdits():
            return
        if (len(self.checked_channels) == 0) and (self.montage is None):
            return
        if self.ax is None:
            self.ax = self.figure.fig.add_subplot(gs[0])
        self.ax.cla()
        self.ax.grid(True)
        self.ax.set_ylabel(u'µV')
        self.set_traces()

        self.plotit(self.start, self.recs)

        if self.use_date:
            sstgnow = self.sleepstg.get_sleepstage(ctime[0], ctime[-1])
            self.sstglabel.setText(sstgnow)
            self.ax.xaxis.set_major_locator(self.locator)
            self.ax.xaxis.set_major_formatter(self.formatter)

        # if self.ylim is not None:
        #    if self.ylim == (0, 0):
        #        ylim = (-200, len(self.checked_channels) * self.offset)
        #        self.ax.set_ylim(ylim)
        #    else:
        #        self.ax.set_ylim(self.ylim)
        #    self.ax.set_yticks(range(0, ylim[1] + 100, 100))
        #    self.ax.set_yticklabels([0, 100])

        self.figure.draw()

    def advance(self):

        if not self.readlineEdits():
            return
        self.lineEditStart.setText(str(self.start + self.recs))
        self.update()

    def back(self):
        if not self.readlineEdits():
            return
        self.lineEditStart.setText(str(self.start - self.recs))
        self.update()

    def setopts(self):

        ylimlow = int(self.spinBoxYlimLow.value())
        ylimhigh = int(self.spinBoxYlimHigh.value())

        self.ylim = (ylimlow, ylimhigh)

        lfpperc = float(self.spinBoxLFPpercent.value())
        self.lfpfactor = lfpperc/100

        self.update()

    def open_spike_dialog(self):
        dialog = SpikeView(self)
        dialog.show()


def main():
    app = qtgui.QApplication(sys.argv)
    w = SimpleViewer()
    w.show()
    app.exec_()

if __name__ == "__main__":
    main()
