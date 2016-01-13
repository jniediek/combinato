# -*- coding: utf-8 -*-
# JN 2014-09-25
# create h5 file containing histogram of firing channels
# in time bins
# this is used to exclude bins with too many channels firing
# as they are likely to be artifacts

from __future__ import print_function, division
import os
import numpy as np
import tables
import time
from .. import NcsFile, h5files, get_regions

DEBUG = True
BIN_MS = 3 

def bincount(ts_beg, ts_end, files, sign='pos'):

    bins = np.arange(ts_beg, ts_end, BIN_MS)
    count = np.zeros(len(bins) - 1, 'uint16')
    nch = 0 # how many channels contribute?
    for i, fn in enumerate(files):
        times = times_from_file(fn, sign) 
        if len(times):
            nch += 1 
            count += (np.histogram(times, bins)[0] > 0)
            if DEBUG:
                print('Added {}/{}'.format(i + 1, len(files)))

    return count, bins, nch 


def _any_from_file(what, fname, sign='pos'):

    failed = False 
    try:
        h5file = tables.open_file(fname)
    except IOError as e:
        print(e.message + ' ' + fname)
        times = []
        failed = True 
   
    if not failed:
        try:
            times = h5file.get_node('/' + sign + '/times')
        except tables.exceptions.NoSuchNodeError as e:
            print(e.message + ' ' + fname)
            times = []
       
    if what == 'times':
        # allocating this array consumes around 1 ms in our case,
        # not worth optimizing
        ret = np.array(times) 
    elif what == 'nspk':
        ret = len(times)
    else:
        ret = None

    h5file.close()
    return ret


def nspk_from_file(fname, sign='pos'):
    """
    returns number of spikes from an h5file
    """
    return _any_from_file('nspk', fname, sign)


def times_from_file(fname, sign='pos'):
    """
    returns times from an h5file
    """
    return _any_from_file('times', fname, sign)



def write_bincount(folder):
    """
    get count for bin, save to file
    """
    outfname = 'concurrent_times.h5'

    if os.path.exists(outfname):
        raise IOError('File exists: ' + outfname)

    files = h5files(folder)
    if not len(files):
        raise ValueError('No spike data found in ' + folder)
        
    ncsfiles = get_regions(folder)
    ncsf = ncsfiles.values()[0][0]
    ncsfid = NcsFile(ncsf)
    ts_beg = float(ncsfid.read(0, 1, mode='timestamp'))/1000
    ts_end = float(ncsfid.read(ncsfid.num_recs-1, 
                               ncsfid.num_recs, 
                               mode='timestamp'))/1000

    count, bins, nch = bincount(ts_beg, ts_end, files)
    outfile = tables.open_file(outfname, 'w')
    outfile.create_array('/', 'count', count)
    outfile.root.count.attrs['nch'] = nch
    outfile.root.count.attrs['start'] = ts_beg
    outfile.root.count.attrs['stop'] = ts_end
    outfile.root.count.attrs['binms'] = BIN_MS 
    outfile.close()


def main():
    folder = os.getcwd()
    write_bincount(folder)
