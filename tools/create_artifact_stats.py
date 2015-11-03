# JN 2015-05-22

"""
creates artifact statistics for given channels
"""

from __future__ import print_function, absolute_import, division
import os
import sys
import pandas as pd
from combinato import SortingManagerGrouped, artifact_types

COLS = ["cscname", "hemisphere", "region", "wire", "n_spikes"]


def create_statistics(artifacts):
    """
    create artifact statistics
    """
    total = artifacts.shape[0]

    artids = [art['art_id'] for art in artifact_types]

    ret = [total]

    for aid in artids:
        ret.append((artifacts == aid).sum())

    return ret


def create_channel_list(fname):
    """
    read a list of ncs files and create a list of relevant h5 files
    """
    with open(fname, 'r') as fid:
        lines = [line.strip() for line in fid.readlines()]

    fid.close()

    cscnames = [name[:-4] for name in lines]

    h5files = []

    for cscname in cscnames:
        cand = os.path.join(cscname, 'data_{}.h5'.format(cscname))
        if os.path.exists(cand):
            h5files.append((cand, cscname))
        else:
            print('{} not found'.format(cand))

    return h5files


def loop_channels(channel_list, sign):
    """
    create artifact statistics
    """
    art_names = [art['name'] for art in artifact_types]
    local_cols = COLS + art_names
    iterator = range(len(art_names))
    res = []

    for h5file, cscname in channel_list:
        man = SortingManagerGrouped(h5file)
        artifacts = man.h5datafile.get_node('/' + sign, 'artifacts')[:]
        entity = man.header['AcqEntName']
        region = entity[1:-1]
        side = entity[0]
        wire = entity[-1]
        del man
        stat = create_statistics(artifacts)
        # stat[0] is the total count
        row = [str(cscname), str(side), str(region), int(wire), stat[0]]
        for i in iterator:
            row.append(stat[i+1])
        res.append(row)

    frame = pd.DataFrame(data=res, columns=local_cols)
    return frame


def main():
    """
    standard main function
    pass e.g. do_extract.txt as an argument
    """
    h5files = create_channel_list(sys.argv[1])
    frame = loop_channels(h5files, 'pos')
    outfname = 'artifact_stats.h5'
    frame.to_hdf(outfname, 'artifact_stats')

if __name__ == "__main__":
    main()
