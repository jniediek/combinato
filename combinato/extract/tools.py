"""
reading and writing data
"""
# pylint: disable=E1101
from __future__ import absolute_import, print_function, division
import os
import numpy as np
import tables
from .. import NcsFile, DefaultFilter

from scipy.io import loadmat

SAMPLES_PER_REC = 512
DEFAULT_MAT_SR = 24000

def read_matfile(fname):
    """
    read data from a matfile
    """
    data = loadmat(fname)

    try:
        sr = data['sr'].ravel()[0]
        insert = 'stored'
    except KeyError:
        sr = DEFAULT_MAT_SR
        insert = 'default'

    print('Using ' + insert + ' sampling rate ({} kHz)'.format(sr/1000.))
    ts = 1/sr
    fdata = data['data'].ravel()
    atimes = np.linspace(0, fdata.shape[0]/(sr/1000), fdata.shape[0])
    # print(atimes.shape, fdata.shape)
    # print(ts)

    return fdata, atimes, ts


class ExtractNcsFile(object):
    """
    reads data from ncs file
    """

    def __init__(self, fname, ref_fname=None):
        self.fname = fname
        self.ncs_file = NcsFile(fname)
        self.ref_file = ref_fname
        if ref_fname is not None:
            self.ref_file = NcsFile(ref_fname)

        stepus = self.ncs_file.timestep * 1e6

        self.timerange = np.arange(0,
                                   SAMPLES_PER_REC * stepus,
                                   stepus)

        self.filter = DefaultFilter(self.ncs_file.timestep)

    def read(self, start, stop):
        """
        read data from an ncs file
        """
        data, times = self.ncs_file.read(start, stop, 'both')
        fdata = np.array(data).astype(np.float32)
        fdata *= (1e6 * self.ncs_file.header['ADBitVolts'])

        if self.ref_file is not None:
            print('Reading reference data from {}'.
                format(self.ref_file.filename))
            ref_data = self.ref_file.read(start, stop, 'data')
            fref_data = np.array(ref_data).astype(np.float32)
            fref_data *= 1e6 * self.ref_file.header['ADBitVolts']
            fdata -= fref_data

        expected_length = round((fdata.shape[0] - SAMPLES_PER_REC) *
                                (self.ncs_file.timestep * 1e6))

        err = expected_length - times[-1] + times[0]
        if err != 0:
            print("Timestep mismatch in {}"
                  " between records {} and {}: {:.1f} ms"
                  .format(self.fname, start, stop, err/1e3))

        atimes = np.hstack([t + self.timerange for t in times])/1e3
        # MUST NOT USE dictionaries here, because they would persist in memory
        return (fdata, atimes, self.ncs_file.timestep)


class OutFile(object):
    """
    write out file to hdf5 tables
    """
    def __init__(self, name, fname, spoints=64, destination=''):

        dirname = os.path.join(destination, name)
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
        fname = os.path.join(dirname, fname)
        f = tables.open_file(fname, 'w')
        f.create_group('/', 'pos', 'positive spikes')
        f.create_group('/', 'neg', 'negative spikes')

        for sign in ('pos', 'neg'):
            f.create_earray('/' + sign, 'spikes',
                           tables.Float32Atom(), (0, spoints))
            f.create_earray('/' + sign, 'times', tables.FloatAtom(), (0,))

        f.create_earray('/', 'thr', tables.FloatAtom(), (0, 3))

        self.f = f
        print('Initialized ' + fname)

    def write(self, data):
        r = self.f.root
        posspikes = data[0][0]
        postimes = data[0][1]
        negspikes = data[1][0]
        negtimes = data[1][1]

        if len(posspikes):
            r.pos.spikes.append(posspikes)
            r.pos.times.append(postimes)
        if len(negspikes):
            r.neg.spikes.append(negspikes)
            r.neg.times.append(negtimes)

        # threshold data
        r.thr.append(data[2])

        self.f.flush()

    def close(self):
        self.f.close()
