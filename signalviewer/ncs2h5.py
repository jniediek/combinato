# -*- coding: utf-8 -*-
# JN 2016-01-12

"""
Downsample ncs files and save as h5
"""
from __future__ import print_function, division, absolute_import
import os

from argparse import ArgumentParser
from multiprocessing import Pool
from time import time
import scipy.signal
from .helper.helper import initfile, make_blocks
from combinato import NcsFile

DEBUG = True


def downsampling(ncsfname, h5fname, Q=16):
    """
    Main routine for downsampling
    """
    ncsf = NcsFile(ncsfname)
    chname = ncsf.header['AcqEntName']
    h5f = initfile(h5fname, ncsf, Q)
    nrec = ncsf.num_recs
    ds_order = 8
    ts = ncsf.timestep

    if DEBUG:
        print('{} has {} records'.format(ncsfname, nrec))

    blocks = make_blocks(nrec, min(100000, nrec))
    if Q > 1:
        # design filter for lowpass filtering before downsampling
        # use 80% of the Nyquist frequency as cutoff
        b_down, a_down = scipy.signal.cheby1(ds_order, .05, 0.8/Q)

    for start, stop in blocks:
        if DEBUG:
            print('Filtering {} {}-{}'.format(chname, start, stop))
        data, ts = ncsf.read(start, stop, mode='both')
        h5f.root.time.append(ts)

        if Q > 1:
            # Warning!
            # scipy.signal.decimate uses lfilt,
            # so the decimated signal has a phase shift
            # for this reason, we use 
            ds_data = scipy.signal.filtfilt(b_down, a_down, data)[::Q]
        else:
            ds_data = data

        h5f.root.data.rawdata.append(ds_data)

        # if you would like to create other traces
        # (e.g. filtered versions of the data), do it here
        # by calling appropriate functions

        h5f.flush()

    h5f.close()


def helper(job):
    """
    used because Pool.map supports only 1-argument functions
    """
    fname = job[0]
    Q = job[1]
    outfolder = job[2]
    h5fname = fname[:-4] + '_ds.h5'
    if outfolder is not None:
        h5fname = os.path.join(outfolder, h5fname)
    downsampling(fname, h5fname, Q)


def downsample_main(fnames, q, outfolder=None, ncores=4):
    """
    Get the arguments and work with them
    """
    cands = []
    for cand in fnames:
        if os.path.exists(cand):
            if os.stat(cand).st_size > 16 * 1024:
                cands.append(cand)

    if DEBUG:
        print('Working on: {}'.format(cands))

        jobs = zip(cands, [q] * len(cands), [outfolder] * len(cands))
    t1 = time()
    if ncores > 1:
        p = Pool(ncores)
        p.map(helper, jobs)
    else:
        for job in jobs:
            helper(job)

    if DEBUG:
        td = time() - t1
        print('Took {:.1f} seconds'.format(td))


def main():
    """
    Argument parsing as usual
    """
    parser = ArgumentParser('css-ncs-downsample',
                            epilog='Johannes Niediek (jonied@posteo.de)')
    parser.add_argument('fname', nargs='+')
    parser.add_argument('--ncores', type=int, default=4)
    parser.add_argument('--q', type=int, default=16)
    parser.add_argument('--outfolder', nargs=1)
    args = parser.parse_args()
    fnames = args.fname

    if args.outfolder:
        outfolder = args.outfolder[0]
    else:
        outfolder = None

    downsample_main(fnames, args.q, outfolder, args.ncores)
