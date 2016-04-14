from __future__ import print_function, division
import numpy as np
import tables
from combinato import NcsFile
from signalviewer import expandts
Q = 16

def main(fname):
    fid = NcsFile(fname)
    nrec = fid.num_recs
    # out_size = (nrec + 1) * 512/Q
    times = fid.read(0, fid.num_recs, mode='timestamp')
    times = times.astype(float) / 1000
    arr = expandts(times, 1e3 * fid.timestep, 16)
    idx_err = np.diff(arr, 2).nonzero()[0]
    print(idx_err.shape[0])
    print(np.diff(arr, 2)[idx_err])

    outfile = tables.open_file('times_16.h5', 'w')
    outfile.create_array('/', 'times', arr)
    outfile.close()

if __name__ == "__main__":
    main('CSC1.ncs')
