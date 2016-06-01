# JN 2016-06-01

"""
given dropfiles, create a common one (lines contained in all files)
"""


def common_dropfile(fnames):
    
    sets = []
    for fname in fnames:
        with open(fname, 'r') as fid:
            sets.append(set([l.strip() for l in fid.readlines()]))

    return sorted(sets[0].intersection(*(sets[1:])))


if __name__ == "__main__":
    import sys
    ret = common_dropfile(sys.argv[1:])
    for l in ret:
        print(l)
