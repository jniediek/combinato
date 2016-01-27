# -*- coding: utf-8 -*-
# JN 2016-01-12

from __future__ import print_function, division, absolute_import
import os
import csv
import glob
import numpy as np
import tables
from .man_spikes import SpikeManager
from .tools import expandts, debug
from .. import make_attrs

FNAME_H5META = 'h5meta.txt'


class H5Manager(object):
    """
    Backend for h5 files containing continuously sampled data
    """
    def __init__(self, files, modify=False, load_events=True):
        """
        Initialize with given files
        """
        self.timesteps = {}
        self.qs = {}
        self.entnames = {}
        self.bitvolts = {}
        self.fid = {}
        self.spm = None
        self.time_factors = {}
        self.events = {}
        self.modify = modify
        self.folder = os.path.dirname(files[0])
        self.init_meta()

        if modify:
            mode = 'r+'
        else:
            mode = 'r'

        # open the requested files
        for fname in files:
            fid = tables.open_file(fname, mode)
            key = os.path.basename(fname)[:-6]
            if key in self.entnames:
                entname = self.entnames[key]
                self.fid[entname] = fid

            # check if events exist
            if load_events:
                event_fname = os.path.join(self.folder, key + '_events.h5')
                if os.path.exists(event_fname):
                    debug('Loading ' + event_fname)
                    self.events[entname] = tables.open_file(event_fname, 'r')

        self.chs = sorted(self.fid.keys())
        if not len(self.chs):
            raise(ValueError('No channels found'))

    def __del__(self):
        """
        close the h5 files
        """
        if hasattr(self, 'spm'):
            del self.spm
        if hasattr(self, 'fid'):
            for fid in self.fid.values():
                fid.close()

    def init_spikes(self, sign, label):
        """
        initialize unsorted or sorted spike data
        """
        self.spm = SpikeManager()
        for key, entname in self.entnames.items():
            self.spm.check_add(key, entname)

    def init_meta(self):
        """
        initialize the meta information for all channels
        """
        if os.path.exists(os.path.join(self.folder, FNAME_H5META)):
            with open(FNAME_H5META, 'r') as fid:
                reader = csv.reader(fid, delimiter=';')
                metad = list(reader)
        else:
            cand = glob.glob(os.path.join(self.folder, '*_ds.h5'))
            metad = make_attrs(cand)
        effective_ts = {}

        for flds in metad:
            key = flds[0]
            entname = flds[1]
            adbitvolts = float(flds[2])
            self.entnames[key] = entname
            self.bitvolts[entname] = adbitvolts
            self.qs[entname] = int(flds[3])
            self.timesteps[entname] = float(flds[4])/1e3
            effective_ts[entname] = self.qs[entname] * self.timesteps[entname]

        # calculate the relative sampling rates
        min_effective_ts = min(effective_ts.values())
        for name, ts in effective_ts.items():
            rel = ts/min_effective_ts
            if rel - int(rel) > 1e-6:
                raise Warning("Relative sampling rates have to be integers")
            # for each channel, store the multiplication factor
            self.time_factors[name] = int(rel)

        debug((self.entnames, self.bitvolts, self.qs,
              self.timesteps))
        debug(self.time_factors)

    def _mod_times(self, q, start, stop):
        """
        helper function for time stamp conversion
        """
        start *= q
        stop *= q
        tstart = int(start/512)
        tstop = int(stop/512) + 1
        shift = int((start % 512)/q)
        if tstart > tstop:
            raise Warning('Time stamp conversion failure!')

        return tstart, tstop, shift

    def translate(self, ch, sample):
        """
        transform samples according to relative times
        """
        factor = self.time_factors[ch]
        return int(sample/factor)

    def get_time(self, ch, start, stop):
        q = self.qs[ch]
        ts = self.timesteps[ch]
        tstart, tstop, shift = self._mod_times(q, start, stop)
        obj = self.fid[ch]
        timeraw = obj.root.time[tstart:tstop+512/q]
        tar = np.array(timeraw, 'float64')/1000
        # time needs to be shifted
        time = expandts(tar, ts, q)[shift:stop-start+shift]
        print(time.shape)
        assert(time.shape[0] == (stop - start))

        return time

    def get_data(self, ch, start, stop, traces=[]):
        """
        read data
        """
        adbitvolts = self.bitvolts[ch]
        # make it an array of columns here
        temp = []
        # debug(self.fid.keys())
        obj = self.fid[ch]
        for trace in traces:
            try:
                temp_d = obj.get_node('/data', trace)[start:stop]
                temp.append(temp_d)
            except tables.NoSuchNodeError as error:
                debug(error)
        data = np.vstack(temp)
        print(data.shape)
        return data, adbitvolts

    def get_events(self, ch, start, stop, trace):
        """
        read events in the given window
        """
        if ch in self.events:
            obj = self.events[ch]
        else:
            return []

        try:
            # this is a bit unefficient because we just need
            # certain parts, but it's not easy to do better
            temp_d = obj.get_node('/', trace)[:, :]
        except tables.NoSuchNodeError:
            return []

        idx = (temp_d[:, 0] >= start) & (temp_d[:, 1] <= stop)
        return temp_d[idx, :]

    def add_trace(self, ch, trace_name):
        """
        add a trace
        """
        size = self.fid[ch].root.data.rawdata.shape[0]
        zeros = np.zeros(size, np.int16)
        if not self.modify:
            print('Cannot add trace because modify is False')
            return
        try:
            self.fid[ch].create_array('/data', trace_name, zeros)
        except tables.exceptions.NodeError as error:
            print(error)
            print('Not re-creating')


def test():
    """
    simple test function
    """
    from argparse import ArgumentParser
    import matplotlib.pyplot as mpl
    parser = ArgumentParser()
    parser.add_argument('fnames', nargs='+')
    args = parser.parse_args()
    h5man = H5Manager(args.fnames)
    chs = h5man.chs
    start = 10000
    nblocks = 20000

    # this is to test referencing
    ch = 'Cb1'
    start_ch = h5man.translate(ch, start)
    stop_ch = start_ch + h5man.translate(ch, nblocks)
    ref, adbitvolts = h5man.get_data(ch, start_ch, stop_ch,
                                     ['rawdata'])

    for i, ch in enumerate(chs):
        print(ch)
        start_ch = h5man.translate(ch, start)
        stop_ch = start_ch + h5man.translate(ch, nblocks)
        d, adbitvolts = h5man.get_data(ch, start_ch, stop_ch,
                                       ['rawdata'])
        time = h5man.get_time(ch, start_ch, stop_ch)
        print('Plotting {} seconds of data'.format((time[-1] - time[0])/1e3))
        mpl.plot(time, (d - ref) * adbitvolts + 100*i, 'darkblue')
        mpl.text(time[0], i*100, ch, backgroundcolor='w')
    mpl.show()

    del h5man
