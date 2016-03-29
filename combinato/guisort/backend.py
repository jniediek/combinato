# JN 2015-01-06
# refactoring
"""
this is the gui sorter backend, doesn't have much functionality actually
"""
from __future__ import print_function, division, absolute_import

import os
import numpy as np
from .. import SortingManagerGrouped
from .sessions import Sessions


class Backend(object):
    """
    gui sorter backend
    """
    def __del__(self):
        print('Closing session')
        del self.sorting_manager
        del self.sessions

    def __init__(self, datafilename, sessionfilename,
                 start_time=0, stop_time=np.inf):

        self.sessions = None
        print('Openening session {} {}'.format(datafilename, sessionfilename))
        self.folder = os.path.dirname(datafilename)
        self.sorting_manager = SortingManagerGrouped(datafilename)
        self.sorting_manager.init_sorting(sessionfilename)

        self.sign = self.sorting_manager.sign

        start_idx, stop_idx = self.sorting_manager.\
            get_start_stop_index(self.sign, start_time, stop_time)

        print('Setting index {} to {}'.format(start_idx, stop_idx))

        self.sorting_manager.\
            set_sign_times_spikes(self.sign, start_idx, stop_idx)

        self.x = np.arange(self.sorting_manager.get_samples_per_spike())
        self.sessions = Sessions(self)
        thresholds = self.sorting_manager.get_thresholds()
        if thresholds is not None:
            if (thresholds[-1, 1] - thresholds[0, 0]) > 24*60*60*1000:
                thresholds[:, :2] /= 1e3  # this is necessary for some old files
        self.thresholds = thresholds
        self.original_start = start_time
        self.original_stop = stop_time

    def get_thresholds(self):
        """
        returns thresholds for the current time range
        """
        if self.thresholds is None:
            return None
        # start = self.sessions.start_time
        # stop = self.sessions.stop_time
        start = self.original_start
        stop = self.original_stop
        start_idx = self.thresholds[:, 0] >= start - 300e3
        stop_idx = self.thresholds[:, 1] <= stop + 300e3
        idx = start_idx & stop_idx
        if idx.any():
            ret = self.thresholds[idx, :]
        else:
            ret = self.thresholds
        return ret
