# -*- coding: utf-8 -*-
# JN 2016-01-12
# JN 2014-10-28


from __future__ import division, absolute_import, print_function
import datetime
import tables


def make_blocks(N, bs=100000):
    """
    creates block starts and stops of length bs
    """
    starts = list(range(0, N, bs))

    if N - starts[-1] < bs/4:
        del starts[-1]

    stops = starts[1:] + [N]

    return zip(starts, stops)


def initfile(h5name, ncsf, q_down, include_times=True):
    """
    initializes a h5 file to store converted data
    """
    adbitvolts = ncsf.header['ADBitVolts']
    timestep = ncsf.timestep

    chname = ncsf.header['AcqEntName']

    h5f = tables.open_file(h5name, 'w')

    h5f.create_group('/', 'data')
    h5f.create_earray('/data', 'rawdata', tables.Int16Atom(), [0])
    h5f.root.data.rawdata.set_attr('ADBitVolts', adbitvolts)
    h5f.root.data.rawdata.set_attr('timestep', timestep)
    h5f.root.data.rawdata.set_attr('Q', q_down)
    h5f.root.data.rawdata.set_attr('AcqEntName', chname)

    if include_times:
        h5f.create_earray('/', 'time', tables.UInt64Atom(), [0])

    return h5f


def parse_datetime(fname, mode='start'):
    """
    read datetime file
    returns ts_start_nlx: start time in milliseconds
    start_date: start time as datetime object

    the same for mode='stop'
    """
    if mode == 'start':
        target = 'start_recording'
    elif mode == 'stop':
        target = 'stop_recording'
    else:
        raise Warning('Unknown parse_datetime mode: {}'.format(mode))

    with open(fname, 'r') as fid:
            lines = [line.strip() for line in fid.readlines()]

    for line in lines:
        if line[0] == '#':
            continue
        fields = line.split()
        if fields[0] == target:
            dtime, micro = fields[2].split('.')
            dstr = fields[1] + ' ' + dtime
            dfmt = '%Y-%m-%d %H:%M:%S'
            start_date = datetime.datetime.strptime(dstr, dfmt)
            start_date += datetime.timedelta(microseconds=int(micro))
            break

    ts_start_nlx = float(fields[3])/1000
    return ts_start_nlx, start_date


if __name__ == "__main__":
    """
    a small test case
    """
    from combinato import NcsFile
    import sys
    Q = 16
    ncsfname = sys.argv[1]
    fid = NcsFile(ncsfname)
    h5f = initfile('out.h5', fid, Q)
    print(h5f)
