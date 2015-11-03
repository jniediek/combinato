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
        print('Module combinato not found: {}'.format(error))
        print('Check your PYTHONPATH')
        return False
    print('Found Combinato')

    def_opt_path = combinato.default_options.__file__
    try:
        import combinato.options
    except ImportError as error:
        print('Combinato options not found: {}'.format(error))
        print('Copy {} to options.py in the folder'.format(def_opt_path))
        return False
    print('Found options.py')

    try:
        subprocess.call(combinato.options['ClusterPath'],
                        stdout=subprocess.PIPE)
    except OSError as error:
        print('SPC binary not found or not executable: {}'.format(error))
        print('Place SPC binary in a folder and set path in options.py')
        return False
    print('Found SPC binary')

    return True


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
