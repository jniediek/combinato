#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import importlib.util
from argparse import ArgumentParser, FileType

# Usage:
#   python run_combinato_workflow.py --jobs jobs.txt --destination /path/to/output/folder
#
# Multiple job files, same destination:
#   python run_combinato_workflow.py --jobs job1.txt job2.txt job3.txt --destination /out
#
# Multiple job files, different destinations:
#   python run_combinato_workflow.py --jobs job1.txt job2.txt job3.txt --destination /out1 /out2 /out3
#
# Process only one polarity (default: both pos and neg):
#   python run_combinato_workflow.py --jobs jobs.txt --destination /out --sign neg
#   python run_combinato_workflow.py --jobs jobs.txt --destination /out --sign pos
#
# Override combinato parameters (see load_local_options / apply_mask_artifact_options
# below for what the file may define):
#   python run_combinato_workflow.py --jobs jobs.txt --destination /out \
#       --local-options /path/to/my_local_options.py
#
# example job1.txt:
#   /path/to/electrode.bin


def load_local_options(path):
    """Load *path* and register it as the `local_options` module that
    combinato looks for.

    combinato/__init__.py and combinato/extract/extract_spikes.py each do
    `from local_options import options as local_options` exactly once, the
    first time they're imported -- and they only find that module because
    combinato/__init__.py adds the current working directory to sys.path at
    that moment. That's fragile here: this script changes directories
    (os.chdir) partway through, and it's launched from whatever cwd the
    caller (combos_gui.py, a batch script, ...) happens to use. Registering
    the loaded module directly in sys.modules sidesteps all of that -- the
    file can live anywhere and be named anything, as long as this runs
    before combinato is first imported.
    """
    spec = importlib.util.spec_from_file_location('local_options', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules['local_options'] = module
    return module


def apply_mask_artifact_options(local_options_module):
    """Monkeypatch combinato.artifacts.mask_artifacts's per-artifact-type
    option dicts (e.g. options_by_bincount['max_frac_ch']).

    These aren't part of combinato's options/local_options mechanism --
    they're private module-level dicts in mask_artifacts.py with no CLI
    flag -- so overriding them without hand-editing combinato has to
    happen in-process, before mask_artifacts.parse_args() runs.
    """
    overrides = getattr(local_options_module, 'mask_artifact_options', None)
    if not overrides:
        return

    from combinato.artifacts import mask_artifacts
    by_name = {opts['name']: opts for opts in mask_artifacts.artifact_types}
    for name, values in overrides.items():
        if name not in by_name:
            raise ValueError(
                "Unknown mask artifact type {!r} in mask_artifact_options, "
                "expected one of: {}".format(name, ', '.join(sorted(by_name))))
        by_name[name].update(values)
        print("Updated mask_artifacts {!r} options: {}".format(name, values))


def main(job_file, out_folder, signs=('pos', 'neg')):
    # Deferred until after --local-options has been applied (see __main__
    # below) so combinato picks up any overrides at first import.
    from combinato.extract.extract import main as extract_main
    from combinato.artifacts.concurrent import main as concurrent_main
    from combinato.artifacts.mask_artifacts import parse_args as mask_main
    from combinato.cluster.prepare import main as prepare_main
    from combinato.cluster.cluster import main as cluster_main
    from combinato.cluster.concatenate import main as combine_main
    from combinato.cluster.create_groups import main as groups_main

    print('Using job file: {}'.format(job_file))

    if not os.path.exists(os.path.expanduser(out_folder)):
        os.makedirs(os.path.expanduser(out_folder))


    # extract spikes
    sys.argv = ['~',
        '--jobs', job_file,
        '--destination', out_folder]
    extract_main()

    # find concurrent spikes
    os.chdir(out_folder)
    concurrent_main()

    # mask artifacts using concurrent spikes
    os.chdir(out_folder)
    sys.argv = ['~'] # no arguments to pass here
    mask_main()

    # find all extracted h5 files
    from combinato import h5files
    h5files = h5files(out_folder)
    print('Found {} h5 files'.format(len(h5files)))


    # run through each extracted spike file, and do sorting
    for fname in h5files:

        print('Processing file: {}'.format(fname))

        sign = 'neg'
        label_ = 'basic'
        for sign_ in signs:
            sessions = prepare_main([fname], sign_, 'index', 0,
                                        None, 20000, label_, False, False)
            if (sessions) :
                for name, sign, ses in sessions:
                    cluster_main(name, ses, sign)
                label = 'sort_{}_{}'.format(sign, label_)
                outfname = combine_main(fname,
                                        [os.path.basename(ses[2]) for ses in sessions],
                                        label)
                groups_main(fname, outfname)


if __name__ == "__main__":

    parser = ArgumentParser('run_combinato_workflow.py',
                            description='runs combinato workflow using jobs')
    parser.add_argument('--jobs', type=FileType('r'), nargs='+')
    parser.add_argument('--destination', nargs='+')
    parser.add_argument('--sign', choices=['pos', 'neg'], nargs='+', default=['pos', 'neg'])
    parser.add_argument('--local-options',
                        help='path to a local_options.py-style file. May define '
                             'options / artifact_criteria (merged into combinato\'s '
                             'options, e.g. clustering/extraction parameters) and/or '
                             'mask_artifact_options (applied to '
                             'combinato.artifacts.mask_artifacts, e.g. to override '
                             'max_frac_ch for the bincount artifact type)')
    args = parser.parse_args()

    if args.destination is None:
        print('Supply destination folder using --destination')
        sys.exit(1)
    if args.jobs is None:
        print('Supply job file using --jobs')
        sys.exit(1)

    if args.local_options:
        if not os.path.isfile(args.local_options):
            print('local options file not found: {}'.format(args.local_options))
            sys.exit(1)
        local_options_module = load_local_options(args.local_options)
        apply_mask_artifact_options(local_options_module)

    job_files = [f.name for f in args.jobs]
    destinations = args.destination

    if len(destinations) == 1:
        destinations = destinations * len(job_files)
    elif len(destinations) != len(job_files):
        print('Number of destinations must be 1 or match the number of job files')
        sys.exit(1)

    for job_file, dest in zip(job_files, destinations):
        main(job_file, dest, args.sign)
