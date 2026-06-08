# JN 2015-01-11
"""
main program for spike sorting
"""

from __future__ import print_function, division, absolute_import
import os
import math
from time import strftime
import numpy as np
import logging

logger = logging.getLogger(__name__)

# pylint:   disable=E1101
from .. import SortingManager, SessionManager, options

import matplotlib.pyplot as mpl

from .wave_features import wavelet_features
from .select_features import select_features
from .define_clusters import define_clusters
from .cluster_features import cluster_features, read_results
from .dist import template_match
from .artifacts import find_artifacts
from .plot_temp import plot_temperatures
from .handle_random_seed import handle_random_seed


FIRST_MATCH_FACTOR = options['FirstMatchFactor']
SEED = None


def features_to_index(features, folder, name, overwrite=True):
    """
    wrapper function
    """
    # logger.debug('features_to_index called: folder=%s, name=%s', folder, name)  # Log function cal

    # Handle seed incase the entry point is not argument_parser
    global SEED
    if SEED is None:
        SEED = handle_random_seed()

    clu = None

    if not overwrite:
        try:
            clu, tree = read_results(folder, name)
            logger.info('Read clustering results from %s', folder)
        except IOError:
            logger.info('Starting clustering in %s', folder)
            overwrite = True

    if clu is not None:
        if features.shape[0] != clu.shape[1] - 2:
            logger.info('Read outdated clustering, restarting')
            overwrite = True

    if overwrite:
        feat_idx = select_features(features)
        logger.info('Clustering data in %s/%s', folder, name)

        cluster_features(features[:, feat_idx], folder, name, SEED)

        logger.info('Clustering run completed: folder=%s, name=%s', folder, name)

        clu, tree = read_results(folder, name)

    idx, tree, used_points = define_clusters(clu, tree)
    return idx, tree, used_points


def cluster_step(features, folder, sub_name, overwrite):
    """
    one step in clustering
    """
    # logger.debug('cluster_step called: sub_name=%s', sub_name)  # Log function call

    res_idx, tree, used_points = features_to_index(features,
                                                   folder,
                                                   sub_name,
                                                   overwrite)
    # save temperature plot here if wanted
    if options['plotTemps']:
        temp_fig = plot_temperatures(tree, used_points)
        temp_fname = os.path.join(folder, 'temp_' + sub_name + '.png')
        temp_fig.savefig(temp_fname)
        mpl.close(temp_fig)

    if options['Debug']:
        logger.debug('Cluster step %s returned', sub_name)
        for clid in np.unique(res_idx):
            logger.debug('  %d: %d spikes', clid, (res_idx == clid).sum())

    return res_idx


def iterative_sorter(features, spikes, n_iterations, name, overwrite=True):
    """
    name is used to generate temporary filenames
    """ 
    # logger.debug('iterative_sorter called: name=%s, n_iterations=%d, n_spikes=%d',
    #              name, n_iterations, features.shape[0]) # Log function call

    idx = np.zeros(features.shape[0], np.uint16)
    match_idx = np.zeros(features.shape[0], bool)

    for i in range(n_iterations):

        # input to clustering are the spikes that have no index so far
        sub_idx = idx == 0

        sub_name = 'sort_' + str(i)

        if sub_idx.sum() < options['MinInputSize']:
            if options['Debug']:
                logger.debug('Stopping iteration, %d spikes left', sub_idx.sum())
            break

        if options['Debug']:
            logger.debug('Clustering %d spikes', sub_idx.sum())

        # res_idx contains a number for each cluster generated from clustering
        res_idx = cluster_step(features[sub_idx], name, sub_name, overwrite)

        if options['Debug']:
            logger.debug('Iteration %d, new classes: %s', i, np.unique(res_idx))
            logger.debug('Iteration %d, old classes: %s', i, np.unique(idx))

        clustered_idx = res_idx > 0
        prev_idx_max = idx.max()
        res_idx[clustered_idx] += prev_idx_max
        idx[sub_idx] = res_idx
        # now idx contains the new spike numbers

        # feed new, sufficiently big clusters into clustering again
        # (to reduce under-clustering)
        if options['ReclusterClusters']:
            clids = np.unique(res_idx[clustered_idx])

            for clid in clids:
                recluster_idx = idx == clid
                cluster_size = recluster_idx.sum()

                if cluster_size < options['MinInputSizeRecluster']:
                    if options['Debug']:
                        logger.debug('Not reclustering cluster %d (%d spikes)',
                                     clid, cluster_size)
                    continue

                else:
                    if options['Debug']:
                        logger.debug('Reclustering cluster %d (%d spikes)',
                                     clid, cluster_size)

                sub_sub_name = '{}_{:02d}'.format(sub_name, clid)

                recluster_res_idx = cluster_step(features[recluster_idx],
                                                 name, sub_sub_name, overwrite)

                # make sure to increase the cluster numbers enough
                biggest_clid = idx.max()
                recluster_res_idx[recluster_res_idx != 0] += biggest_clid
                idx[recluster_idx] = recluster_res_idx

        # conservative template matching here
        template_match(spikes, idx, match_idx, FIRST_MATCH_FACTOR)

    return idx, match_idx


def sort_spikes(spikes, folder, overwrite=False, sign='pos'):
    """
    function organizes code
    """
    # logger.debug('sort_spikes called: folder=%s, sign=%s', folder, sign)    # Log function call

    n_iterations = options['RecursiveDepth']
    if options['Debug']:
        logger.debug('Recursive depth is %d.', n_iterations)

    # it is suboptimal that we calculate the features
    # even when reading clusters from disk
    all_features = wavelet_features(spikes)

    # sorting includes template match
    sorted_idx, match_idx = iterative_sorter(all_features, spikes,
                                             n_iterations, folder,
                                             overwrite=overwrite)

    # identify artifact clusters
    class_ids = np.unique(sorted_idx)

    if options['MarkArtifactClasses']:
        invert = True if sign == 'neg' else False
        _, artifact_ids = find_artifacts(spikes, sorted_idx, class_ids, invert)
    else:
        artifact_ids = []

    return sorted_idx, match_idx, artifact_ids


def main(data_fname, session_fname, sign, overwrite=False):
    """
    sort spikes from given session
    """
    # logger.debug('main called: data=%s, session=%s, sign=%s',
    #              data_fname, session_fname, sign)   # Log function call

    sort_man = SortingManager(data_fname)
    session = SessionManager(session_fname)
    idx = session.index
    spikes = sort_man.get_data_by_name_and_index('spikes', idx, sign)
    sort_idx, match_idx, artifact_ids =\
        sort_spikes(spikes, session.session_dir,
                    overwrite=overwrite, sign=sign)

    # Write random seed to session folder for reproducibility
    seed_file = os.path.join(session.session_dir, 'random_seed.txt')
    with open(seed_file, 'a') as f:
        f.write('{} | {}\n'.format(strftime('%Y-%m-%d_%H-%M-%S'), SEED))

    all_ids = np.unique(sort_idx)

    artifact_scores = np.zeros((len(all_ids), 2), np.uint8)
    artifact_scores[:, 0] = all_ids

    for cl_id in all_ids:
        idx = artifact_scores[:, 0] == cl_id
        artifact_score = 1 if cl_id in artifact_ids else 0
        artifact_scores[idx, 1] = artifact_score

    session.update_classes(sort_idx)
    session.update_sorting_data(match_idx, artifact_scores)
    session.h5file.close()


def sort_helper(args):
    """
    usual multiprocessing helper, used to un
    """
    # logger.debug('sort_helper called: %s', args)    # Log function call

    main(args[0], args[2], args[1], options['overwrite'])


def write_options():
    """
    Log all current clustering options.
    """
    # logger.debug('write_options called')    # Log function call

    # Remove old session_random_seeds.txt if exists (legacy cleanup)
    if os.path.exists('session_random_seeds.txt'):
        os.remove('session_random_seeds.txt')
        logger.info('Old session_random_seeds.txt has been deleted.')

    logger.info('Clustering options:')
    for key in sorted(options.keys()):
        if key in ('density_hist_bins', 'cmap'):
            continue
        logger.info('  %s: %s', key, options[key])


def test_joblist(joblist):
    """
    simple test to detect whether the same job is
    requested more than once
    """
    # logger.debug('test_joblist called: %d jobs', len(joblist))   # Log function call

    unique_joblist = set(joblist)
    if len(joblist) != len(unique_joblist):
        # there are duplicates!
        counter = dict()
        for item in joblist:
            if item in counter:
                counter[item] += 1
            else:
                counter[item] = 1

        for key, val in counter.items():
            if val > 1:
                logger.warning('Job %s requested %d times', key, val)
        raise ValueError('Duplicate jobs requested')


def argument_parser():
    """
    standard argument parsing
    """
    # logger.debug('argument_parser called')   # Log function call

    from argparse import ArgumentParser, FileType, ArgumentError
    from multiprocessing import Pool, cpu_count
    parser = ArgumentParser('css-cluster',
                            description='Combinato Spike Sorter. This is the'
                                        ' main clustering executable. Specify'
                                        ' either a jobfile or datafile and '
                                        'sessions.',
                            epilog='Johannes Niediek (jonied@posteo.de)')
    parser.add_argument('--jobs', type=FileType('r'))
    parser.add_argument('--datafile', nargs=1)
    parser.add_argument('--sessions', nargs='+')
    parser.add_argument('--single', default=False, action='store_true')
    parser.add_argument('--rng', type=float, default=None, help='Random seed for clustering')

    # possibilities:
    # 1) jobs is supplied, and neither datafile nor session
    # 2) datafile and sessions are supplied

    args = parser.parse_args()

    # Use the passed seed if provided, otherwise generate one
    global SEED
    if args.rng is None or math.isnan(args.rng):
        SEED = handle_random_seed()
    else:
        SEED = handle_random_seed(args.rng)


    if args.jobs is None:
        if None in (args.datafile, args.sessions):
            raise ArgumentError(args.jobs,
                                'Specify either jobs or datafile and sessions')
        else:
            joblist = []
            for session in args.sessions:
                sign = 'neg' if 'neg' in session else 'pos'
                joblist.append([args.datafile[0], sign, session])
    else:
        jobdata = args.jobs.read().splitlines()
        joblist = tuple((tuple(line.split()) for line in jobdata))
        test_joblist(joblist)

    n_cores = 1 if args.single else cpu_count() + 1

    logger.info('Starting %d jobs with %d workers', len(joblist), n_cores)

    write_options()

    if n_cores == 1:
        [sort_helper(job) for job in joblist]

    else:
        pool = Pool(n_cores)
        pool.map(sort_helper, joblist)
