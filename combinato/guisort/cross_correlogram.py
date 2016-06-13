# JN 2016-06-10

import numpy as np
EMPTY = np.array([], dtype=np.float64)

def cross_correlogram(times1, times2, lag, is_same):
    """
    Calculate cross-correlogram. This assumes that the input arguments are sorted!
    In most cases, np.histogram(res, bins) will follow.
    """
    if times1.shape[0] < times2.shape[0]:
        outer = times1
        inner = times2
        invert = True
    else:
        outer = times2
        inner = times1
        invert = False

    lags = []

    for i in range(outer.shape[0]):
        temp = outer[i]
        start = inner.searchsorted(temp - lag)
        stop = inner.searchsorted(temp + lag, 'right')
        if is_same:
            if (i > start):
                lags.append(inner[start:i] - temp)
            if (i + 1 < stop):
                lags.append(inner[i+1:stop] - temp)
            if (i < start) or (i >= stop):
                lags.append(inner[start:stop] - temp)
        else:
            if start < stop:
                lags.append(inner[start:stop] - temp)

    res = np.hstack(lags)

    if len(lags) == 0:
        return EMPTY

    if invert:
        res *= -1

    return res
