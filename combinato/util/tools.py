"""
collection of helper functions
"""
from __future__ import print_function, division, absolute_import
import os
from glob import glob
from collections import defaultdict
import tables
from .. import NcsFile

def check_sorted(channel_dirname):
    """
    check how many 'sorted_...' folder there are
    """
    pattern = os.path.join(channel_dirname, 'sort_???_?????_*')
    return len(glob(pattern))

def spike_count_h5f(fname):
    """
    return number of positive/negative spikes in h5file
    """
    fid = tables.open_file(fname, 'r')
    try:
        n_pos = fid.root.pos.spikes.shape[0]
    except tables.NoSuchNodeError:
        n_pos = 0
    try:
        n_neg = fid.root.neg.spikes.shape[0]
    except tables.NoSuchNodeError:
        n_neg = 0

    fid.close()

    if n_pos + n_neg > 0:
        ch_extracted = True
    else:
        ch_extracted = False

    return ch_extracted, n_pos, n_neg


def check_status(channel_fname):
    """
    check whether channel is extracted/sorted
    """
    channel_dirname = os.path.splitext(channel_fname)[0]
    if os.path.isdir(channel_dirname):
        h5fname = os.path.join(channel_dirname,
                               'data_' + channel_dirname + '.h5')
        if os.path.exists(h5fname):
            ch_extracted, n_pos, n_neg = spike_count_h5f(h5fname)
            n_sorted = check_sorted(channel_dirname)
        else:
            h5fname = None
            ch_extracted = False
            n_pos = n_neg = n_sorted = 0
    else:
        h5fname = None
        ch_extracted = False
        n_pos = n_neg = n_sorted = 0

    return ch_extracted, n_pos, n_neg, n_sorted, h5fname


def get_channels(path, from_h5files=False):
    """
    simply finds the ncs files that are big enough
    """
    def h5fname2channel(h5fname):
            """
            transform h5filename to channel name
            It's a hack....
            """
            dirname = os.path.dirname(h5fname)
            basename = os.path.basename(dirname)
            cand = os.path.join(basename, basename + '.ncs')
            if os.path.exists(cand):
                return cand
            else:
                print('{} not found!'.format(cand))

    ret = {}

    if from_h5files:
        chs = [h5fname2channel(name) for name in h5files(path)]
    else:
        chs = glob(os.path.join(path, '*.ncs'))

    for chan in chs:
        statr = os.stat(chan)
        if statr.st_size > 16 * 1024:
            fid = NcsFile(chan)
            name = fid.header['AcqEntName']
            ret[name] = os.path.basename(chan)
    return ret


def get_regions(path):

    channels = glob(os.path.join(path, 'CSC*.ncs'))
    regions = defaultdict(list)

    for ch in channels:
        statr = os.stat(ch)
        if statr.st_size > 16 * 1024:
            fh = NcsFile(ch)

            name = fh.header['AcqEntName']
            try:
                int(name[-1])
                name = name[:-1]
            except ValueError:
                if name[-4:] == '_Ref':
                    name = name[:-4]
                else:
                    print('Unknown Region: ' + name[-4:])
            
            regions[name].append(ch)

    for name in regions:
        regions[name] = sorted(regions[name])
    return regions


def h5files(path):
    """
    highly specific tool to find all relevant h5 files
    """
    channel_dirs = glob(os.path.join(path, 'CSC?'))
    channel_dirs += glob(os.path.join(path, 'CSC??'))

    ret = []
    for chd in channel_dirs:
        basename = os.path.basename(chd)
        h5cand = os.path.join(chd, 'data_{}.h5'.format(basename))
        if os.path.exists(h5cand):
            if os.stat(h5cand).st_size > 0:
                ret.append(h5cand)

    return sorted(ret)
