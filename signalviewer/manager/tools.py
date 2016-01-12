# -*- coding: utf-8 -*-
# JN 2016-01-12

from __future__ import print_function, division, absolute_import
import numpy as np


DEBUG = True


def debug(msg):
    if DEBUG:
        print(msg)


def expandts(ts, timestep, q=1):
    """
    expands time stamps by inserting 512/q interpolated
    time points after each time point in ts
    all times are given in ms
    """
    interp = np.arange(0, 512*timestep, q*timestep)
    return np.hstack([interp + t for t in ts])
