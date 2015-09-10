# JN 2015-04-22
# refactoring

"""
manages spikes and sorting, after concatenation
"""
from __future__ import print_function, division, absolute_import
import numpy as np
import tables
import os

from .. import SIGNS, TYPE_NAMES, TYPE_ART, NcsFile


class SortingFile(object):
    """
    represents a grouped sorting file
    """
    def __del__(self):
        self.h5fid.close()

    def __init__(self, h5fname):
        self.h5fid = tables.open_file(h5fname, 'r+')
        self.index = self.h5fid.root.index[:]
        self.classes = self.h5fid.root.classes[:]
        self.groups = self.h5fid.root.groups[:]
        self.types = self.h5fid.root.types[:]
        self.sign = self.h5fid.get_node_attr('/', 'sign')
        self.basedir = os.path.dirname(h5fname)
        self.matches = self.h5fid.root.matches[:]

    def get_gids(self):
        """
        return list of gids
        """
        return np.unique(self.groups[:, 1])

    def get_cluster_ids_by_gid(self, gid):
        """
        return class ids for a group
        """
        idx = self.groups[:, 1] == gid
        return self.groups[idx, 0]

    def get_cluster_index(self, clid):
        """
        return index for a cluster
        """
        return self.index[self.classes == clid]

    def _get_group_matches(self, gid):
        """
        specific function to get matches
        """
        clids = self.get_cluster_ids_by_gid(gid)
        return self.matches[np.in1d(self.classes, clids)]

    def get_cluster_index_joined(self, gid):
        """
        return index for group (concatenated from all clusters)
        """
        clids = self.get_cluster_ids_by_gid(gid)
        all_idx = []

        for clid in clids:
            all_idx.append(self.get_cluster_index(clid))

        return np.sort(np.hstack(all_idx))

    def get_group_type(self, gid):
        """
        return the type of a group
        """
        idx = self.types[:, 0] == gid
        return self.types[idx, 1][0]

    def save_groups_and_types(self, groups, types):
        """
        save a new group and type array
        """
        self.groups = groups
        self.types = types

        self.h5fid.root.groups[:] = groups

        self.h5fid.remove_node('/', 'types')
        self.h5fid.create_array('/', 'types', types)
        self.h5fid.flush()


class SortingManagerGrouped(object):
    """
    represents a sorting session after grouping
    """
    def __del__(self):
        self.h5datafile.close()

    def __init__(self, h5fname):
        self.basedir = os.path.dirname(h5fname)
        self.h5datafile = tables.open_file(h5fname, 'r')

        self.start_idx = None
        self.stop_idx = None
        self.sign = None

        self.all_times = dict()
        self.spikes = dict()
        self.times = dict()

        for sign in SIGNS:
            self.all_times[sign] = None
            self.spikes[sign] = None
            self.times[sign] = None

        self.sorting = None

        self.header = None
        self.init_header()

    def get_thresholds(self):
        """
        get extraction thresholds
        """
        return self.h5datafile.root.thr[:, :]

    def init_header(self):
        """
        Tries to initialize a ncs header. Not necessarily possible.
        """
        ext = os.path.basename(self.basedir)
        cand_folders = (os.path.join(self.basedir, '..'),
                        ext)

        name = None

        for folder in cand_folders:
            cand_name = os.path.join(folder, ext + '.ncs')
            if os.path.exists(cand_name):
                name = cand_name
                break
            else:
                cand_name = os.path.join(folder, ext + '.Ncs')
                if os.path.exists(cand_name):
                    name = cand_name
                    break

        if name is not None:
            fid = NcsFile(name)
            self.header = fid.header
            del fid

        else:
            print('Ncs file not found, no header!')
            self.header = None

    def init_sorting(self, sorting_folder):
        """
        initialize a sorting folder
        returns True if init worked, else False
        """
        sorting_path = os.path.join(sorting_folder, 'sort_cat.h5')

        if os.path.exists(sorting_path):
            self.sorting = SortingFile(sorting_path)
            self.sign = self.sorting.sign
            return True
        else:
            return False

    def get_start_stop_index(self, sign, start_time, stop_time):
        """
        return where to start and stop for a given time frame
        """

        if self.times[sign] is None:
            self.times[sign] = self.h5datafile.get_node('/' + sign, 'times')[:]

        t = self.times[sign]
        start_idx = t.searchsorted(start_time)
        stop_idx = t.searchsorted(stop_time)

        if stop_idx < t.shape[0]:
            stop_idx += 1

        return start_idx, stop_idx

    def set_sign_times_spikes(self, sign, start_idx=0, stop_idx=np.inf):
        """
        set times, spikes, start, stop
        """
        self.start_idx = start_idx

        if stop_idx in [np.inf, None]:
            stop_idx = self.h5datafile.get_node('/' + sign,
                                                'times').shape[0]

        self.stop_idx = stop_idx
        self.sign = sign

        self.spikes[sign] =\
            self.h5datafile.\
            get_node('/' + sign, 'spikes')[start_idx:stop_idx, :]

        if self.all_times[sign] is not None:
            t = self.all_times[sign]
        else:
            t = self.h5datafile.get_node('/' + sign, 'times')

        self.times[sign] = t[start_idx:stop_idx]

    def get_groups(self, times=True, spikes=True):
        """
        return groups, each containing its times and spikes if requested
        """
        gids = self.sorting.get_gids()
        ret = dict()

        for gid in gids:
            clids = self.sorting.get_cluster_ids_by_gid(gid)
            for clid in clids:
                idx = self.sorting.get_cluster_index(clid)
                # shorten it
                sel = (idx >= self.start_idx) & (idx < self.stop_idx)
                idx = idx[sel] - self.start_idx

                if idx.any():
                    if gid not in ret:
                        ret[gid] = dict()

                    ret[gid][clid] = dict()

                    if times:
                        ret[gid][clid]['times'] = self.times[self.sign][idx]
                    if spikes:
                        ret[gid][clid]['spikes'] =\
                            self.spikes[self.sign][idx, :]

                    imgname = 'class_{:03d}.png'.format(clid)
                    imgpath1 = os.path.join(self.basedir, self.sorting.basedir,
                                            imgname)
                    imgpath2 = os.path.join(self.sorting.basedir, imgname)

                    if os.path.exists(imgpath1):
                        imgval = imgpath1

                    elif os.path.exists(imgpath2):
                        imgval = imgpath2
                    else:
                        imgval = None

                    ret[gid][clid]['image'] = imgval

        return ret

    def get_group_joined(self, gid, times=True, spikes=True, artifacts=True):
        """
        get one group, all clusters joined
        """
        ret = dict()

        gtype = self.get_group_type(gid)

        if (artifacts is False) and (gtype == TYPE_ART):
            return ret

        idx = self.sorting.get_cluster_index_joined(gid)

        if not idx.any():
            return ret

        idx -= self.start_idx
        shape = self.times[self.sign].shape[0]
        if idx[-1] >= shape:
            idx = idx[idx < shape]
            print('Shortened index!')

        ret['type'] = gtype
        if times:
            ret['times'] = self.times[self.sign][idx]
        if spikes:
            ret['spikes'] = self.spikes[self.sign][idx]

        return ret

    def get_groups_joined(self, times=True, spikes=True, artifacts=True):
        """
        return groups with times and spikes joined
        """
        gids = self.sorting.get_gids()
        ret = dict()

        for gid in gids:
            group = self.get_group_joined(gid, times, spikes, artifacts)
            if len(group) > 0:
                ret[gid] = group
        return ret

    def get_group_type(self, gid):
        """
        return group type
        """
        return self.sorting.get_group_type(gid)

    def get_samples_per_spike(self):
        """
        return samples per spike...
        """
        return self.spikes[self.sign].shape[1]

    def save_groups_and_types(self, groups, types):
        """
        save to underlying sorting file
        """
        self.sorting.save_groups_and_types(groups, types)

    def get_group_table(self):
        """
        get group table
        """
        return self.sorting.groups

    def get_type_table(self):
        """
        get type table
        """
        return self.sorting.types


class Combinato(SortingManagerGrouped):
    """
    convenience class, reads sorted data
    """

    def __init__(self, fname, sign, label):
        super(Combinato, self).__init__(fname)
        self.set_sign_times_spikes(sign)
        basedir = os.path.dirname(fname)
        labelbasename = os.path.basename(label)
        sorting_session = os.path.join(basedir, labelbasename)

        self.initialized = False
        if os.path.exists(sorting_session):
            res = self.init_sorting(sorting_session)

            if not res:
                print('Sorting session {} '
                      'not initialized'.format(sorting_session))
            else:
                self.initialized = True
        else:
            print('Session folder {} '
                  'not found'.format(sorting_session))


def test(name):
    """
    simple test case
    """
    with open(os.path.join(os.path.dirname(name), '../morning_ts.txt')) as fid:
        start, stop = [int(x)/1000. for x in fid.readline().split()]
    fid.close()

    man = SortingManagerGrouped(name)
    print(name, start, stop)
    start_idx, stop_idx = man.get_start_stop_index('pos', start, stop)
    print(start_idx, stop_idx)
    man.set_sign_times_spikes('pos', start_idx, stop_idx)
    man.init_sorting(os.path.join(os.path.dirname(name), 'sort_pos_mo'))
    groups = man.get_groups()

    # iterate clusters
    for k, v in groups.items():
        print('Group {} type {}'.format(k, TYPE_NAMES[man.get_group_type(k)]))
        sumidx = 0
        for clid in v:
            print('Cluster {} len {}'.format(clid, v[clid]['times'].shape[0]))
            sumidx += v[clid]['times'].shape[0]
            # print('{:.1f} min'.format((v[clid]['times'].max() -
            #                           v[clid]['times'].min())/6e4))

        print('Total index len {} vs {} summed'.
            format(man.sorting.get_cluster_index_joined(k).shape[0], sumidx))


    groups = man.sorting.groups
    # types = man.sorting.types

    all_groups = man.get_groups_joined()
    for gid, group in all_groups.items():
        print('Group {} has {} times and type {}'.format(gid, group['times'].shape[0],
        TYPE_NAMES[group['type']]))
    # man.save_groups_and_types(groups, types)


def main():
    import sys
    test(sys.argv[1])

if __name__ == "__main__":
    main()
