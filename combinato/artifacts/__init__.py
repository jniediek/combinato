"""
just for export
"""
from __future__ import print_function, division, absolute_import
id_to_name = {}
from .mask_artifacts import options_by_diff,\
                           options_by_height, options_by_bincount

artifact_types = (options_by_diff, options_by_height, options_by_bincount)

for options in artifact_types: 
    id_to_name[options['art_id']] = options['name']
