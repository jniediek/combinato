# JN 2015-01-11
"""
main program for spike sorting
"""

from __future__ import print_function, division, absolute_import
import os
import numpy as np
# pylint:   disable=E1101
from .. import SortingManager, SessionManager, options
from time import strftime
from getpass import getuser

import matplotlib.pyplot as mpl

from .wave_features import wavelet_features
from .select_features import select_features
from .define_clusters import define_clusters
from .cluster_features import cluster_features, read_results
from .dist import template_match
from .artifacts import find_artifacts
from .plot_temp import plot_temperatures


USER = getuser()
LOG_FNAME = 'log.txt'
FIRST_MATCH_FACTOR = options['FirstMatchFactor']


def features_to_index(features, folder, name, overwrite=True):
    """
    wrapper function
    """
    clu = None

    if not overwrite:
        try:
            clu, tree = read_results(folder, name)
            print('Read clustering results from ' + folder)
        except IOError:  # as error:
            print('Starting clustering ')
            # + error.strerror + ': ' + error.filename)
            overwrite = True

    if clu is not None:
        if features.shape[0] != clu.shape[1] - 2:
            print('Read outdated clustering, restarting')
            overwrite = True

    if overwrite:
        feat_idx = select_features(features)
        print('Clustering data in {}/{}'.format(folder, name))
        cluster_features(features[:, feat_idx], folder, name)
        now = strftime('%Y-%m-%d_%H-%M-%S')

        log_fname = os.path.join(folder, LOG_FNAME)
        with open(log_fname, 'a') as fid_done:
            fid_done.write('{} {} ran {}\n'.format(now, USER, name))
        fid_done.close()

        clu, tree = read_results(folder, name)

    idx, tree, used_points = define_clusters(clu, tree)
    return idx, tree, used_points


def cluster_step(features, folder, sub_name, overwrite):
    """
    one step in clustering
    """

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
        print('Cluster step {} returned'.format(sub_name))
        for clid in np.unique(res_idx):
            print('{}: {} spikes'.format(clid, (res_idx == clid).sum()))

    return res_idx


def iterative_sorter(features, spikes, n_iterations, name, overwrite=True):
    """
    name is used to generate temporary filenames
    """
    idx = np.zeros(features.shape[0], np.uint16)
    match_idx = np.zeros(features.shape[0], bool)

    for i in range(n_iterations):

        # input to clustering are the spikes that have no index so far
        sub_idx = idx == 0

        sub_name = 'sort_' + str(i)

        if sub_idx.sum() < options['MinInputSize']:
            if options['Debug']:
                print('Stopping iteration, {} spikes left'
                      .format(sub_idx.sum()))
            break

        if options['Debug']:
            print('Clustering {} spikes'.format(sub_idx.sum()))

        # res_idx contains a number for each cluster generated from clustering
        res_idx = cluster_step(features[sub_idx], name, sub_name, overwrite)

        if options['Debug']:
            print('Iteration {}, new classes: {}'.
                  format(i, np.unique(res_idx)))
            print('Iteration {}, old classes: {}'.format(i, np.unique(idx)))

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
                        print('Not reclustering cluster {} ({} spikes)'
                              .format(clid, cluster_size))
                    continue

                else:
                    if options['Debug']:
                        print('Reclustering cluster {} ({} spikes)'
                              .format(clid, cluster_size))

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
    n_iterations = options['RecursiveDepth']
    if options['Debug']:
        print('Recursive depth is {}.'.format(n_iterations))

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
    sort_man = SortingManager(data_fname)
    session = SessionManager(session_fname)
    idx = session.index
    spikes = sort_man.get_data_by_name_and_index('spikes', idx, sign)
    sort_idx, match_idx, artifact_ids =\
        sort_spikes(spikes, session.session_dir,
                    overwrite=overwrite, sign=sign)

    all_ids = np.unique(sort_idx)

    artifact_scores = np.zeros((len(all_ids), 2), np.uint8)
    artifact_scores[:, 0] = all_ids

    for cl_id in all_ids:
        idx = artifact_scores[:, 0] == cl_id
        artifact_score = 1 if cl_id in artifact_ids else 0
        artifact_scores[idx, 1] = artifact_score

    session.update_classes(sort_idx)
    session.update_sorting_data(match_idx, artifact_scores)


def sort_helper(args):
    """
    usual multiprocessing helper, used to un
    """
    main(args[0], args[2], args[1], options['overwrite'])


def write_options(fname='css-cluster-log.txt'):
    """
    save options to log file
    """
    print('Writing options to file {}'.format(fname))
    msg = strftime('%Y-%m-%d_%H-%M-%S') + ' ' + USER + '\n'

    for key in sorted(options.keys()):
        if key in ['density_hist_bins', 'cmap']:
            continue
        msg += '{}: {}\n'.format(key, options[key])

    msg += 60 * '-' + '\n'

    with open(fname, 'a') as fid:
        fid.write(msg)

    fid.close()


def test_joblist(joblist):
    """
    simple test to detect whether the same job is
    requested more than once
    """
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
                print('Job {} requested {} times'.format(key, val))
        raise ValueError('Duplicate jobs requested')


def argument_parser():
    """
    standard argument parsing
    """
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

    # possibilities:
    # 1) jobs is supplied, and neither datafile nor session
    # 2) datafile and sessions are supplied

    args = parser.parse_args()

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

    print('Starting {} jobs with {} workers'.
          format(len(joblist), n_cores))

    write_options()

    if n_cores == 1:
        [sort_helper(job) for job in joblist]

    else:
        pool = Pool(n_cores)
        pool.map(sort_helper, joblist)
