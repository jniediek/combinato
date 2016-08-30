# JN 2016-08-26

"""
Converts refscheme.mat to refscheme.csv
The format of refscheme.csv is 
file_name;ref_file_name
"""

from __future__ import division, print_function, absolute_import
import csv
import os
from scipy.io import loadmat
from argparse import ArgumentParser
OUTFNAME = 'refscheme.csv'

def convert(fname_in):
    refscheme = loadmat(fname_in)['refscheme'][0].ravel()
    lines = []

    for i in range(len(refscheme)):
        fname_csc = 'CSC{}.ncs'.format(i + 1)
        fname_csc_ref = 'CSC{}.ncs'.format(refscheme[i][0])
        lines.append((fname_csc, fname_csc_ref))

    return lines


def main():
    parser = ArgumentParser()
    parser.add_argument('infile', nargs=1)
    args = parser.parse_args()
    
    if os.path.isfile(OUTFNAME):
        print('File exists, not writing')
    else:
        lines = convert(args.infile[0])
        with open(OUTFNAME, 'w') as fid:
            writer = csv.writer(fid, delimiter=';')
            writer.writerows(lines)

if __name__ == "__main__":
    main()
