#!/usr/bin/python3
# -*- coding: utf-8 -*-
# JN 2016-01-12 ncs data viewer
from __future__ import division, print_function, absolute_import
import sys
import os
from glob import glob
from time import time

import PyQt4.QtGui as qtgui

import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.dates import AutoDateLocator, num2date
from matplotlib.ticker import FuncFormatter
# from matplotlib.patches import Rectangle

from .ui_viewer import Ui_MainWindow

from .sWidgets import MplCanvas
# from .sWidgets import
from .. import H5Manager, debug, options
# from sleepstg import SleepStg
from .spikes import SpikeView


stylesheet = 'QListView:focus { background-color: rgb(240, 255, 255)}'

gs = GridSpec(1, 1, top=.95, bottom=.05, left=.05, right=.95)
print(sys.version)
DEBUG = True

colordict = {
    'rawdata': 'b',
    'ripple': 'g',
    'logothetis': 'r',
    'simple': '#999900',
    'ynir': 'm'
}

swrboxcolors = {
    'logothetis': '#990000',
    'ynir_short': '#009900',
    'ynir_long': '#000099',
    'our': '#999900'
}


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
        self.locator = AutoDateLocator()
        self.formatter = FuncFormatter(fmtfunc)
        self.offset = 150
        self.actionsdir = {
            self.actionLFP: 'rawdata',
            self.actionFiltered: 'ripple',
            self.actionLogothetis: 'logothetis',
            self.actionSimple: 'simple',
            self.actionYuval_Nir: 'ynir'
            }
        self.setup_gui()
        t1 = time()
        self.init_h5man()
        dt = time() - t1
        debug('Init h5 took {:.1f} s'.format(dt))
        # self.sleepstg = SleepStg()
        # self.use_date = self.sleepstg.use_date
        self.setopts()
        self.labelFolder.setText(os.path.split(os.getcwd())[1])

    def setup_gui(self):
        self.verticalLayout.addWidget(self.figure)
        self.pushButtonGo.clicked.connect(self.update)
        self.pushButtonAdvance.clicked.connect(self.advance)
        self.pushButtonSet.clicked.connect(self.setopts)
        self.pushButtonSpikes.clicked.connect(self.open_spike_dialog)
        self.pushButtonSave.clicked.connect(self.save_image)
        self.sstglabel = qtgui.QLabel(self)
        self.statusBar().addWidget(self.sstglabel)
        min_len = options['yn_min_ms']
        max_len = options['yn_max_ms']
        self.spinBoxYNirMin.setValue(min_len)
        self.spinBoxYNirMax.setValue(max_len)

    def init_h5man(self):
        # cands = glob('CSC*_ds.h5')
        cands = []
        if not len(cands):
            cands = glob('*_ds.h5')
        self.h5man = H5Manager(cands)

        for chn in self.h5man.chs:
            action = self.menuChannels.addAction(chn)
            action.setCheckable(True)
            action.triggered.connect(self.setch)

        debug('Available channels: {}'.format(self.h5man.chs))
        for a in self.actionsdir:
            a.triggered.connect(self.set_traces)

        # self.one_ms = 1./self.h5man.timestep/self.h5man.q

    def set_traces(self):
        traces = []
        for a, s in self.actionsdir.items():
            if a.isChecked():
                traces.append(s)
        self.traces = traces

        # self.yn_min_samp = self.spinBoxYNirMin.value() * self.one_ms
        # self.yn_max_samp = self.spinBoxYNirMax.value() * self.one_ms

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

    def plotit(self, start, nblocks):
        # try to deal with references here, later
        for ich, ch in enumerate(self.checked_channels):
            ioff = self.offset * ich
            # self.plot_traces(ch, start_time, stop_time, ioff)

            start_ch = self.h5man.translate(ch, start)
            stop_ch = start_ch + self.h5man.translate(ch, nblocks)
            d, adbitvolts = self.h5man.get_data(ch, start_ch, stop_ch,
                                                self.traces)
            data = d * adbitvolts
            time = self.h5man.get_time(ch, start_ch, stop_ch)
            self.ax.plot(time, data + ioff, 'darkblue', lw=1)

        self.ax.set_xlabel('time')
        self.ax.set_xlim((time[0], time[-1]))

           # print('Plotting {} seconds of data'.format((time[-1] - time[0])/1e3))
            # mpl.plot(time, (d - ref) * adbitvolts + 100*i, 'darkblue')
     
            # if self.actionShow_SWR_boxes.isChecked():
            #    self.plot_swr_boxes(ch, start, stop, ioff, ctime)

            # if self.actionShow_spikes.isChecked():
            #    self.plot_spikes(ch, ioff)

            # self.ax.text(ctime[0], ioff, ch, backgroundcolor='#EEEEEE')

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
        if not len(self.checked_channels):
            return
        if self.ax is None:
            self.ax = self.figure.fig.add_subplot(gs[0])
        # time = self.h5man.get_time(start, stop)
        # self.current_start_time = time[0]
        # self.current_stop_time = time[-1]
        # ctime = self.sleepstg.convert_time(time/1000)
        # ctime = time
        self.ax.cla()
        self.ax.set_ylabel(u'µV')
        self.set_traces()

        self.plotit(self.start, self.recs)

        if self.use_date:
            sstgnow = self.sleepstg.get_sleepstage(ctime[0], ctime[-1])
            self.sstglabel.setText(sstgnow)
            self.ax.xaxis.set_major_locator(self.locator)
            self.ax.xaxis.set_major_formatter(self.formatter)

        if self.ylim is not None:
            if self.ylim == (0, 0):
                self.ax.set_ylim((-200,
                                  len(self.checked_channels) * self.offset))
            else:
                self.ax.set_ylim(self.ylim)

        self.figure.draw()

    def advance(self):

        if not self.readlineEdits():
            return
        self.lineEditStart.setText(str(self.start + self.recs))
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
