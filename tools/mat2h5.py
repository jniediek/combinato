# JN 2015-06-19, 2015-12-14
# Convert spikes from Matlab files to our format
from __future__ import division, print_function, absolute_import
import os
from argparse import ArgumentParser
import numpy as np
from scipy.io import loadmat
import tables

NAME_SPIKES = 'spikes'
NAME_TS = 'timestamps'


def convert(fname_in, fname_out, sign='pos', time_factor=1, volt_factor=1):
    """
    Read a matfile, write a h5 file. Times and Volts are multiplied
    by supplied factors
    """
    if os.path.exists(fname_out):
        raise Warning('{} exists, not overwriting'.format(fname_out))

    spikes = {}
    times = {}
    in_data = loadmat(fname_in)

    in_spikes = in_data[NAME_SPIKES] * volt_factor
    in_times = in_data[NAME_TS][0].ravel() * time_factor
    n_spk = in_times.shape[0]

    empty_spikes = np.zeros((1, in_spikes.shape[1]))
    empty_times = np.zeros(1)

    dur = (in_times[-1] - in_times[0])/6e4
    print('Read {} spikes from a {:.0f} minute recording'.format(n_spk, dur))

    # fill the other sign with empty data
    other_sign = 'pos' if sign == 'neg' else 'neg'

    spikes[sign] = in_spikes
    times[sign] = in_times
    spikes[other_sign] = empty_spikes
    times[other_sign] = empty_times

    out_file = tables.open_file(fname_out, 'w')

    for sign in ('pos', 'neg'):
        out_file.create_group('/', sign)
        out_file.create_array('/' + sign, 'times', times[sign])
        out_file.create_array('/' + sign, 'spikes', spikes[sign])

    out_file.close()


def parse_arguments():
    """
    parse command line arguments
    """
    desc = "Converts spikes from a Matlab file to our format.\n"\
           "Variable names have to be `{}` for spikes"\
           " and `{}` for timestamps.".\
           format(NAME_SPIKES, NAME_TS)
    parser = ArgumentParser(description=desc)
    parser.add_argument('--micro', action='store_true', default=False,
                        help='timestamps in input file are in microseconds')
    parser.add_argument('--neg', action='store_true', default=False)
    parser.add_argument('--outname', nargs=1)
    parser.add_argument('matfile', nargs=1)

    args = parser.parse_args()
    fname_in = args.matfile[0]
    fname_in_base = os.path.splitext(fname_in)[0]

    sign = 'neg' if args.neg else 'pos'

    if args.outname is not None:
        fname_out = args.outname
        if fname_out[-2:] != '.h5':
            fname_out += '.h5'
    else:
        fname_out = 'data_{}.h5'.format(fname_in_base)

    if args.micro:
        time_factor = .001
        time_unit = 'microseconds'
    else:
        time_factor = 1
        time_unit = 'milliseconds'

    print('Converting {} to {}\nAmplitude: {}\nTime unit: {}'.
          format(fname_in, fname_out, sign, time_unit))

    convert(fname_in, fname_out, sign, time_factor)


if __name__ == '__main__':
    parse_arguments()
