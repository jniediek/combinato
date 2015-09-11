from __future__ import absolute_import
import numpy as np

def spikeDist(a, b):
    d = np.sqrt( ( (a - b)**2 ).sum() )
    f = min(a.max(), b.max())
    return d/f
