# JN 2016-05-31

"""
calculate a cross-correlogram
"""

from __future__ import division, print_function, absolute_import
import numpy as np
cimport numpy as np


def cross_correlogram(np.ndarray[np.float64_t, ndim=1] arr1,
                      np.ndarray[np.float64_t, ndim=1] arr2,
                      np.float64_t lag, int is_same):
    """
    Calculate cross-correlogram. This assumes that the input arguments are sorted!
    In most cases, np.histogram(res, bins) will follow.
    if is_same is given, it skips lag 0
    """
    cdef Py_ssize_t len_arr1 = arr1.shape[0]
    cdef Py_ssize_t len_arr2 = arr2.shape[0]
    cdef Py_ssize_t start_idx, stop_idx, i
    cdef np.float64_t temp
    cdef int invert
    cdef np.ndarray[np.float64_t, ndim=1] result
    cdef np.ndarray[np.float64_t, ndim=1] empty = np.array([], dtype=np.float64)

    if len_arr1 < len_arr2:
        inner_size = len_arr2
        outer_size = len_arr1
        # have to invert
        invert = True
    else:
        inner_size = len_arr1
        outer_size = len_arr2
        invert = False

    cdef np.ndarray inner = np.zeros(inner_size, dtype=np.float64)
    cdef np.ndarray outer = np.zeros(outer_size, dtype=np.float64)

    if len_arr1 < len_arr2:
        inner[:] = arr2[:]
        outer[:] = arr1[:]

    else:
        inner[:] = arr1[:]
        outer[:] = arr2[:]

    lags = []
    for i in range(outer_size):
        temp = outer[i]
        # find the first place, assuming that arrays are sorted
        start_idx = inner.searchsorted(temp - lag)
        stop_idx = inner.searchsorted(temp + lag, 'right')

        if is_same:
            if (i > start_idx):
                lags.append(inner[start_idx:i] - temp)
            if (stop_idx > i + 1):
                lags.append(inner[i+1:stop_idx] - temp)
            if (i < start_idx) or (i > stop_idx):
                lags.append(inner[start_idx:stop_idx] - temp)
        else:
            if start_idx < stop_idx:
                lags.append(inner[start_idx:stop_idx] - temp)
    
    if len(lags) == 0:
        return empty

    result = np.hstack(lags)
    if invert:
        result *= -1

    return result
