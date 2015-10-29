# JN 2015-05-11

"""
small function to copy start of ncs file to folders
"""

from __future__ import print_function, division, absolute_import

import os
from argparse import ArgumentParser
from combinato.basics.nlxio import NCS_RECSIZE, NLX_OFFSET


def start_to_folder(ncsfname, destination=None):
    """
    read the header, write it to a folder
    """

    if destination is None:
        outfname = ncsfname[:-4]
        outpath = os.path.join(outfname, ncsfname)
    else:
        outpath  = os.path.join(destination, ncsfname)

    checkdir = os.path.dirname(outpath)
    if not os.path.exists(checkdir):
        print("No such folder: " + checkdir)
        return

    # read file and first two records

    with open(ncsfname, 'rb') as ncsfid:
        data = ncsfid.read(NLX_OFFSET + 2*NCS_RECSIZE)

    ncsfid.close()

    
    with open(outpath, 'wb') as outfid:
        outfid.write(data)

    outfid.close()

    print('Wrote {} bytes from {} to {}'.
        format(len(data), ncsfname, outpath))


def parse_args():
    parser = ArgumentParser(description='Copies the first 16 KB plus 2088 Bytes of'
                                        ' ncs files to a different directory.'
                                        ' If --destination is not given, each header is'
                                        ' copied to the subdirectory with the same name.',
                            epilog='Johannes Niediek (jonied@posteo.de)')
    parser.add_argument('--destination', nargs=1)
    parser.add_argument('--files', nargs='*', required=True)
    
    args = parser.parse_args()

    if args.destination:
        destination = args.destination[0]
    else:
        destination = None
    
    for ncsfname in args.files:
        start_to_folder(ncsfname, destination)


if __name__ == "__main__":
    parse_args()
