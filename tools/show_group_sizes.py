# JN 2015-05-28

"""
convenience script to show how many groups there are in each channel
"""
from __future__ import print_function, division, absolute_import
import os
from combinato import Combinato, h5files


def main(sign, label):
    """
    show group sizes in h5files
    """
    files = h5files(os.getcwd())
    n_arti_total = 0
    for fname in files:
        man = Combinato(fname, sign, label)
        if not man.initialized:
            continue
        groups = man.get_groups(times=False, spikes=False)
        if 0 in groups.keys():
            n_unassigned = len(groups[0])
        if -1 in groups.keys():
            n_arti = len(groups[-1])
        else:
            n_arti = 0


        print('{} {} groups, {} artifacts'.
              format(os.path.basename(fname), len(groups), n_arti))

        n_arti_total += n_arti

    return n_arti_total


if __name__ == "__main__":
    ret = main('pos', 'sort_pos_joh')
    print('Total artifacts: {}'.format(ret))
