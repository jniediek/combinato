#!/usr/bin/env python3
import os
from glob import glob
from combinato import NcsFile


def to_original():
    ncsfiles = glob('*.ncs')
    for nf in ncsfiles:
        n = NcsFile(nf)
        oldname = n.header['AcqEntName'] + '.ncs'

        if os.path.exists(oldname):
            print('Not renaming {} to {}, file exists'.format(nf, oldname))
        else:
            print('renaming {} to {}'.format(nf, oldname))
            os.rename(nf, oldname)

def to_csc():
    ncsfiles = sorted(glob('L*.ncs') + glob('R*.ncs'))

    for i, nf in enumerate(ncsfiles):
        newname = 'CSC{}.ncs'.format(i + 1)
        print('Renaming {} to {}'.format(nf, newname))
        os.rename(nf, newname)
    
if __name__ == "__main__":
    to_csc()
