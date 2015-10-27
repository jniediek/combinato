from __future__ import division, print_function, absolute_import
import os
from argparse import ArgumentParser
from .mp_extract import mp_extract
from .. import NcsFile


def get_nrecs(filename):
    fid = NcsFile(filename)
    return fid.num_recs


def main():
    """standard main function"""
    # standard options
    nWorkers = 8
    blocksize = 10000

    parser = ArgumentParser(prog='css-extract',
                            description='spike extraction from .ncs files',
                            epilog='Johannes Niediek (jonied@posteo.de)')
    parser.add_argument('--files', nargs='+',
                        help='.ncs files to be extracted')
    parser.add_argument('--start', type=int,
                        help='start index for extraction')
    parser.add_argument('--stop', type=int,
                        help='stop index for extraction')
    parser.add_argument('--jobs', nargs=1,
                        help='job file contains one filename per row')
    parser.add_argument('--matfile', nargs=1,
                        help='extract data from a matlab file')
    parser.add_argument('--destination', nargs=1, default='',
                        help='folder where spikes should be saved')
    args = parser.parse_args()

    if (args.files is None) and (args.matfile is None) and\
            (args.jobs is None):
        parser.print_help()
        print('Supply either files or jobs or matfile.')
        return

    destination = args.destination[0]

    # special case for a matlab file
    if args.matfile is not None:
        jname = os.path.splitext(os.path.basename(args.matfile[0]))[0]
        jobs = [{'name': jname,
                 'filename': args.matfile[0],
                 'is_matfile': True,
                 'count': 0}]
        mp_extract(jobs, 1)
        return

    if args.jobs:
        with open(args.jobs[0], 'r') as f:
            files = [a.strip() for a in f.readlines()]
        f.close()
        print('Read jobs from ' + args.jobs[0])
    else:
        files = args.files

    if files[0] is None:
        print('Specify files!')
        return

    # construct the jobs
    jobs = []

    for f in files:
        if args.start:
            start = args.start
        else:
            start = 0

        nrecs = get_nrecs(f)
        if args.stop:
            stop = min(args.stop, nrecs)
        else:
            stop = nrecs

        if stop % blocksize > blocksize/2:
            laststart = stop-blocksize
        else:
            laststart = stop

        starts = range(start, laststart, blocksize)
        stops = starts[1:] + [stop]
        name = os.path.splitext(os.path.basename(f))[0]
        print(name)
        for i in range(len(starts)):
            jdict = {'name': name,
                     'filename': f,
                     'start': starts[i],
                     'stop': stops[i],
                     'count': i,
                     'destination': destination}

            jobs.append(jdict)

    mp_extract(jobs, nWorkers)
