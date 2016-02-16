# -*- encoding: utf-8 -*-
# JN 2016-02-16

"""
Plot a spectrum from the first 1000 records of data
"""
import sys
import scipy.signal as sig
import matplotlib.pyplot as mpl

from combinato import NcsFile, DefaultFilter


def plot_spectrum(fname):
    fid = NcsFile(fname)
    rawdata = fid.read(0, 1000)
    data = rawdata * (1e6 * fid.header['ADBitVolts'])
    fs = 1/fid.timestep
    my_filter = DefaultFilter(fid.timestep)
    filt_data = my_filter.filter_extract(data)
    [f, p] = sig.welch(data, fs, nperseg=32768)
    [f_filt, p_filt] = sig.welch(filt_data, fs, nperseg=32768)

    fig = mpl.figure()
    plot = fig.add_subplot(1, 1, 1)
    plot.plot(f, p, label='Unfiltered')
    plot.plot(f_filt, p_filt, label='Filtered')

    plot.set_yscale('log')
    plot.legend()
    plot.set_ylabel(r'$\mu\mathrm{V}^2/\mathrm{Hz}$')
    plot.set_xlabel(r'$\mathrm{Hz}$')


def main():
    plot_spectrum(sys.argv[1])
    mpl.show()


if __name__ == '__main__':
    main()
