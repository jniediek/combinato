# JN 2016-02-12
"""
create channel_names.csv
"""
from __future__ import division, print_function
import os
import sys
import csv
from combinato import NcsFile


FNAME_OUT = "channel_names.csv"


def main(fnames):
    """
    for each file in fnames, get entity name
    write everything to a csv file
    """
    fnames.sort()
    out_data = list()

    for name in fnames:
        fid = NcsFile(name)
        label = os.path.splitext(name)[0]
        entity = fid.header['AcqEntName']
        out_data.append((label, entity))

    with open(FNAME_OUT, 'w') as fid:
        csv_writer = csv.writer(fid, delimiter=';')
        csv_writer.writerows(out_data)


if __name__ == "__main__":
    main(sys.argv[1:])
