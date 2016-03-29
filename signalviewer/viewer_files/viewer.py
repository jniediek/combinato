#!env /usr/bin/python
# -*- coding: utf-8 -*-
# JN 2016-01-12 ncs data viewer
from __future__ import division, print_function, absolute_import
import sys
import os
from glob import glob
from time import time
from collections import defaultdict
# import datetime
import numpy as np

import PyQt4.QtGui as qtgui

from matplotlib.gridspec import GridSpec
from matplotlib.dates import AutoDateLocator, num2date, date2num
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Rectangle

from .ui_viewer import Ui_MainWindow

from .sWidgets import MplCanvas
from .. import H5Manager, debug, options, DATE_FNAME, parse_datetime
from .spikes import SpikeView

stylesheet = 'QListView:focus { background-color: rgb(240, 255, 255)}'

COLORS = ['darkblue', 'red', 'magenta', 'black', 'green']
gs = GridSpec(1, 1, top=.95, bottom=.05, left=.05, right=.95)
DEBUG = True

sleepdtype = np.dtype([('starttime', float),
                       ('stoptime', float),
                       ('stage', 'S1')])


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
        self.ylim = (0, 0)
        self.lfpfactor = 1
        self.sleepstages = []
        self.ts_start_nlx = None
        self.ts_start_mpl = None
        self.use_date = False
        self.montage = None
        self.positions = None
        self.locator = AutoDateLocator()
        self.formatter = FuncFormatter(fmtfunc)
        self.offset = 150
        self.setup_gui()
        self.init_traces()
        t1 = time()
        self.init_h5man()
        dt = time() - t1
        debug('Init h5 took {:.1f} s'.format(dt))
        self.setopts()
        self.labelFolder.setText(os.path.split(os.getcwd())[1])
        self.init_montages()
        self.init_realtime()
        self.display_sleep = None
        if os.path.exists('sleepstages_clean.npy'):
            self.display_sleep = np.load('sleepstages_clean.npy')
        elif os.path.exists('sleepstages.npy'):
            self.display_sleep = np.load('sleepstages.npy')

    def init_traces(self):
        """
        Read trace names from file
        Each trace has a display scale factor,
        which we store in the dictionary self.all_traces
        """
        fname_trace = 'traces.txt'
        if os.path.exists(fname_trace):
            self.all_traces = dict()
            with open(fname_trace, 'r') as fid:
                lines = [line.strip() for line in fid.readlines()]

            for line in lines:
                fields = line.split(' ')
                self.all_traces[fields[0]] = int(fields[1])
        else:
            self.all_traces = {'rawdata': 1}
        debug(self.all_traces)
        for trace in sorted(self.all_traces.keys()):
            action = self.menuTraces.addAction(trace)
            action.setCheckable(True)
            if trace == 'rawdata':
                action.setChecked(True)

    def setup_gui(self):
        self.verticalLayout.addWidget(self.figure)
        self.addAction(self.actionBack)
        self.addAction(self.actionAdvance)
        self.addAction(self.actionSampUp)
        self.addAction(self.actionSampDown)
        self.pushButtonGo.clicked.connect(self.update)
        self.pushButtonAdvance.clicked.connect(self.advance)
        self.pushButtonBack.clicked.connect(self.back)
        self.pushButtonSet.clicked.connect(self.setopts)
        self.pushButtonSpikes.clicked.connect(self.open_spike_dialog)
        self.pushButtonSave.clicked.connect(self.save_image)
        self.pushButtonSampUp.clicked.connect(self.samp_up)
        self.pushButtonSampDown.clicked.connect(self.samp_down)
        self.actionBack.triggered.connect(self.back)
        self.actionAdvance.triggered.connect(self.advance)
        self.actionSampUp.triggered.connect(self.samp_up)
        self.actionSampDown.triggered.connect(self.samp_down)
        self.sstglabel = qtgui.QLabel(self)
        self.statusBar().addWidget(self.sstglabel)
        pairs = ((self.action_W, self.set_w),
                 (self.action_N1, self.set_n1),
                 (self.action_N2, self.set_n2),
                 (self.action_N3, self.set_n3),
                 (self.action_R, self.set_r),
                 (self.action_Save_to_file, self.save_sleepstages))
        for action, func in pairs:
            action.triggered.connect(func)

    def init_h5man(self):
        cands = glob('*_ds.h5')
        self.h5man = H5Manager(cands)

        for chn in self.h5man.chs:
            action = self.menuChannels.addAction(chn)
            action.setCheckable(True)
            action.triggered.connect(self.setch)

        debug('Available channels: {}'.format(self.h5man.chs))

    def init_realtime(self):
        """
        try to find the real date and time of the recording
        """
        if not os.path.exists(DATE_FNAME):
            return

        else:
            ts_start_nlx, ts_start_obj = parse_datetime(DATE_FNAME)

        ts_start_mpl = date2num(ts_start_obj)

        self.ts_start_nlx = ts_start_nlx
        self.ts_start_mpl = ts_start_mpl
        if DEBUG:
            print(self.ts_start_nlx, self.ts_start_mpl)

    def init_montages(self):
        """
        Make a list of montage files
        """
        cands = glob('*_montage.txt')
        for cand in cands:
            name = cand[:-4]
            action = self.menuRefs.addAction(name)
            action.setCheckable(True)
            action.triggered.connect(self.read_montage)

    def read_montage(self):
        """
        read a montage from file
        """
        checked_montages = [a for a in self.menuRefs.children()
                            if a.isChecked()]
        fnames = [str(a.text()) + '.txt' for a in checked_montages]
        all_lines = []
        for fname in fnames:
            print(fname)
            with open(fname, 'r') as fid:
                lines = [line.strip() for line in fid.readlines()]
            all_lines += lines

        self.set_montage(all_lines)

    def set_montage(self, lines):
        """
        Set a montage from channel name lines
        """
        montage = defaultdict(list)
        positions = dict()
        for il, line in enumerate(lines):
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
        self.n_disp_chs = len(lines)

    def set_traces(self):
        """
        simply list the names of the checked traces
        """
        self.checked_traces = [str(act.text())
                               for act in self.menuTraces.children()
                               if act.isChecked()]

    def setch(self):
        checked_actions = [a for a in self.menuChannels.children()
                           if a.isChecked()]
        checked_channels = [str(a.text()) for a in checked_actions]
        self.set_montage(checked_channels)

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

    def convert_time(self, time, internal=False):
        """
        this will be used to convert to real times etc
        """
        if internal:
            return time

        if self.use_date:
            time = (time - self.ts_start_nlx)/(1000*24*60*60)
            time += self.ts_start_mpl
        else:
            time /= 1000

        return time

    def plotit(self, start, nblocks):
        # try to deal with references here, later
        allstart = 0
        allstop = np.inf

        if self.montage is None:
            return

        # iterate over all references
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
                                                        self.checked_traces)
                ref_data = ref_d * adbitvolts
                time = self.h5man.get_time(ref_ch, start_ch_ref,
                                           stop_ch_ref)

            # iterate over all channels with that reference
            for ch in self.montage[ref_ch]:
                print('Updating {}-{}'.format(ch, ref_ch))
                start_ch = self.h5man.translate(ch, start)
                stop_ch = start_ch + self.h5man.translate(ch, nblocks)

                if ref_ch != 0:
                    assert start_ch == start_ch_ref
                    assert stop_ch == stop_ch_ref
                d, adbitvolts = self.h5man.get_data(ch, start_ch, stop_ch,
                                                    self.checked_traces)

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

                for irow, (row, name) in enumerate(
                        zip(data, self.checked_traces)):
                    # multiply each trace by its factor
                    row *= self.all_traces[name]
                    self.ax.plot(plot_time, shift + row,
                                 COLORS[irow], lw=1)

                if ref_ch == 0:
                    label = ch
                else:
                    label = '{}-{}'.format(ch, ref_ch)
                self.ax.text(plot_time[0], shift, label,
                             backgroundcolor='w')

                if self.actionShowBoxes.isChecked():
                    self.plot_events(ch, start_ch, stop_ch, shift)

        if not self.use_date:
            self.ax.set_xlabel('seconds')

        plot_start, plot_stop = [self.convert_time(t)
                                 for t in (allstart, allstop)]
        self.ax.set_xlim((plot_start, plot_stop))

        self.allstart = allstart
        self.allstop = allstop

    def plot_events(self, ch, start_ch, stop_ch, shift):
        """
        Add boxes for detected events
        """
        for itr, trace in enumerate(self.checked_traces):
            events = self.h5man.get_events(ch, start_ch, stop_ch,
                                           trace)
            print('Plotting {} events'.format(len(events)))
            for iev, event in enumerate(events):
                if event[0] == event[1]:
                    continue
                times = self.h5man.get_time(ch, event[0], event[1])
                start_ev, stop_ev = [self.convert_time(t)
                                     for t in (times[0], times[-1])]
                rec = Rectangle((start_ev, shift - self.offset/2),
                                stop_ev - start_ev,
                                self.offset,
                                edgecolor='none',
                                alpha=options['alpha'],
                                facecolor=COLORS[itr])
                self.ax.add_artist(rec)

#    def plot_spikes(self, ch, offset):
#        self.h5man.spm.set_beg_end(ch,
#                                   self.current_start_time,
#                                   self.current_stop_time)
#        ptimes = []
#        if ch in self.h5man.spm.sortedfiles:
#            print('getting sorted data!')
#            clu = self.h5man.spm.get_sorted_data(ch, self.current_start_time,
#                                                 self.current_stop_time)
#
#            for c, cl in clu.items():
#                print(c, cl['times'].shape[0])
#                if len(cl['times']):
#                    ptimes.append(self.sleepstg.convert_time(cl['times']/1000))
#                    print (self.current_start_time,
#                           self.current_stop_time, cl['times'][0])
#
#        else:
#            sptimes = self.h5man.spm.get_sp_data(ch)
#            ptimes.append(self.sleepstg.convert_time(sptimes/1000))
#
#        color = 'brgymkkkkkkkkkkkkkk'
#        for i, cluster in enumerate(ptimes):
#            print(num2date(ptimes[0]))
#            y = offset * np.ones(len(cluster), 'int8')
#            self.ax.plot(cluster, y, color[i] + '|',
#                         ms=options['ms'], mew=options['mew'])

    def update(self):
        if not self.readlineEdits():
            return
        if self.montage is None:
            return
        if self.ax is None:
            self.ax = self.figure.fig.add_subplot(gs[0])
        self.ax.cla()
        self.ax.grid(True)
        self.ax.set_ylabel(u'µV')
        if self.actionUse_wall_time.isChecked():
            self.use_date = True
        else:
            self.use_date = False

        if self.use_date:
            self.ax.xaxis.set_major_locator(self.locator)
            self.ax.xaxis.set_major_formatter(self.formatter)

        self.set_traces()
        self.plotit(self.start, self.recs)

        if self.ylim is not None:
            if self.ylim == (0, 0):
                ylim = (-200, self.n_disp_chs * self.offset)
            else:
                ylim = self.ylim
            self.ax.set_ylim(ylim)
            self.ax.set_yticks(range(0, ylim[1] + 100, 100))
            self.ax.set_yticklabels([0, round(100/self.lfpfactor)])

        if self.display_sleep is not None:
            start, stop = [self.convert_time(time, internal=True)
                           for time in self.allstart, self.allstop]
            rel_idx = (self.display_sleep['stoptime'] >= start) &\
                      (self.display_sleep['starttime'] <= stop)
            for row in self.display_sleep[rel_idx]:
                print(row)
                rowstart = max(start, row[0])
                rowstop = min(stop, row[1])
                recstart, recstop = [self.convert_time(t)
                                     for t in (rowstart, rowstop)]
                rec = Rectangle((recstart, ylim[0]), recstop - recstart,
                                self.offset/2, facecolor='r', alpha=.5)
                self.ax.text(recstart, ylim[0]+self.offset/2, row[2],
                             fontsize=14, va='top', ha='left')
                self.ax.add_patch(rec)

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

        lfpperc = float(self.spinBoxLFPpercent.value())
        self.lfpfactor = lfpperc/100

        self.update()

    def open_spike_dialog(self):
        dialog = SpikeView(self)
        dialog.show()

    def samp_up(self):
        self.lineEditRecords.setText(str(self.recs * 2))
        self.update()

    def samp_down(self):
        self.lineEditRecords.setText(str(int(self.recs / 2)))
        self.update()

    def set_w(self):
        self.set_sleepstage('W')

    def set_n1(self):
        self.set_sleepstage('1')

    def set_n2(self):
        self.set_sleepstage('2')

    def set_n3(self):
        self.set_sleepstage('3')

    def set_r(self):
        self.set_sleepstage('R')

    def set_sleepstage(self, which):
        start, stop = [self.convert_time(time, internal=True)
                       for time in self.allstart, self.allstop]
        self.sleepstages.append((start, stop, which))
        self.advance()

    def save_sleepstages(self):
        """
        save sleepstages to file
        """
        data = np.array(self.sleepstages, sleepdtype)
        np.save('sleepstages.npy', data)


def main():
    app = qtgui.QApplication(sys.argv)
    w = SimpleViewer()
    w.show()
    app.exec_()

if __name__ == "__main__":
    main()
