# -*- coding: utf-8 -*-
# JN 2014-09-24
# JN 2015-01-08
"""
prepare clustering jobs
"""
from __future__ import print_function, division, absolute_import
import os
import numpy as np
from .. import options, DataManager, create_session

DEBUG = options['Debug']


def make_arguments(filename, sign, mode, start=0,
                   stop=None, max_nspk_session=20000):
    """
    prepare arguments for clustering
    mode:
    if 'time', start and stop are interpreted as
    start and stop timestamps
    if 'index', start and stop are interpreted as
    start and stop indexes into the spike array, after artifact exclusion
    """
    h5manager = DataManager(filename, cache=['times', 'artifacts'])
    non_artifact_idx, num_spikes = h5manager.get_non_artifact_index(sign)
    if num_spikes == 0:
        print('No spikes found!')
        return None

    # find start and stop index
    if mode == 'time':
        times = h5manager.get_data_by_name_and_index('times',
                                                     non_artifact_idx,
                                                     sign=sign)[:]
        # print(times[0], times[-1])
        start_idx = np.searchsorted(times, start)
        stop_idx = np.searchsorted(times, stop)
        print('Converted time to {}-{}'.format(start_idx, stop_idx))

    else:
        start_idx = start
        stop_idx = stop
        if stop_idx is None:
            stop_idx = non_artifact_idx[-1]

    # partition into blocks of length 'max_nspk_session'
    starts = range(start_idx, stop_idx, max_nspk_session)
    stops = starts[1:]
    stops.append(min(stop_idx, non_artifact_idx[-1]))

    if len(stops) > 1:
        if stops[-1] - stops[-2] < max_nspk_session/5:
            stops[-2] = stops[-1]
            del starts[-1], stops[-1]

    stops[-1] += 1

    ret = []

    for start, stop in zip(starts, stops):
        ret.append(non_artifact_idx[start:stop])

    return ret


def main(fnames, sign, mode, start, stop, max_nspk_session, label, replace):
    """
    creates clustering directories for given arguments
    """

    ret = []

    print('running {} {} {} {} {} {} {} {}'.format(fnames, sign, mode, start,
        stop, max_nspk_session, label, 'replace' if replace else 'no replace'))

    for name in fnames:
        jobs = make_arguments(name, sign, mode, start, stop, max_nspk_session)
        if jobs is None:
            continue
        dirname = os.path.dirname(name)

        for job in jobs:
            if job.shape[0] == 0:
                continue
            session_name = create_session(dirname, sign, label, job, replace)
            ret.append((name, sign, os.path.join(dirname, session_name)))
            # print(name, session_name)

    return ret


def test(fnames):
    """
    simple test
    """
    main(fnames, 'pos', 'time', 0, 109392566615/1000, 20000, 'jn', True)


def parse_arguments():
    """
    typical argument parsing
    """
    from argparse import ArgumentParser
    from getpass import getuser
    parser = ArgumentParser('css-prepare-sorting',
                            description='Prepares folders for spike sorting',
                            epilog='Johannes Niediek (jonied@posteo.de)')
    parser.add_argument('--times', nargs='+',
                        help='supply timestamps from files')
    parser.add_argument('--jobs', nargs=1,
                        help='supply list of clustering jobs')
    parser.add_argument('--datafile', nargs=1,
                        help='cluster from one datafile')
    parser.add_argument('--between', default=False, action='store_true',
                        help='use time between supplied timestamps')
    parser.add_argument('--neg', default=False, action='store_true',
                        help='use negative spikes')
    parser.add_argument('--max-nspk', default=20000, type=int,
                        help='maximal number of spikes per run')
    parser.add_argument('--label', default=getuser()[:3],
                        help='name under which sorting is stored')
    parser.add_argument('--start', nargs=1, type=int,
                        help='start at this spike')
    parser.add_argument('--stop', nargs=1, type=int,
                        help='stop at this spike')

    args = parser.parse_args()

    write_log = True
    sign_set = False

    if args.jobs is None and args.datafile is None:
        parser.print_help()
        return

    if None not in (args.jobs, args.datafile):
        parser.print_help()
        print('Supply either list file or data file, not both')
        return

    if args.times is not None:
        mode = 'time'
        start_stop = []

        for fname_time in args.times:
            with open(fname_time, 'r') as fpt:
                times = [float(field) for field in fpt.readline().split()]
            fpt.close()
            # convert from microseconds at this stage
            start_stop.append((times[0]/1000, times[1]/1000))

        if args.between:
            # 2nd timestamp of 1st file to 1st timestamp of 2nd file
            start_stop = [(start_stop[0][1], start_stop[1][0])]

    else:
        mode = 'index'

    if args.datafile:
        fnames = args.datafile
        if mode == 'index':
            if None in (args.start, args.stop):
                start_stop = [(0, None)]
                print('Automatically using all spikes'.format(*start_stop))
            else:
                start_stop = [(args.start[0], args.stop[0])]

    elif args.jobs:
        with open(args.jobs[0], 'r') as fpn:
            fnames = fpn.read().splitlines()
        fpn.close()
        
        if (mode == 'index') and (None in (args.start, args.stop)):
            start_stop = [(0, None)]
            print('Automatically using all spikes'.format(*start_stop))

        if 'neg' in args.jobs[0]:
            sign = 'neg'
            sign_set = True
        elif 'pos' in args.jobs[0]:
            sign = 'pos'
            sign_set = True

    # get the sign
    if not sign_set:
        sign = 'neg' if args.neg else 'pos'

    for start, stop in start_stop:
        sessions = main(fnames, sign, mode, start,
                        stop, args.max_nspk, args.label, True)

        if write_log:
            outfname = "sort_{}_{}.txt".format(sign, args.label)
            with open(outfname, 'a') as outf:
                for name, sign, ses in sessions:
                    outf.write("{} {} {}\n".format(name, sign, ses))
            outf.close()
