# encoding: utf-8
# JN 2014-12-27
# script to concatenate spikes from various h5 files
# useful for interrupted recording sessions
# JN 2014-12-29: script needs to be tested, programmed in train...
"""
at the moment, this script needs to be adjusted for every single use case
"""

from __future__ import print_function, division, absolute_import
import os
import tables
import glob

SIGNS = ('pos', 'neg')
PATTERN = ''
OUT = ''

def get_h5_fnames(folders):
    """
    make a list of files to unify from
    """
    ret = {}
    for folder in folders:
        for csc in range(1, 97):
            csccand = 'CSC' + str(csc)
            candname = os.path.join(folder, csccand,
                                    'data_' + csccand + '.h5')
            if os.path.exists(candname):
                if not csccand in ret:
                    ret[csccand] = [candname]
                else:
                    ret[csccand].append(candname)

    return ret


def count_spikes(in_fnames):
    """
    count spikes
    """
    num_pos = 0
    num_neg = 0
    nsamp = None

    for h5file in in_fnames:

        fid = tables.open_file(h5file, 'r')
        num_pos += fid.root.pos.times.shape[0]
        num_neg += fid.root.neg.times.shape[0]
        # might be a problem if no spikes:
        if (nsamp is None) and num_pos:
            nsamp = fid.root.pos.spikes.shape[1]
        fid.close()
    return num_pos, num_neg, nsamp



def unify_channel(out_fname, in_fnames):
    """
    do unification for one channel
    """

    # find total number of spikes
    num_pos, num_neg, nsamp = count_spikes(in_fnames)
    print('Positive: {}, Negative: {}'.format(num_pos, num_neg))
    print('opening ' + out_fname)

    outfile = tables.open_file(out_fname, 'w')

    for sign, nspk in zip(SIGNS, (num_pos, num_neg)):
        outfile.create_group('/', sign)
        outfile.create_array('/' + sign, 'times',
                             atom=tables.Float64Atom(), shape=(nspk, ))
        outfile.create_array('/' + sign, 'spikes',
                             atom=tables.Float32Atom(), shape=(nspk, nsamp))

    start = {}
    stop = {}

    # main loop
    for sign in SIGNS:
        start[sign] = 0

    for h5file in in_fnames:
        fid = tables.open_file(h5file, 'r')

        for sign in SIGNS:
            # times
            data = fid.get_node('/' + sign + '/times')
            stop[sign] = start[sign] + data.shape[0]
            out = outfile.get_node('/' + sign + '/times')
            out[start[sign]:stop[sign]] = data[:]

            data = fid.get_node('/' + sign + '/spikes')
            out = outfile.get_node('/' + sign + '/spikes')
            out[start[sign]:stop[sign]] = data[:]

            start[sign] = stop[sign]

        fid.close()

    outfile.close()


def unify_h5(folders, outfolder):
    """
    go through folders, read in h5 spikes and save to outfolder
    """
    if not os.path.exists(outfolder):
        os.mkdir(outfolder)

    jobs = get_h5_fnames(folders)
    sorted_keys = sorted(jobs.keys())

    for key in sorted_keys:
        print(key)
        # prepare global file
        out_csc_folder = os.path.join(outfolder, key)
        if not os.path.exists(out_csc_folder):
            os.mkdir(out_csc_folder)
        out_fname = os.path.join(out_csc_folder, 'data_{}.h5'.format(key))
        unify_channel(out_fname, jobs[key])


if __name__ == "__main__":
    DIRS = glob.glob(PATTERN)
    print('Working in {}'.format(DIRS))
    unify_h5(DIRS, OUT)
