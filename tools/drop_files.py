#!/usr/bin/env python3
# JN 2015-06-08

"""
mark all clusters in a channel as artifacts
"""
from __future__ import print_function, division
import os
import tables
from combinato import TYPE_ART, TYPE_NO


def make_artifact(h5fname):
    """
    mark the artifacts
    """
    print('Setting all classes in {} to Artifact'.format(h5fname))
    fid = tables.open_file(h5fname, 'r+')
    types = fid.root.types[:].copy()
    idx = types[:, 1] != TYPE_NO
    if idx.any():
        types[idx, 1] = TYPE_ART
    fid.root.types[:] = types

    fid.close()


def main():
    """
    just the main function
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--dropfile', nargs=1, required=True)
    parser.add_argument('--label', nargs=1, required=True)

    args = parser.parse_args()

    dropfname = args.dropfile[0]
    label = args.label[0]

    # sign = 'neg' if 'neg' in label else 'pos'

    with open(dropfname, 'r') as fid:
        fnames = [os.path.dirname(line.strip()) for line in fid.readlines()]

    drop_args = []
    for dirname in fnames:
        sortname = os.path.join(dirname, label, 'sort_cat.h5')
        if os.path.exists(sortname):
            drop_args.append(sortname)

    map(make_artifact, drop_args)

if __name__ == "__main__":
    main()
