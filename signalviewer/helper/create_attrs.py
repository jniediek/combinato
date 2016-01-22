#!/usr/bin/env python
# -*- coding: utf-8 -*-
# JN 2016-01-22
"""
Create a csv file containing downsampling information from all channels
"""

from __future__ import print_function, division, absolute_import
import tables
import csv

FNAME_OUT = 'h5meta.txt'


def to_file(msg, outname):
    """
    write h5information to file
    """

    with open(outname, 'w') as fid:
        writer = csv.writer(fid, delimiter=';')
        writer.writerows(msg)
    fid.close()


def make_attrs(h5files):
    """
    read the information
    """
    msgs = []

    for fname in h5files:
        fid = tables.open_file(fname, 'r')
        attrs = fid.root.data.rawdata.attrs
        msg = [fname[:-6],
               attrs.AcqEntName.decode('utf-8'),
               attrs.ADBitVolts * 1e6,
               attrs.Q,
               attrs.timestep * 1e6]
        msgs.append(msg)

        fid.close()

    return msgs


def main():
    """
    main function
    """
    from glob import glob
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('fnames', nargs='*')
    args = parser.parse_args()

    if not args.fnames:
        fnames = sorted(glob('*ds.h5'))
    else:
        fnames = args.fnames

    msg = make_attrs(fnames)
    to_file(msg, FNAME_OUT)


if __name__ == "__main__":
    main()
