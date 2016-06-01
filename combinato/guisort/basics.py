from __future__ import absolute_import, division
import numpy as np

def spikeDist(a, b):
    d = np.sqrt( ( (a - b)**2 ).sum() )
    f = min(a.max(), b.max())
    return d/f


def correlation(times1, times2, up_to_lag, auto_corr=False):
    """
    calculate the correlation in a loop
    """ 
    l1 = len(times1)
    l2 = len(times2)

    if l1 < l2:
        outer = times1
        inner = times2
    else:
        outer = times2
        inner = times1

    lags = []
    for t in outer:
        index = (inner >= t - up_to_lag) & (inner <= t + up_to_lag)
        if auto_corr:
            index &= (inner != t)
        lags.append(inner[index] - t)

    return np.hstack(lags)
