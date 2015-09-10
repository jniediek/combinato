# JN 2015-01-11
# refactoring
from __future__ import print_function, division, absolute_import

import os
import time
import subprocess
import numpy as np
#   pylint:disable=E1101

from .. import options


# Debugging options
DO_CLEAN = True
DO_RUN = True
DO_TIMING = True

EXT_CL = ('.dg_01', '.dg_01.lab')
EXT_TMP = ('.mag', '.mst11.edges', '.param', '_tmp_data', '_cluster.run')


def _cleanup(base, ext):
    """
    helper function, deletes all files with names 'base + ext'
    """
    for this_ext in ext:
        name = base + this_ext
        if os.path.exists(name):
            os.remove(name)


def cluster_features(features, folder, name):
    """
    folder to store temporary files
    name to generate temporary file names
    returns whether it ran
    """

    if not os.path.isdir(folder):
        os.mkdir(folder)

    cleanname = os.path.join(folder, name)

    if DO_CLEAN:
        _cleanup(cleanname, EXT_CL)

    data_fname = name + "_tmp_data"
    datasavename = os.path.join(folder, data_fname)

    np.savetxt(datasavename, features, newline='\n', fmt="%f")

    argument_fname = name + "_cluster.run"
    run_fname = os.path.join(folder, argument_fname)

    with open(run_fname, "w") as fid:
        fid.write('NumberOfPoints: %i\n' % features.shape[0])
        fid.write('DataFile: %s\n' % data_fname)
        fid.write('OutFile: %s\n' % name)
        fid.write('Dimensions: %s\n' % features.shape[1])
        fid.write('MinTemp: 0\n')
        fid.write('MaxTemp: 0.201\n')
        fid.write('TempStep: %f\n' % options['TempStep'])
        fid.write('SWCycles: 100\n')
        fid.write('KNearestNeighbours: 11\n')
        fid.write('MSTree|\n')
        fid.write('DirectedGrowth|\n')
        fid.write('SaveSuscept|\n')
        fid.write('WriteLables|\n')
        fid.write('WriteCorFile~\n')
        fid.write('ForceRandomSeed: %f\n' % np.random.random())
        # fid.write('ForceRandomSeed: 0')

    fid.close()

    if options['ShowSPCOutput']:
        out = None
    else:
        out = subprocess.PIPE

    if DO_RUN:
        if DO_TIMING:
            t1 = time.time()
        ret = subprocess.call((options['ClusterPath'], argument_fname),
                              stdout=out,
                              cwd=folder)
        if DO_TIMING:
            dt = time.time() - t1
    else:
        ret = 0

    if ret:
        raise Exception('Error in Clustering: ' + name)

    if DO_TIMING:
        with open(os.path.join(folder, 'cluster_log.txt'), 'a') as log_fid:
            log_fid.write('clustered {} spikes in {:.6f} s'.
                          format(features.shape[0], dt))

    if DO_CLEAN:
        _cleanup(cleanname, EXT_TMP)

    return ret


def read_results(folder, name):
    """
    reads in cluster results
    """
    tree_fname = os.path.join(folder, name + '.dg_01')
    clu_fname = os.path.join(folder, name + '.dg_01.lab')

    tree = np.loadtxt(tree_fname)
    clu = np.loadtxt(clu_fname)

    return clu, tree


def testit():
    """
    just a test
    """
    part1 = np.random.normal(0, 1, (250, 10))
    part2 = np.random.normal(2, 1, (100, 10))
    part3 = np.random.normal(6, 2, (20, 10))
    data = np.vstack([part1, part2, part3])
    ndata = data.shape[0]

    ret = cluster_features(data, 'test', 'testdata')
    assert ret == 0
    clu, tree = read_results('test', 'testdata')
    assert clu.shape[1] == ndata + 2
    return clu, tree

if __name__ == "__main__":
    testit()
