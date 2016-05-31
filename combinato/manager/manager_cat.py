# JN 2015-04-22
# refactoring

"""
manages spikes and sorting, after concatenation
"""
from __future__ import print_function, division, absolute_import
import numpy as np
import tables
import os

from .. import SIGNS, TYPE_NAMES, TYPE_ART, GROUP_NOCLASS, GROUP_ART, NcsFile,\
    TYPE_NON_NOISE, TYPE_ALL


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

    def get_non_noise_cluster_index(self):
        """
        returns an index of spikes that are not in
        unassigned or artifact groups
        """
        bad_groups = np.array((GROUP_ART, GROUP_NOCLASS))
        idx = np.in1d(self.types[:, 1], bad_groups)
        gids = self.types[-idx, 0]
        idx = self.get_cluster_index_joined_list(gids)
        return idx

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
        get_cluster_index_alt will be renamed to this function
        """
        clids = self.get_cluster_ids_by_gid(gid)
        all_idx = []

        for clid in clids:
            # print('Getting index for {}'.format(clid))
            all_idx.append(self.get_cluster_index(clid))

        return np.sort(np.hstack(all_idx))

    def get_cluster_index_alt(self, gid):
        """
        alternative implementation
        """
        return self.get_cluster_index_joined_list([gid])

    def get_cluster_index_joined_list(self, gids):
        """
        return index for several groups together
        """
        idx = np.in1d(self.groups[:, 1], gids)
        all_clids = self.groups[idx, 0]

        return self.index[np.in1d(self.classes, all_clids)]

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
        if self.h5datafile is not None:
            self.h5datafile.close()

    def __init__(self, h5fname):
        self.basedir = os.path.dirname(h5fname)
        self.h5datafile = None
        try:
            self.h5datafile = tables.open_file(h5fname, 'r')
        except IOError as error:
            print('Could not initialize {}: {}'.format(h5fname, error))
            self.initialized = False
            return

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
        self.initialized = True

    def get_thresholds(self):
        """
        get extraction thresholds
        """
        try:
            thr = self.h5datafile.root.thr[:, :]
        except tables.exceptions.NoSuchNodeError:
            print('Extraction thresholds were not saved!')
            thr = None
        return thr

    def init_header(self):
        """
        Tries to initialize a ncs header. Not necessarily possible.
        """
        ext = os.path.basename(self.basedir)
        cand_folders = (os.path.join(self.basedir, '..'),
                        ext)

        name = None

        for folder in cand_folders:
            for suffix in ('.ncs', '.Ncs'):
                cand_name = os.path.join(folder, ext + suffix)
                if os.path.exists(cand_name):
                    name = cand_name
                    break

        if name is not None:
            fid = NcsFile(name)
            self.header = fid.header
            del fid
            return

        for folder in cand_folders:
            cand_name = os.path.join(folder, 'channel_names.csv')
            if os.path.exists(cand_name):
                import csv
                with open(cand_name) as fid:
                    reader = csv.reader(fid, delimiter=';')
                    names = {l[0]: l[1] for l in reader}
                self.header = {'AcqEntName': names[ext]}
                return

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

        if stop_idx + 1 < t.shape[0]:
            stop_idx += 2

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
        n_clusters = len(self.sorting.get_cluster_ids_by_gid(gid))
        # shorten it
        sel = (idx >= self.start_idx) & (idx <= self.stop_idx)

        if not sel.any():
            return ret

        idx = idx[sel] - self.start_idx
        # idx -= self.start_idx
        shape = self.times[self.sign].shape[0]
        if idx[-1] >= shape:
            idx = idx[idx < shape]
            print('Shortened index!')

        ret['type'] = gtype
        ret['n_clusters'] = n_clusters
        if times:
            ret['times'] = self.times[self.sign][idx]
        if spikes:
            ret['spikes'] = self.spikes[self.sign][idx]

        return ret

    def get_data_from_index(self, index, times=True, spikes=True):
        """
        return data from a given index
        """
        idx = index - self.start_idx
        ret = dict()
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

    def get_non_noise_spikes(self):
        """
        return all non-noise spikes joined
        """
        idx = self.sorting.get_non_noise_cluster_index()
        sel = (idx >= self.start_idx) & (idx < self.stop_idx)
        idx = idx[sel]
        ret = self.get_data_from_index(idx)
        ret['type'] = TYPE_NON_NOISE
        return ret

    def get_all_spikes(self):
        """
        return all spikes
        """
        sel = (self.sorting.index >= self.start_idx) &\
            (self.sorting.index < self.stop_idx)
        idx = self.sorting.index[sel]
        ret = self.get_data_from_index(idx)
        ret['type'] = TYPE_ALL
        return ret


class Combinato(SortingManagerGrouped):
    """
    convenience class, reads sorted data
    """

    def __init__(self, fname, sign, label):
        self.initialized = False
        self.h5datafile = None  # in case of early return

        basedir = os.path.dirname(fname)
        labelbasename = os.path.basename(label)
        sorting_session = os.path.join(basedir, labelbasename)

        # quick check if we can do this
        if not os.path.exists(sorting_session):
            print('Session folder {} '
                  'not found'.format(sorting_session))
            return

        super(Combinato, self).__init__(fname)
        self.set_sign_times_spikes(sign)
        res = self.init_sorting(sorting_session)

        if not res:
            print('Sorting session {} '
                  'not initialized'.format(sorting_session))
        else:
            self.initialized = True
        
def test(name, label, ts):
    """
    simple test case, needs a folder as argument
    """
    with open(ts) as fid:
        start, stop = [int(x)/1000. for x in fid.readline().split()]
    fid.close()

    man = SortingManagerGrouped(name)
    if not man.initialized:
        return
    print('Working on {}, from time {} to {} ({:.1f} min)'
          .format(name, start, stop, (stop-start)/6e4))
    start_idx, stop_idx = man.get_start_stop_index('pos', start, stop)
    print('Setting start index: {}, stop index: {}'.
          format(start_idx, stop_idx))
    man.set_sign_times_spikes('pos', start_idx, stop_idx)
    ret = man.init_sorting(os.path.join(os.path.dirname(name), label))
    if not ret:
        print('Unable to initialize!')
        return
    print(man.sorting.index.shape)
    groups = man.get_groups()
    print('Retrieved Groups')
    test_gid = groups.keys()[0]
    man.get_group_joined(test_gid)

    all_groups = man.get_groups_joined()

    # iterate through clusters
    all_good = 0
    for k, v in groups.items():
        print('Group {} type {}'.format(k, TYPE_NAMES[man.get_group_type(k)]))
        print(v.keys())
        sumidx = 0
        for clid in v:
            print('Cluster {} len {}'.format(clid, v[clid]['times'].shape[0]))
            sumidx += v[clid]['times'].shape[0]

        if man.get_group_type(k) > 0:
            all_good += sumidx

        idx1 = man.sorting.get_cluster_index_joined(k)
        idx2 = man.sorting.get_cluster_index_alt(k)
        assert not (idx1 - idx2).any()

        print('Total index len {} vs {} summed'.
              format(idx1.shape[0], sumidx))
        # assert idx1.shape[0] == sumidx

    non_noise_spk = man.get_non_noise_spikes()
    total = man.get_all_spikes()
    print('Non-noise index has {} elements'.
          format(non_noise_spk['times'].shape[0]))
    assert non_noise_spk['times'].shape[0] == all_good

    print('Total has {} elements'.format(total['times'].shape[0]))

    for gid, group in all_groups.items():
        print('Group {} has {} times, type {} and {} members'.
              format(gid, group['times'].shape[0],
                     TYPE_NAMES[group['type']], group['n_clusters']))
