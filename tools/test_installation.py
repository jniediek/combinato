# JN 2015-11-03
"""
This module should contain calls to the test functions
already present in various submodules of combinato.

At the moment, it only checks whether the clustering binaries
are present and whether plotting is possible
"""
from __future__ import division, absolute_import, print_function
import subprocess
import sys
import os


def initial_test():
    """
    check correct setup of SPC binary
    """
    try:
        import combinato.default_options
    except ImportError as error:
        print('Unable to load Combinato: {}'.format(error))
        print('Check your PYTHONPATH and make sure to copy\n'
              'combinato/default_options.py to combinato/options.py')
        return False
    print('Found Combinato')

    # now check if SPC binary is callable
    try:
        subprocess.call(combinato.options['ClusterPath'],
                        stdout=subprocess.PIPE)
    except OSError as error:
        print('SPC binary not found or not executable: {}'.format(error))
        print('Place SPC binary in a folder and set path in options.py')
        return False
    print('Found SPC binary')

    # check for version of tables
    try:
        import tables
    except ImportError as error:
        print('Unable to import tables: {}'.format(error))
        print('Please install pytables')
        return False

    tabversion = tables.__version__
    print('Your version of pytables is ' + tabversion)
    if int(tabversion[0]) < 3:
        print('But you need at least 3.0.0')
        return False

    return True


def manager_test(fname, label, ts):
    """
    Test if we can load a sorted session and retrieve data.
    Requires certain files to be present
    """
    from combinato.manager.manager_cat import test
    test(fname, label, ts)


def plotting_test():
    """
    run a rudimentary test whether plotting will work
    """
    if 'linux' in sys.platform:
        if 'DISPLAY' not in os.environ:
            print('You are using linux without graphical environment. '
                  'Plotting will not work. Try ssh -X.')
        else:
            print('Found display')
    try:
        subprocess.call('montage', stdout=subprocess.PIPE)
    except OSError as error:
        print("'montage' from ImageMagick not found: {}\n"
              "Plotting continuous data will not work".format(error))
    else:
        print("Found 'montage', plotting continuous data possible.")

if __name__ == '__main__':

    if initial_test():
        print('Combinato clustering setup: no problems detected.')
    else:
        print('Re-run after fixing problems.')

    plotting_test()

    if len(sys.argv) > 3:
        manager_test(sys.argv[1], sys.argv[2], sys.argv[3])
