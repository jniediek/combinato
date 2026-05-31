# JN 2016-05-12

"""
Setup options.py with the correct clustering binaries
"""
from __future__ import print_function
import os
import sys
import subprocess

OPT_PATH = os.path.join('combinato', 'options.py')
DEF_OPT_PATH = os.path.join('combinato', 'default_options.py')

def setup():

    if os.path.isfile(OPT_PATH):
        print(OPT_PATH + ' exists, not doing anything.')
        return

    platform = sys.platform

    if "linux" in platform:
        binary = 'cluster_linux64.exe'
    elif "win32" in platform:
        binary = 'cluster_64.exe'
    elif "darwin" in platform:
        # binary = 'cluster_maci.exe'
        binary = 'cluster_mac_new.exe'

    binary = os.path.join(os.getcwd(),'spc', binary)
    try:
        subprocess.call(binary, stdout=subprocess.PIPE)
    except OSError as error:
        print('Could not execute SPC binary {}'.format(binary))
        print(error)
        return

    print('Found and executed SPC binary {}'.format(binary))
            
    # try to execute the binary

    out_fname = OPT_PATH
    in_fname = DEF_OPT_PATH

    with open(in_fname, 'r') as in_fid:
        lines = in_fid.readlines()
    
    with open(out_fname, 'w') as out_fid:
        for line in lines:
            if line.startswith('CLUS_BINARY'):
                line = 'CLUS_BINARY = \'{}\''.format(binary)
            out_fid.write(line)


if __name__ == "__main__":
    setup()
