# -*- coding: utf-8 -*-
# JN 2016-01-12
# JN 2014-10-28


from __future__ import division, absolute_import, print_function
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


def initfile(h5name, ncsf, q_down):
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

    h5f.create_earray('/', 'time', tables.UInt64Atom(), [0])

    return h5f


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
