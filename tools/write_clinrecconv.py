# -*- coding: utf-8 -*-
# JN 2014-10-21
# script creates a clinRecConv.py from ncs files

import os
import numpy as np
from combinato import NcsFile
from matplotlib.dates import date2num

if __name__ == "__main__":
    if os.path.exists('clinRecConv.py'):
        print('File exists, doing nothing')
    else:
        fid = NcsFile('CSC1.ncs')
        d = fid.header['opened']
        n = date2num(d)
        ts = fid.read(0, 1, 'timestep')
        np.save('clinRecConv', np.array((ts, d)))
