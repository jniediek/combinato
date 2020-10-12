#!/usr/bin/env python3
# JN 2016-05-17

"""
This script runs css-prepare, css-cluster, and css-combine in a row.
It does not use multi-processing, and it accepts a single file name only.

It is generally better to call the css-* scripts one after the other!
"""
from __future__ import print_function, absolute_import

import os 
from argparse import ArgumentParser

from combinato.cluster.prepare import main as prepare_main
from combinato.cluster.cluster import main as cluster_main
from combinato.cluster.concatenate import main as combine_main
from combinato.cluster.create_groups import main as groups_main


def main():
    parser = ArgumentParser('Simple script for clustering one datafile',
                            epilog='Johannes Niediek (jonied@posteo.de)')
    parser.add_argument('--datafile', nargs=1, required=True)
    parser.add_argument('--neg', default=False, action='store_true')
    parser.add_argument('--label', nargs=1, default=['simple'])

    args = parser.parse_args()

    sign = 'neg' if args.neg else 'pos'
    
    sessions = prepare_main(args.datafile, sign, 'index', 0,
                            None, 20000, args.label[0], False, False)

    if (sessions) :

        for name, sign, ses in sessions:
            cluster_main(name, ses, sign)

        label = 'sort_{}_{}'.format(sign, args.label[0])
        outfname = combine_main(args.datafile[0],
                                [os.path.basename(ses[2]) for ses in sessions],
                                label)

        groups_main(args.datafile[0], outfname)

    else :
        print("No spike sessions to sort.")



if __name__ == "__main__":
    main()
