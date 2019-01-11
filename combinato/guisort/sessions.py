"""
Sessions class for sorting sessions for guisort
"""

from __future__ import print_function, division, absolute_import
import numpy as np
from .cluster import Cluster
from .group_list_model import GroupListModel
from .. import GROUP_ART, GROUP_NOCLASS, TYPE_MU, TYPE_ART, TYPE_NO

class Sessions(object):
    """
    represents a collection of opened sessions
    """
    def __init__(self, parent=None):
        self.dirty = False
        self.sorting_manager = parent.sorting_manager
        self.group_table = self.sorting_manager.get_group_table()
        self.type_table = self.sorting_manager.get_type_table()

        self.start_time = np.inf
        self.stop_time = 0

        self.groupsById = {}
        self._init_clusters()

    def _init_clusters(self):
        """
        initialize all groups and clusters for this specific session
        """

        groups = self.sorting_manager.get_groups()

        if GROUP_ART not in groups:
            print('Adding empty artifact group')
            model = GroupListModel('Artifacts', GROUP_ART, [], TYPE_ART)
            self.groupsById[GROUP_ART] = model
            self.type_table = np.vstack(([GROUP_ART, TYPE_ART],
                                         self.type_table))

        if GROUP_NOCLASS not in groups:
            print('Adding empty noclass group')
            model = GroupListModel('Unassigned', GROUP_NOCLASS, [], TYPE_NO)
            self.groupsById[GROUP_NOCLASS] = model

        for gid, data in groups.items():

            if not len(data):
                continue

            group_type = self.sorting_manager.get_group_type(gid)

            if gid == GROUP_ART:
                name = 'Artifacts'
            elif gid == GROUP_NOCLASS:
                name = 'Unassigned'
            else:
                name = str(gid)

            model = GroupListModel(name, gid, [], group_type)
            tmp_clusters = []

            for clid, clus in data.items():
                times = clus['times']
                spikes = clus['spikes']
                fname = clus['image']
                clu = Cluster(clid, fname, spikes, times)
                tmp_clusters.append(clu)
                self.start_time = min(self.start_time, times[0])
                self.stop_time = max(self.stop_time, times[-1])

            model.addClusters(tmp_clusters)

            self.groupsById[gid] = model

        self.updateGroupsByName()

    def updateGroupsByName(self):
        self.groupsByName = {}
        for group in self.groupsById.values():
            self.groupsByName[group.name] = group

    def save(self):
        """
        save the sorting result to file
        """
        # update our group table

        for group_id, group in self.groupsById.items():
            idx_type = self.type_table[:, 0] == group_id
            self.type_table[idx_type, 1] = group.group_type

            for cluster in group.clusters:
                idx_cl = self.group_table[:, 0] == cluster.name
                self.group_table[idx_cl, 1] = group_id

        self.sorting_manager.save_groups_and_types(self.group_table,
                                                   self.type_table)

    def newGroup(self):

        keys = self.type_table[:, 0]

        for newkey in range(1, 1000):
            if newkey not in keys:
                self.groupsById[newkey] = GroupListModel(str(newkey),
                                                         newkey, [], TYPE_MU)
                print('Added group {}'.format(newkey))
                break

        self.type_table = np.vstack((self.type_table, [newkey, TYPE_MU]))

        self.updateGroupsByName()

    def reorganize_groups(self):
        """
        rename groups by group size, delete empty groups
        """
        # get group sizes
        sizes = [] 
        for gid, group in self.groupsById.items():
            if gid not in (GROUP_ART, GROUP_NOCLASS):
                sz = len(group.times)
                if sz:
                    sizes.append((len(group.times), gid))

        sizes.sort(reverse=True)
        new_groups = {}
        new_groups[GROUP_ART] = self.groupsById[GROUP_ART]
        new_groups[GROUP_NOCLASS] = self.groupsById[GROUP_NOCLASS]

        for pre_new_gid, (size, gid) in enumerate(sizes):
            new_gid = pre_new_gid + 1
            print("{} -> {} ({})".format(gid, new_gid, size))
            group = self.groupsById[gid] 
            group.name = str(new_gid)
            group.groupId = new_gid
            new_groups[new_gid] = group

        self.groupsById = new_groups
        self.updateGroupsByName()
