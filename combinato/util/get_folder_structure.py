# JN 2015-04-24
"""
read out the structure of a sorting folder
"""
from __future__ import division, print_function, absolute_import
import os
import glob
from .. import options


def check_folder(dirname, data_only=False):
    """
    check whether there is a file data_*.h5 and sorting_*h5
    if data_only == True, only check whether a h5 file exists
    """
    datafiles = glob.glob(os.path.join(dirname, 'data_*.h5'))
    if not len(datafiles):
        return None
    else:
        datafile = os.path.basename(datafiles[0])

    sort_files = []

    if data_only:
        return datafile, sort_files

    sort_folders = glob.glob(os.path.join(dirname, 'sort_???_*'))
    for cand in sort_folders:
        if os.path.exists(os.path.join(cand, 'sort_cat.h5')):
            sort_files.append(os.path.basename(cand))

    return datafile, sort_files


def get_relevant_folders(path, data_only=False):
    """
    find all folders that contain a data_*.h5 and sort directories
    """
    patterns = options['folder_patterns']
    candidates = list()
    for pat in patterns:
        candidates += glob.glob(os.path.join(path, pat))

    ret = list()
    for cand in candidates:
        if os.path.isdir(cand):
            res = check_folder(cand, data_only)
            if res is not None:
                if data_only:
                    ret.append((cand, res[0]))
                else:
                    for item in res[1]:
                        ret.append((cand, res[0], item))

    return sorted(ret)


def get_time_files(path):
    """
    find time definitions
    """
    timefiles = glob.glob(os.path.join(path, '*_ts.txt'))
    timefiles += glob.glob(os.path.join(path, 'times.txt'))

    ret = []

    for fname in timefiles:
        with open(fname, 'r') as fid:
            try:
                start, stop = map(int, fid.readline().split())
            except ValueError as error:
                print(fname, error.message)
                continue
            ret.append((fname, start, stop))
    return ret


def test():
    print(get_relevant_folders(os.getcwd()))
    print(get_time_files(os.getcwd()))
