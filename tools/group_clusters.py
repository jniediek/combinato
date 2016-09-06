# JN 2016-09-05
"""
create cluster groups in an existing sorting session
useful for testing purposes
"""

from __future__ import print_function, division

import os
from argparse import ArgumentParser
from combinato.cluster.create_groups import main as create_groups_main

def main():
    """
    parse arguments
    """
    parser = ArgumentParser()
    parser.add_argument('--read-only', default=False, action='store_true')
    parser.add_argument('--datafile', nargs=1, required=True)
    parser.add_argument('--sorting', nargs=1, required=True)

    args = parser.parse_args()

    datafile = args.datafile[0]
    sortingfile = os.path.join(args.sorting[0], 'sort_cat.h5')

    create_groups_main(datafile, sortingfile, args.read_only)

if __name__ == "__main__":
    main()
