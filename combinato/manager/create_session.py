# JN 2015-01-09
"""
create a new folder for sorting
"""
from __future__ import print_function, division, absolute_import
import os
import numpy as np
import tables


def _set_attrs(h5file, attrs):
    """
    helper
    """
    for key, val in attrs.items():
        h5file.set_node_attr('/', key, val)


def create_session(folder, sign, label, index, replace=False):
    """
    creates a new sorting session
    """

    session_name = 'sort_{}_{}_{:07d}_{:07d}'.format(sign,
                                                     label,
                                                     index[0],
                                                     index[-1])

    session_dir = os.path.join(folder, session_name)

    if not os.path.isdir(session_dir):
        os.mkdir(session_dir)

    data_fname = os.path.join(session_dir, 'sorting.h5')

    if os.path.exists(data_fname) and not replace:
        print('Not replacing ' + data_fname)

    h5fid = tables.open_file(data_fname, 'w')
    h5fid.create_array('/', 'index', index.astype(np.uint32))
    attrs = {'ident': session_name}
    _set_attrs(h5fid, attrs)
    h5fid.close()
    return session_name
