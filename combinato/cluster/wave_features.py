# JN 2015-01-11

from __future__ import print_function, division, absolute_import
import numpy as np
import pywt # scipy doesn't have the flexibility yet
from .. import options

WAVELET = pywt.Wavelet(options['Wavelet'])
OUT_DTYPE = np.float32
LEVEL = 4

def wavelet_features(data):
    """
    calculates wavelet transform
    """
    # probably implementing this in cython would
    # save some computation time

    first_row = pywt.wavedec(data[0, :], WAVELET, level=LEVEL)
    aligned = np.hstack(first_row)

    output = np.empty((data.shape[0], aligned.shape[0]), dtype=OUT_DTYPE)
    output[0, :] = aligned

    for i, row in enumerate(data[1:, :]):
        features = pywt.wavedec(row, WAVELET, level=LEVEL)
        output[i + 1, :] = np.hstack(features)

    return output


# FIXME move tests to separate test directory!
def testit():
    data = np.ones((3, 64)) 
    data[0, :] = np.arange(64)
    data[1, :] = np.linspace(0, 1, 64)
    print(wavelet_features(data))
    # test successfull 2015-02-10 JN


if __name__ == "__main__":
    testit()
