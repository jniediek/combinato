# -*- encoding: utf-8 -*-
# last change: 2015-07-27, dynamic ylim in plots
# JN 2015-04-15
"""
reads out all clusters from sessions and puts them into one file
for final grouping
"""
from __future__ import print_function, division, absolute_import
import os
import numpy as np
#   pylint: disable=E1101
import tables
from multiprocessing import Pool, cpu_count

import matplotlib.pyplot as mpl

from .. import SessionManager, SortingManager, options, SPIKE_MATCHED_2,\
    CLID_UNMATCHED, SPIKE_MATCHED, SPIKE_CLUST

from .dist import distances_euclidean, get_means
from .create_groups import main as create_groups_main
from .artifacts import find_artifacts
from .cluster import test_joblist

COL_CLASS = 0
COL_GROUP = 1
COL_MATCH_TYPE = 2

ORIG_COLOR = '#0000ff'
MATCH_COLOR = '#00aaff'
MATCH_COLOR_2 = '#ff7700'

# status printout
MSG = True

plotdata = ((SPIKE_MATCHED_2, MATCH_COLOR_2),
            (SPIKE_MATCHED, MATCH_COLOR),
            (SPIKE_CLUST, ORIG_COLOR))


def read_all_info(managers):
    """
    reads clustering and matches from all sessions
    num is the total number of spikes to deal with
    """

    # find size of index to be generated
    man_names = sorted(managers)
    num = 0
    for ses in man_names:
        num += managers[ses].index.shape[0]

    sorted_index = np.zeros(num, dtype=np.uint32)
    sorted_info = np.zeros((num, 4), dtype=np.int16)

    curr_idx = 0
    old_max_class = 0
    artifact_scores = [[0, 0]]

    for ses in man_names:
        man = managers[ses]
        t_size = man.index.shape[0]
        sorted_index[curr_idx:curr_idx+t_size] = man.index
        overfull = (np.diff(sorted_index[:curr_idx+t_size]) == 0).sum()
        if overfull:
            print(ses, overfull, "ALARM")
        t_classes = man.classes
        print("Working on {}".format(man.h5file.filename))
        idx = t_classes != 0
        t_classes[idx] += old_max_class
        t_arti = man.artifact_scores.astype(np.int16)
        if t_arti[0, 0] == CLID_UNMATCHED:
            t_arti = t_arti[1:, :]
        t_arti[:, 0] += old_max_class
        artifact_scores.append(t_arti)
        sorted_info[curr_idx:curr_idx + t_size, COL_CLASS] = t_classes
        sorted_info[curr_idx:curr_idx + t_size, COL_MATCH_TYPE] = man.matches
        curr_idx += t_size
        old_max_class = t_classes.max()
        print('Read {} spikes from {}'.format(t_size, ses))

    return sorted_index, sorted_info, np.vstack(artifact_scores)


def write_sorting_file(h5fname, sorted_index, sorted_info, artifacts):
    """
    store total sorting data in h5file
    """
    data = (('classes', COL_CLASS, np.uint16),
            ('groups', COL_GROUP, np.int8),
            ('matches', COL_MATCH_TYPE, np.int8))

    fid = tables.open_file(h5fname, 'w')
    print('Writing index')
    fid.create_array('/', 'index', sorted_index)

    for name, col, atom in data:
        print('Writing ' + name)
        fid.create_array('/', name, sorted_info[:, col].astype(atom))

    print('Writing distance')
    fid.create_array('/', 'distance',
                     np.zeros(sorted_index.shape[0], np.float32))

    if options['RecheckArtifacts']:
        msg = 'Storing original artifacts, will be re-checked'
        name = 'artifacts_prematch'
        art_array = artifacts.copy()
        art_array[:, 1] = 0
        fid.create_array('/', 'artifacts', art_array)
    else:
        msg = 'Writing artifacts'
        name = 'artifacts'

    print(msg)
    fid.create_array('/', name, artifacts)
    fid.close()


def collect_sorting(fname, signs, sessions, outfname):
    """
    collect sorting into one h5 file outfname
    """
    # create grouping file

    basedir = os.path.dirname(fname)
    sort_man = SortingManager(fname)
    ses_mans = {}

    for ses in sessions:
        ses_mans[ses] = SessionManager(os.path.join(basedir, ses))

    print('Starting read from {}'.format(fname))
    sorted_index, sorted_info, artifacts = read_all_info(ses_mans)

    # write to file so that we can continue from that file
    write_sorting_file(outfname, sorted_index, sorted_info, artifacts)
    for ses, man in ses_mans.items():
        del man

    return sort_man


def total_match(fid, all_spikes):
    """
    read classes from h5file and match unmatched spikes
    this repeats the function from cluster/dist.py, sorry for the bad style
    """
    classes = fid.root.classes[:]

    print('classes: {}, all_spikes: {}'.format(classes.shape,
                                               all_spikes.shape))

    ids, mean_array, stds = get_means(classes, all_spikes)
    if not len(ids):
        return fid.root.classes[:], fid.root.matches[:]
    unmatched_idx = (classes == CLID_UNMATCHED).nonzero()[0]
    # unmatched_spikes = all_spikes[unmatched_idx]

    # JN 2016-09-08: For spike counts greater 10^6, this becomes a memory problem
    # the procedure should be done in batches of 50,000 spikes
    blocksize =  50*1000
    n_unmatched = unmatched_idx.shape[0]
    starts = np.arange(0, n_unmatched, blocksize)
    if not len(starts):
        starts = np.array([0])
        stops = np.array([n_unmatched])
    else: 
        stops = starts + blocksize
        stops[-1] = n_unmatched

    for start, stop in zip(starts, stops):
        this_idx = unmatched_idx[start:stop] 
        print('Calculating match for {} spikes'.
            format(all_spikes[this_idx].shape[0]))
        all_dists = distances_euclidean(all_spikes[this_idx], mean_array)
        print('all_dists: {}'.format(all_dists.shape))

        all_dists[all_dists > options['SecondMatchFactor'] * stds] = np.inf
        minimizers_idx = all_dists.argmin(1)
        minimizers = ids[minimizers_idx]

        minima = all_dists.min(1)
        minimizers[minima >= options['SecondMatchMaxDist'] * all_spikes.shape[1]] = 0

        fid.root.classes[this_idx] = minimizers
        fid.root.matches[this_idx] = SPIKE_MATCHED_2
        fid.root.distance[this_idx] = minima

    fid.flush()
    return fid.root.classes[:], fid.root.matches[:]


def plot_all_classes(classes, matches, all_spikes, plot_dirname):
    """
    plot classes
    """

    if not os.path.isdir(plot_dirname):
        os.mkdir(plot_dirname)

    clids = np.unique(classes)
    fig = mpl.figure(figsize=options['figsize'])
    fig.add_axes([0, 0, 1, 1])
    xax = np.arange(all_spikes.shape[1])
    xlim = (0, all_spikes.shape[1] - 1)

    _, means, _ = get_means(classes, all_spikes)

    if not len(means):
        ylim = options['ylim']
    else:
        max_of_means = (np.abs(means)).max()
        if max_of_means < options['ylim'][1]:
            ylim = (-1.5 * max_of_means, 1.5 * max_of_means)
        else:
            ylim = options['ylim']

    for clnum, clid in enumerate(clids):
        cl_idx = classes == clid
        outname = os.path.join(plot_dirname, 'class_{:03d}.png'.format(clid))
        print('Plotting {}/{}, {}, {} spikes'.
               format(clnum + 1, len(clids), plot_dirname, cl_idx.sum()))
        plot_class(fig, xax, xlim, ylim,
                   all_spikes[cl_idx], matches[cl_idx], outname)

    mpl.close(fig)


def plot_class(fig, xax, xlim, ylim, spikes, types, fname):
    """
    plot according to type
    """
    lnw = options['linewidth']
    axis = fig.get_axes()[0]
    axis.cla()
    axis.set_xlim(xlim)
    axis.set_ylim(ylim)
    axis.set_xticks(np.linspace(xlim[0], xlim[1], 5))
    axis.set_yticks(np.linspace(ylim[0], ylim[1], 5))
    axis.grid(True)
    i = 0
    skip = ylim[1]/8
    for sp_type, sp_color in plotdata:
        idx = types == sp_type
        if idx.any():
            axis.plot(xax, spikes[idx].T, sp_color, lw=lnw)
            axis.text(xax[-2], ylim[1] - skip*i - 10, str(idx.sum()),
                      color=sp_color, ha='right', va='top', size=9)
        i += 1

    meanspk = spikes.mean(0)
    axis.plot(xax, meanspk, 'k', lw=1.5*lnw)
    axis.text(xax[2], ylim[1] - 10, u'{:.0f} µV'.format(ylim[1]),
              color='k', ha='left', va='top', size=9)
    fig.savefig(fname)


def main(fname, sessions, label, do_plot=True):
    """
    usual main function
    """
    # make the necessary dictionary
    sign = 'neg' if 'neg' in sessions[0] else 'pos'

    for ses in sessions:
        if sign not in ses:
            raise ValueError('Different signs: {}'.format(sessions))

    basedir = os.path.dirname(fname)
    sorting_dir = os.path.join(basedir, label)

    logfname = os.path.join(basedir, 'log.txt')

    logfid = open(logfname, 'a')

    if not os.path.isdir(sorting_dir):
        os.mkdir(sorting_dir)
        logfid.write('created {}\n'.format(sorting_dir))

    outfname = os.path.join(sorting_dir, 'sort_cat.h5')

    if not options['OverwriteGroups']:
        if os.path.exists(outfname):
            print(outfname + ' exists already, skipping!')
            return None

    sort_man = collect_sorting(fname, sign, sessions, outfname)
    fid = tables.open_file(outfname, 'r+')
    fid.set_node_attr('/', 'sign', sign)
    spk_idx = fid.root.index[:]
    all_spikes = sort_man.get_data_by_name_and_index('spikes', spk_idx, sign)
    del sort_man

    classes, matches = total_match(fid, all_spikes)

    # after matching, artifacts might be different!
    if options['RecheckArtifacts']:
        clids = np.unique(classes)
        rows_clids = len(clids)

        if 0 in clids:
            artifacts = np.zeros((rows_clids, 2), 'int64')
            artifacts[:, 0] = clids
        else:
            artifacts = np.zeros((rows_clids + 1, 2), 'int64')
            artifacts[1:, 0] = clids

        invert = True if sign == 'neg' else False

        _, art_ids = find_artifacts(all_spikes, classes, clids, invert)

        for aid in art_ids:
            artifacts[artifacts[:, 0] == aid, 1] = 1

        fid.root.artifacts[:] = artifacts
        fid.flush()

        # print('New artifacts: {}'.format(fid.root.artifacts))

    if do_plot:
        plot_all_classes(classes, matches, all_spikes, sorting_dir)
        logfid.write('Plotted classes in {}\n'.format(sorting_dir))

    print(fid.filename, fid.root.artifacts[:])

    fid.close()
    logfid.close()

    return outfname


def multi_helper(args):
    """
    standard multiprocessing helper
    """
    fname, sessions, label, do_groups, do_plot = args

    outfname = main(fname, sessions, label, do_plot)
    if do_groups:
        if outfname is not None:
            create_groups_main(fname, outfname)


def parse_args():
    """
    usual parser
    """
    from argparse import ArgumentParser, FileType, ArgumentError

    parser = ArgumentParser('css-combine',
                            description='Concatenates sorted sessions',
                            epilog='Johannes Niediek (jonied@posteo.de)')
    parser.add_argument('--jobs', type=FileType('r'))
    parser.add_argument('--datafile', nargs=1)
    parser.add_argument('--sessions', nargs='+')
    parser.add_argument('--label', nargs=1)
    parser.add_argument('--no-grouping', default=False, action='store_true')
    parser.add_argument('--single', default=False, action='store_true')
    parser.add_argument('--no-plots', default=False, action='store_true')

    args = parser.parse_args()
    do_groups = not args.no_grouping
    single = args.single
    do_plots = not args.no_plots

    if args.jobs is None:
        if None in (args.datafile, args.sessions, args.label):
            raise ArgumentError(args.jobs,
                                'Specify either jobs or datafile, '
                                'sessions, and label')
        else:
            outfname = main(args.datafile[0], args.sessions, args.label[0],
                            do_plots)
            if do_groups:
                if outfname is not None:
                    create_groups_main(args.datafile[0], outfname)

    else:
        if args.label is None:
            label = args.jobs.name[:-4]
        else:
            label = args.label[0]
        jobs = tuple((tuple(x.split()) for x in args.jobs.readlines()))
        args.jobs.close()
        test_joblist(jobs)
        jobdict = dict()

        for job in jobs:

            session = os.path.basename(job[2])
            if job[0] in jobdict:
                jobdict[job[0]].append(session)
            else:
                jobdict[job[0]] = [session]

        if single:
            for fname, sessions in jobdict.items():
                multi_helper((fname, sessions, label, do_groups, do_plots))
        else:
            pool = Pool(cpu_count())
            print('Starting {} workers to concatenate'.format(cpu_count()))
            pool.map(multi_helper, [(fname, sessions, label,
                                     do_groups, do_plots)
                                    for fname, sessions in jobdict.items()])
