# -*- coding: utf-8 -*-
# JN 2015-01-06

# JN 2015-04-13
# state of the project:
# switched to manager_cat, this code is legacy only

"""
manages spikes in h5 files
giving access to clusters, groups etc
"""
from __future__ import print_function, division, absolute_import

import os
from glob import glob
from collections import namedtuple

import numpy as np
# pylint: disable=E1101
import tables  # this should be the only place all around that imports tables

from .. import TYPE_ART, SPIKE_MATCHED_2, TYPE_NAMES

SIGNS = ('pos', 'neg')
DEBUG = False
NO_EXIST_CHECK = True  # check whether image files exist on disk
EMPTY = np.array([])

H5Data = namedtuple('H5Data', ['spikes', 'times', 'artifacts'])


class DataManager(object):
    """
    represents a spike file
    """

    def __init__(self, h5fname, mode='r', cache=None):
        """
        mode: the opening mode of the h5file
        load_all: if True, load all spikes/times at init
        this makes further operation faster
        """

        self._h5file = tables.open_file(h5fname, mode)
        self._h5data = {}
        self.init_h5data(cache)

    def init_h5data(self, cache):
        """
        initializes h5data
        """
        def print_no_spikes(sign):
            """
            helper
            """
            print('No {} spikes'.format(sign))

        if cache is None:
            cache = []

        for sign in SIGNS:
            # it's a big difference in loading times to load
            # all spikes here with [:] or not!
            try:
                times = self._h5file.get_node('/' + sign, 'times')
            except tables.NoSuchNodeError:
                print_no_spikes(sign)
                continue

            if len(times.shape) == 0:
                print_no_spikes(sign)
                continue
            elif times.shape[0] == 0:
                print_no_spikes(sign)

            spikes = self._h5file.get_node('/' + sign, 'spikes')

            try:
                artifacts = self._h5file.get_node('/' + sign, 'artifacts')
            except tables.NoSuchNodeError:
                artifacts = None
                print('No artifacts defined')

            if 'spikes' in cache:
                spikes = spikes[:]
            if 'times' in cache:
                times = times[:]
            if 'artifacts' in cache:
                if artifacts is not None:
                    artifacts = artifacts[:]

            assert times.shape[0] == spikes.shape[0]

            self._h5data[sign] = H5Data(spikes, times, artifacts)

    def get_h5data(self, sign='pos'):
        """
        returns pointers to h5data
        """
        return self._h5data[sign]

    def get_data_by_name_and_index(self, name, index, sign='pos'):
        """
        read out actual data
        """
        if isinstance(index, str):
            if index == 'all':
                index = slice(None, None)

        if name == 'spikes':
            return self._h5data[sign].spikes[index, :]
        elif name == 'times':
            return self._h5data[sign].times[index]

        elif name == 'artifacts':
            return self._h5data[sign].artifacts[index]

        else:
            raise NotImplementedError('Field name {} not known')

    def get_non_artifact_index(self, sign='pos'):
        """
        return index of non-artifacts
        """
        artifacts = self._h5data[sign].artifacts

        if artifacts is None:
            num = self._h5data[sign].times.shape[0]
            idx = np.arange(num, dtype=np.uint32)

        else:
            idx = (self._h5data[sign].artifacts[:] == 0).nonzero()[0]
            num = idx.shape[0]

        return idx, num

    def __del__(self):
        self._h5file.close()


class SessionManager(object):
    """
    represents one sorting session
    """
    def __init__(self, session_dir):
        self.session_dir = session_dir
        h5fname = os.path.join(session_dir, 'sorting.h5')
        self.h5file = tables.open_file(h5fname, 'r+')

        # index and ident are always there
        self.index = None
        self.ident = None
        self.is_sorted = False  # default

        # these are there for sorted classes
        self.classes = None
        self.matches = None
        self.artifact_scores = None
        self.all_ids = None
        self.art_idx = None

        # and this is for session after global template matching
        self.global_matches = None

        self._init_session()

    def _init_session(self):
        """
        initializes parts of h5file
        data is copied to memory since it's small
        and needs to be accessed quickly
        changed data is written to file
        """
        # index and ident are always there
        self.index = self.h5file.root.index[:]
        self.ident = self.h5file.get_node_attr('/', 'ident')

        # the rest only for sorted sessions
        try:
            self.classes = self.h5file.root.classes[:]

        except tables.NoSuchNodeError:
            pass

        try:
            self.matches = self.h5file.root.matches[:]
        except tables.NoSuchNodeError:
            pass

        try:
            self.artifact_scores = self.h5file.root.artifact_scores[:]
        except tables.NoSuchNodeError:
            pass

        if True in [x is None for x in
                    (self.classes, self.matches, self.artifact_scores)]:
            self.is_sorted = False
        else:
            self.is_sorted = True
            print('Unsorted session, not loading sorting data')

        if self.artifact_scores is not None:
            self.all_ids = self.artifact_scores[:, 0]
            self.art_idx = self.artifact_scores[:, 1] != 0

        # this is only for template-matched sessions
        try:
            self.global_matches = self.h5file.root.global_matches[:]
        except tables.NoSuchNodeError:
            pass

    def update_classes(self, classes):
        """
        saves classes to file
        """
        self._update_node('classes', classes, np.uint16)
        self.classes = classes

    def _update_node(self, name, data, dtype):
        """
        updates a given node
        """
        try:
            self.h5file.remove_node('/', name)
            print('Updating ' + name)
        except tables.NoSuchNodeError:
            print('Creating ' + name)

        self.h5file.create_array('/', name, data.astype(dtype))

    def update_sorting_data(self, matches, artifact_scores):
        """
        creates new nodes for sorting data
        """

        job_data = (('matches', matches, np.uint8),
                    ('artifact_scores', artifact_scores, np.uint8))

        for job in job_data:
            self._update_node(job[0], job[1], job[2])

        self.matches = matches
        self.artifact_scores = artifact_scores

        self.is_sorted = True

    def get_class_index_by_classes(self, class_ids):
        """
        Returns the index that belongs to a list of classes.
        It points into the main array
        """
        if self.classes is not None:
            idx = np.in1d(self.classes, class_ids).nonzero()[0]
            return self.index[idx]
        else:
            return EMPTY

    def set_global_matches(self, matches):
        """
        Sets matches across sessions. Everything belonging
        to this session is stored here
        """
        self._update_node('global_matches', matches, np.uint32)

        # update our matches so that local template matches
        # don't appear anymore as non-matched
        match_type_changed_idx = np.in1d(self.index, matches)
        if self.matches is not None:
            self.matches[match_type_changed_idx] = SPIKE_MATCHED_2
            self._update_node('matches', self.matches, np.uint8)

    def get_global_matches_by_class(self, clid, start, stop):
        """
        Returns index of globally matched spikes between
        start and stop
        """
        if self.global_matches is None:
            return EMPTY
        else:
            idx = (self.global_matches[:, 0] >= start) &\
                  (self.global_matches[:, 0] <= stop) &\
                  (self.global_matches[:, 1] == clid)
            return self.global_matches[idx, :]

    def get_start_stop_index(self):
        """
        returns first and last index into main array
        """
        return (self.index[0], self.index[-1])

    def get_class_and_match_type(self, class_id, start, stop):
        """
        when interested in global matching
        """
        if self.classes is None:
            return EMPTY
        else:
            # first go for local spikes
            idx = self.classes == class_id
            spk_idx = self.index[idx]
            if self.matches is None:
                return spk_idx, None
            else:
                matches = self.matches[idx]

        if self.global_matches is None:
            return spk_idx, matches

        else:
            global_idx = self.get_global_matches_by_class(class_id,
                                                          start, stop)

            if not global_idx.shape[0]:
                return spk_idx, matches

            spk_idx = np.append(spk_idx, global_idx[:, 0])
            sort_idx = np.argsort(spk_idx)

            all_matches = np.zeros(matches.shape[0] + global_idx.shape[0],
                                   np.uint8)
            all_matches[:matches.shape[0]] = matches
            all_matches[matches.shape[0]:] = 2
            spk_idx = spk_idx[sort_idx]
            all_matches = all_matches[sort_idx]

        return spk_idx, all_matches

    def get_image_name_by_class_id(self, class_id):
        """
        generates the corresponding image name
        """
        fname = 'cluster_{:03d}.png'.format(class_id)
        fname_full = os.path.join(self.session_dir, fname)

        if NO_EXIST_CHECK:
            return fname_full

        if os.path.exists(fname_full):
            return fname_full

        else:
            print('File not found: ' + fname_full)
            return None

    def __del__(self):
        self.h5file.close()


class SortingManager(object):
    """
    represents an entire sorting directory
    """
    def __del__(self):
        if self.groups_h5f is not None:
            self.groups_h5f.close()

        for ses_man in self.session_mans:
            del ses_man

    def __init__(self, h5fname):
        self.basedir = os.path.dirname(h5fname)
        self.session_folders = {}
        self.session_groups = {}
        self.session_mans = {}
        self.group_types = {}
        self.groups_fname = os.path.join(self.basedir, 'groups.h5')
        self.datamanager = DataManager(h5fname)
        self.groups_h5f = None

        for sign in SIGNS:
            self.session_folders[sign] = []
            self.session_groups[sign] = []
            self.group_types[sign] = []
            self.session_mans[sign] = {}

        self.init_sessions()

    def init_sessions(self):
        """
        initialize lists of pos/neg sessions
        """
        for sign in SIGNS:
            pattern = os.path.join(self.basedir, 'sort_' + sign + '*')
            res = sorted(glob(pattern))
            if res:
                for cand in res:
                    if os.path.isdir(cand):
                        h5file = os.path.join(cand, 'sorting.h5')
                        if os.path.exists(h5file):
                            self.session_folders[sign].\
                                    append(os.path.basename(cand))

        # now for groups
        if not os.path.exists(self.groups_fname):
            # print('No groups found!')
            return

        self.groups_h5f = tables.open_file(self.groups_fname, 'r+')

        for sign in SIGNS:
            sessions = [ses for ses in self.groups_h5f.get_node('/' + sign)]
            for ses in sessions:
                if ses.name in self.session_folders[sign]:
                    self.session_groups[sign].append(ses.name)

            types = self.groups_h5f.get_node('/types_' + sign)
            self.group_types[sign] = types[:]

        if DEBUG:
            for sign in SIGNS:
                print('{} session folders: {}'.
                      format(sign, self.session_folders[sign]))
                print('{} session groups: {}'.
                      format(sign, self.session_groups[sign]))
                print('{} group types: {}'.
                      format(sign, self.group_types[sign]))

    def get_group_ids(self, sign='pos'):
        """
        ids of all groups
        """
        if self.group_types is not None:
            return self.group_types[sign][:, 0]
        else:
            print('called get_group_ids, but no groups loaded')

    def get_group_type(self, gid, sign='pos'):
        """
        get the type of a group
        """
        idx = self.group_types[sign][:, 0] == gid
        return self.group_types[sign][idx, 1][0]

    def get_groups_from_sessions(self, session_names, sign='pos'):
        """
        return a dictionary of all group ids with
        their class ids in given sessions
        """
        ret = {}
        for gid in self.group_types[sign][:, 0]:
            for ses_name in session_names:
                ses = self.groups_h5f.get_node('/' + sign + '/' + ses_name)[:]
                idx = ses[:, 1] == gid
                if idx.any():
                    if gid not in ret:
                        ret[gid] = []

                    ret[gid].append((ses_name, ses[idx, 0]))

        return ret

    def set_groups_for_session(self, session_name, clid, group, sign='pos'):
        """
        set groups in one session
        """
        ses = self.groups_h5f.get_node('/' + sign + '/' + session_name)
        # small sanity check:
        idx = (ses[:, 0] == clid).nonzero()[0]
        print(session_name, idx, group)
        ses[idx, 1] = group

#        self.groups_h5f.flush()

    def set_types(self, types, sign='pos'):
        """
        set group types
        """
        name = 'types_' + sign
        self.groups_h5f.remove_node('/' + name)
        self.groups_h5f.create_array('/', name, types)
        self.group_types[sign] = types
        self.groups_h5f.flush()

    def create_groups(self):
        """
        creates a h5 file to store groups across sessions
        """
        if self.groups_h5f is None:
            self.groups_h5f = tables.open_file(self.groups_fname, 'w')
            for sign in SIGNS:
                self.groups_h5f.create_group('/', sign)

            return self.groups_h5f

    def get_class_by_session_id(self, session_name, clid, sign='pos'):
        """
        retrieve a class
        """
        if session_name not in self.session_mans[sign]:
            ses_path = os.path.join(self.basedir, session_name)
            this_man = SessionManager(ses_path)
            self.session_mans[sign][session_name] = this_man
        else:
            this_man = self.session_mans[sign][session_name]

        idx = this_man.get_class_index_by_classes(clid)
        fname = this_man.get_image_name_by_class_id(clid)

        return idx, fname

    def get_data_by_name_and_index(self, name, index, sign='pos'):
        """
        given an index, returns data
        """
        return self.datamanager.get_data_by_name_and_index(name, index, sign)

    def get_h5data(self, sign='pos'):
        """
        return all h5data
        """
        return self.datamanager.get_h5data(sign)

    def get_samples_per_spike(self, sign):
        """
        return number of sampling points
        """
        return self.get_h5data(sign).spikes.shape[1]

    def clusters_from_sessions(self, sessions, sign='pos',
                               skip_artifacts=True, stack=True):
        """
        return a dictionary of groups from the indicated sessions
        """
        group_data = self.get_groups_from_sessions(sessions, sign)
        ret = {}
        all_min = np.Inf
        all_max = 0

        for gid, data in group_data.items():
            group_type = self.get_group_type(gid, sign)

            if skip_artifacts and (group_type == TYPE_ART):
                continue

            ret[gid] = {}
            ret[gid]['type'] = group_type
            ret[gid]['images'] = []
            ret[gid]['clids'] = []
            index = []

            for ses_name, clids in data:
                for clid in clids:
                    idx, fname = self.\
                            get_class_by_session_id(ses_name, clid, sign)
                    all_min = min(idx.min(), all_min)
                    all_max = max(all_max, idx.max())
                    index.append(idx)
                    ret[gid]['images'].append(fname)
                    ret[gid]['clids'].append(clid)

            if stack:
                ret[gid]['index'] = np.hstack(index)
            else:
                ret[gid]['index'] = index

        return ret, all_min, all_max


def test_one():
    """
    simple test case
    """
    import sys
    name = sys.argv[1]
    sorting_man = SortingManager(name)
    ses_names = sorting_man.session_groups['pos']
    print(ses_names)
    gids = sorting_man.get_group_ids()
    print(gids)
    group_data = sorting_man.get_groups_from_sessions(ses_names, 'pos')

    for gid, data in group_data.items():
        group_type = sorting_man.get_group_type(gid, 'pos')
        print(gid, TYPE_NAMES[group_type])
        for ses_name, clids in data:
            print(ses_name)
            for clid in clids:
                idx, fname = sorting_man.\
                        get_class_by_session_id(ses_name, clid, 'pos')
                print(len(idx), fname)

if __name__ == "__main__":
    test_one()
