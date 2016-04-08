# JN 2016-04-08

"""
First read do_sort_neg.txt, CheetahLogFile_*.csv,
and channel_names.csv.

Then check if any channel in do_sort_neg.txt
are using the same reference.

Warning: This assumes that all channels have been renamed
to the CSCxy.ncs format
"""


from __future__ import print_function, division, absolute_import
import os
import glob
import csv


def main(fname_sort_neg, fname_logfile, fname_channels):
    """
    parse the files and check for problems
    """
    
    # read channel names
    with open(fname_channels, 'r') as fid:
        names = dict(csv.reader(fid, delimiter=';'))
    
    # transform to integer based names
    int_names = {int(fname[3:]): names[fname] for fname in names}

    # read references
    with open(fname_logfile, 'r') as fid:
        refs = list((csv.reader(fid, delimiter=',')))
    
    name_refs = {}
    for item in refs:
        if len(item) == 4:
            name_refs[item[1]] = item[2]

    # read proposed sorting

    with open(fname_sort_neg, 'r') as fid:
        job_channels = [int(os.path.basename(line.strip())[8:-3])
                        for line in fid.readlines()]

    used_refs = set()
    for chan in job_channels:
        print('{} (CSC{}) is referenced to {}'.
              format(int_names[chan], chan, name_refs[int_names[chan]]))
        used_refs.add(name_refs[int_names[chan]])

    print('The {} channels in {} use the following {} references: {}'.
          format(len(job_channels), fname_sort_neg,
                 len(used_refs), sorted(used_refs)))



if __name__ == "__main__":
    fname_logfile = glob.glob("CheetahLogFile_*.csv")[0]
    fname_channels = "do_sort_neg.txt"
    fname_channel_names = "channel_names.csv"
    
    print("Checking {} for double references.".format(fname_channels))
    print("Using {} and {}".format(fname_logfile, fname_channel_names))
    main(fname_channels, fname_logfile, fname_channel_names)
