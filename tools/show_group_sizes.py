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
    for fname in files:
        man = Combinato(fname, sign, label)
        if not man.initialized:
            continue
        groups = man.get_groups(times=False, spikes=False)
        print(os.path.basename(fname), len(groups))


if __name__ == "__main__":
    main('pos', 'sort_pos_joh')

