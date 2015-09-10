# JN 2015-05-08 adding docstrings to this old, useful code

"""
Simple signal filtering for spike extraction
"""
from __future__ import absolute_import, division
import numpy as np
from scipy.signal import ellip, filtfilt

# pylint:   disable=invalid-name, unbalanced-tuple-unpacking, E1101

DETECT_LOW = 300        # default 300
DETECT_HIGH = 1000      # default 1000
EXTRACT_LOW = 300       # default 300
EXTRACT_HIGH = 3000     # default 3000


class DefaultFilter(object):
    """
    Simple filters for spike extraction
    """

    def __init__(self, timestep):
        self.sampling_rate = int(1. / timestep)
        self.timestep = timestep
        self.c_detect = ellip(2, .1, 40,
                              (2 * timestep * DETECT_LOW,
                               2 * timestep * DETECT_HIGH),
                              'bandpass')
        self.c_extract = ellip(2, .1, 40,
                               (2 * timestep * EXTRACT_LOW,
                                2 * timestep * EXTRACT_HIGH),
                               'bandpass')
        self.c_notch = ellip(2, .5, 20,
                             (2 * timestep * 1999, 2 * timestep * 2001),
                             'bandstop')

    def filter_detect(self, x):
        """
        filter for spike detection
        """
        b, a = self.c_detect
        return filtfilt(b, a, x)

    def filter_extract(self, x):
        """
        filter for spike extraction
        """
        b, a = self.c_extract
        return filtfilt(b, a, x)

    def filter_denoise(self, x):
        """
        notch filter to remove higher harmonics of 50/60 cycle
        """
        b, a = self.c_notch
        return filtfilt(b, a, x)


def nonlinear(x):
    """
    Nonlinear energy operator for spike detection
    """
    xo = np.int32(x)
    y = [xo[n] ** 2 + xo[n - 1] * xo[n + 1] for n in range(1, len(x) - 1)]
    window = np.bartlett(12)
    return np.convolve(y, window)
