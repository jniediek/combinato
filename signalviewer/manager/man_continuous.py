# -*- coding: utf-8 -*-
# JN 2016-01-12

from __future__ import print_function, division, absolute_import
import os
import tables
import numpy as np
import csv
from .man_spikes import SpikeManager
from .tools import expandts, debug


class H5Manager(object):
    def __init__(self, files):
        self.timesteps = {}
        self.qs = {}
        self.entnames = {}
        self.bitvolts = {}
        self.fid = {}
        self.spm = None

        self.init_meta()
        for fname in files:
            fid = tables.open_file(fname, 'r')
            key = fname[:-6]
            if key in self.entnames:
                entname = self.entnames[key]
                self.fid[entname] = fid
        self.chs = sorted(self.fid.keys())
        if not len(self.chs):
            raise(ValueError('No channels found'))

        self.infoch = self.fid[self.chs[0]]

    def init_spikes(self, sign, label):
        self.spm = SpikeManager()
        for key, entname in self.entnames.items():
            self.spm.check_add(key, entname)

    def __del__(self):
        if hasattr(self, 'spm'):
            del self.spm
        if hasattr(self, 'fid'):
            for fid in self.fid.values():
                fid.close()

    def init_meta(self):
        if not os.path.exists('h5meta.txt'):
            raise(ValueError('H5 Meta file not found'))
            return

        with open('h5meta.txt', 'r') as fid:
            reader = csv.reader(fid, delimiter=';')
            metad = list(reader)

        for flds in metad:
            print(flds)

            key = flds[0]
            entname = flds[1]
            adbitvolts = float(flds[2])
            self.entnames[key] = entname
            self.bitvolts[entname] = adbitvolts
            self.qs[entname] = int(flds[3])
            self.timesteps[entname] = float(flds[4])/1e3

        print(self.entnames, self.bitvolts, self.qs, self.timesteps)

    def _mod_times(self, q, start, stop):
        """
        helper function for time stamp conversion
        """
        start *= q
        stop *= q
        tstart = start/512
        tstop = stop/512 + 1

        return tstart, tstop

    def get_time(self, ch, start, stop):
        q = self.qs[ch]
        ts = self.timesteps[ch]
        tstart, tstop = self._mod_times(q, start, stop)
        obj = self.fid[ch]
        timeraw = obj.root.time[tstart:tstop]
        tar = np.array(timeraw, 'float64') / 1000
        time = expandts(tar, ts, q)[:stop-start]
        assert(time.shape[0] == (stop - start))

        return time

    def get_data(self, ch, start, stop, traces=[]):
        adbitvolts = self.bitvolts[ch]
        # make it an array of columns here
        temp = []
        print(self.fid.keys())
        obj = self.fid[ch]
        for trace in traces:
            try:
                temp_d = obj.get_node('/data', trace)[start:stop]
                temp.append(temp_d)
            except tables.NoSuchNodeError as error:
                print(error)
        data = np.hstack(temp)
        return data, adbitvolts


def test():
    """
    simple test function
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('fnames', nargs='+')
    args = parser.parse_args()
    h5man = H5Manager(args.fnames)
    import matplotlib.pyplot as mpl
    d, adbitvolts = h5man.get_data('C3', 0, 10000, ['rawdata', 'filtered'])
    time = h5man.get_time('C3', 0, 10000)
    print('Plotting {} seconds of data'.format((time[-1] - time[0])/1e3))
    mpl.plot(time, d * adbitvolts)
    mpl.show()

    del h5man
