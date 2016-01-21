# JN 2016-01-12
"""
manage spikes for data viewer
"""
import os
from .tools import debug


class SpikeManager(object):
    """
    Represent spikes for data viewer
    """
    def __init__(self, sign, label):
        self.fnames = {}
        self.openfiles = {}
        self.times = {}
        self.spikes = {}
        self.beg_end = {}
        self.sortednames = {}
        self.sortedfiles = {}
        self.label = label
        self.sign = sign

    def __del__(self):
        for fid in self.openfiles.values():
            fid.close()

    def check_add(self, key, entname):
        sppath = os.path.join(key, 'data_{}.h5'.format(key))
        sorted_path = os.path.join(key, self.label)
        if os.path.isdir(sorted_path):
            self.sortednames[entname] = sppath

        if os.path.exists(sppath):
            self.fnames[entname] = sppath

        debug(self.sortednames)

    def h5f_by_key(self, key):
        if key in self.sortednames:
            print('loading sorted spikes for ' + key)
            self.sortedfiles[key] = Combinato(self.sortednames[key],
                                              self.sign, self.label)

        if key not in self.fnames:
            debug('No spike file for ' + key)
            return

        if key not in self.openfiles:
            fid = tables.open_file(self.fnames[key], 'r')
            self.openfiles[key] = fid
            # warning! times get loaded as copies
            # because we have to search them
            print('Loading times for ' + key)
            t = fid.get_node('/' + self.sign + '/times')[:]
            print('Done')
            self.times[key] = t
            s = fid.get_node('/' + self.sign + '/spikes')
            self.spikes[key] = s

        else:
            t = self.times[key]
            s = self.spikes[key]

        return t, s

    def set_beg_end(self, key, start, stop, sign='pos'):

        ret = self.h5f_by_key(key, sign)
        if ret is None:
            return

        beg = ret[0]
        end = ret[1]

        t = self.times[key]
        beg = max(t.searchsorted(start) - 1, 0)
        end = min(t.searchsorted(stop) + 1, t.shape[0])

        self.beg_end[key] = (beg, end)
        print(self.beg_end[key])

    def get_sorted_data(self, key, start, stop):
        ret = {}
        ea = np.array([])
        if key in self.sortedfiles:
            print(start, stop)
            clu = self.sortedfiles[key].get_groups_joined()
            for c in clu:
                times = clu[c]['times']
                idx = (times >= start) & (times <= stop)
                print(times[0], times[-1], start, stop)
                print(c, idx.sum())
                if idx.any():
                    t = times[idx]
                else:
                    t = ea
                ret[c] = {'times': t}
                print(c, idx.sum())

            return ret

        else:
            return np.array([])

    def get_sp_data(self, key, which='times'):
        key = str(key)

        if key in self.beg_end:
            beg = self.beg_end[key][0]
            end = self.beg_end[key][1]
        else:
            return np.array([])

        if which == 'times':
            retv = self.times[key]
        elif which == 'spikes':
            retv = self.spikes[key]

        return retv[beg:end]

