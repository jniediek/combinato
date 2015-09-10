# JN 2015-02-09 refactoring
"""
These functions allow for fast and convenient access to clusters
"""
from __future__ import print_function, division, absolute_import
import numpy as np

def get_data_from_sessions(sorting_man, sessions,\
        sign='pos', items=None, skip_artifacts=True, stack=True):
    """
    retrieve data from a given list of sessions
    """
    groups, all_min, all_max = sorting_man.\
            clusters_from_sessions(sessions, sign, skip_artifacts, stack)

    if (all_min == np.Inf) or (all_max == 0):
        return None

    data = {}

    if items is None:
        return

    if 'times' in items:
        data['times'] = sorting_man.get_h5data(sign).times[all_min:all_max + 1]

    if 'spikes' in items:
        data['spikes'] = sorting_man.get_h5data(sign).\
                    spikes[all_min:all_max + 1]

    if stack:
        for item in items:
            for group in groups.values():
                group[item] = data[item][group['index'] - all_min]
    else:
        for item in items:
            for group in groups.values():
                group[item] = []
                for idx in group['index']:
                    group[item].append(data[item][idx - all_min])


    return groups


def get_times_from_sessions(sorting_man, sessions,
                            sign='pos', skip_artifacts=True):
    """
    retrieve index first, then times. This is just a renamed function.
    """
    return get_data_from_sessions(sorting_man, sessions,
                                  sign, ['times'], skip_artifacts)

def test(fname):
    """
    simple test case
    """
    from .manager import SortingManager
    sorting_man = SortingManager(fname)
    ses_names = sorting_man.session_groups['pos']
    groups = get_times_from_sessions(sorting_man, ses_names, 'pos')
    groups_full = get_data_from_sessions(sorting_man, ses_names, 'pos',\
            items=['spikes', 'times'])
    print(groups)
    print(groups_full)


if __name__ == "__main__":
    import sys
    test(sys.argv[1])
