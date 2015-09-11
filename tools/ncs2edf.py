#!/usr/bin/python
# -*- encoding: utf-8
# JN 2014-08-30
# convert ncs files to edf files
# this converter does as of now (2014-08-31) 
# not follow all EDF+ rules, but is compatible with
# EDF. In particular, no time channel is kept here
# further work is required

from __future__ import print_function, division
import sys
import os
import glob
import socket
import time
import numpy as np
from combinato import NcsFile, ncs_info

NCS_SAMPLES_PER_REC = 512
ncs_recs_per_read = 2000

hostname = socket.gethostname()
date = time.strftime('%Y-%m-%d %T %Z')
infostring = 'converted: ' + hostname + ' ' + date
include_pattern = ('F', 'C', 'O',
                   'EOG', 'EMG', 'Cb', 'EKG')

header1type = np.dtype([ ('version', '|S8'),
           ('pname', '|S80'),
           ('recinfo', '|S80'),
           ('startdate', '|S8'),
           ('starttime', '|S8'),
           ('nbytes', '|S8'),
           ('reserved', '|S44'),
           ('nrec', '|S8'),
           ('recsec', '|S8'),
           ('nsig', 'S4')])


def make_header2type(ns):
    header2type = np.dtype([ ('labels', '16|S', ns),
                         ('transtype', '80|S', ns),
                         ('dim', '8|S', ns),
                         ('pmin', '8|S', ns),
                         ('pmax', '8|S', ns),
                         ('dmin', '8|S', ns),
                         ('dmax', '8|S', ns),
                         ('filt', '80|S', ns),
                         ('nsamp', '8|S', ns),
                         ('reserved', '32|S', ns) ])

    return header2type


def read_edf_header(filename):
    with open(filename, 'r') as f:
        data = f.read(256)  # header 1 is 256 bytes by spec
        h1data = np.array(data ,dtype=header1type) 
        ns = h1data['nsig'].astype(int)
        h2size = 256 * ns # header 2 is 246 * ns bytes by spec
        header2type = make_header2type(ns)
        data = f.read(h2size)
        h2data = np.array(data, dtype=header2type)

    return(h1data, h2data)

def get_channel_list(folder):
    chs = []
    for pat in include_pattern:
        chs += sorted(glob.glob(pat + '?.ncs'))

    return chs


def ncs_check_timestamps(ncsfname):
    """
    checks if records are equispaced
    """
    f = NcsFile(ncsfname)
    ts = f.read(0, f.num_recs, mode='timestamp')
    ts = ts.astype(int)
    err = np.diff(ts, 2).sum()
    return err


def create_edf_header(ncsfiles, patid='', comment=''):
    """
    Creates the header
    generates information based on the incoming ncsfiles
    """
    ns = len(ncsfiles)

    # perform basic consistency checks
    odate = ncsfiles[0].header['opened']
    cdate = ncsfiles[0].header['closed']
    nrecs = ncsfiles[0].num_recs
    fs = ncsfiles[0].header['SamplingFrequency']

    for nf in ncsfiles[2:]:
	if nf.header['SamplingFrequency'] != fs:
             raise(NotImplementedError('Conversion implemented for\
 equisampled channels only'.format(fs)))
        odiff = odate - nf.header['opened']
        cdiff = cdate - nf.header['closed']
        for d in (odiff, cdiff):
            if np.abs(d.total_seconds()) > 1:
                raise(Warning('Channels not openend/closed\
 at the same time: {} {}'.format(
                    ncsfiles[0], nf)))
        if nf.num_recs != nrecs:
            raise(Warning('Channels have different number of records')) 
        
    # fill header1
    timeinfo = ncsfiles[0].header['opened']
    header1 = np.empty(1, dtype=header1type)
    header1['version'] = format(0, '<8')
    header1['pname'] = format('X X X X' + ' ' + patid + ' ' + comment, '<80')
    header1['recinfo'] = format(infostring, '<80')
    header1['startdate'] = timeinfo.strftime('%d.%m.%y')
    header1['starttime'] = timeinfo.strftime('%H.%M.%S')
    header1['nbytes'] = format((ns + 1) * 256, '<8')
    header1['reserved'] = ' ' * 44
    header1['nrec'] = format(int(nrecs*512/fs), '<8') 
    header1['recsec'] = format(1, '<8')
    header1['nsig'] = format(ns, '<8')

    # fill header2
    header2type = make_header2type(ns)
    header2 = np.empty(1, dtype=header2type)

    for i in range(ns):
	info = ncsfiles[i].header
	admax = info['ADMaxValue']
	adbitmv = info['ADBitVolts'] * 1000
	admin = -1 - admax # assuming certain representation of integers
	filtstring = 'lowcut: {} Hz, highcut {} Hz'.format(
info['DspLowCutFrequency'], info['DspHighCutFrequency'])
	header2[0]['labels'][i] = format(info['AcqEntName'], '<16')
	header2[0]['transtype'][i] = format('Standard Electrode', '<80')
	header2[0]['dim'][i] = format('mV', '<8')
 	header2[0]['pmin'][i] = format(adbitmv * admin, '<8f')
	header2[0]['pmax'][i] = format(adbitmv * admax, '<8f')
	header2[0]['dmin'][i] = format(admin, '<8')
	header2[0]['dmax'][i] = format(admax, '<8')
	header2[0]['filt'][i] = format(filtstring, '<80')
 	header2[0]['nsamp'][i] = format(fs, '<8')
	header2[0]['reserved'][i] = ' ' * 32
    return header1, header2
    

def write_data(ncsfiles, edffile):
	
    ns = len(ncsfiles)
    num_recs = ncsfiles[0].num_recs	
    fs = ncsfiles[0].header['SamplingFrequency']
    ncs_recs_per_edf_rec = fs/NCS_SAMPLES_PER_REC
    end_rec = int(num_recs - num_recs % ncs_recs_per_edf_rec)
    starts = range(0, end_rec, ncs_recs_per_read)
    stops = starts[1:] + [end_rec]
    for start, stop in zip(starts, stops):
	print('Reading from {} to {}'.format(start, stop))
	block = np.zeros((ns * (stop-start)*512/fs, fs), 'int16')
	print('Blocksize {}'.format(block.shape))
	for i, nf in enumerate(ncsfiles):
	    data = nf.read(start, stop, mode='data')
            data = data.reshape(-1, fs)
            block[i::ns, :] = data
  
        edffile.write(block)


if __name__ == "__main__":
    """ missing:
    outfilename
    """
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('--out')
    parser.add_argument('--patid')
    parser.add_argument('--comment', default='')
    args = parser.parse_args()

    chs = get_channel_list(os.getcwd())

    ncsfiles = []
    for ch in chs:
	ncsfiles.append(NcsFile(ch))

    h1, h2 = create_edf_header(ncsfiles, args.patid, args.comment)
    f = open(args.out, 'w')
    f.write(h1)
    f.write(h2)
    write_data(ncsfiles, f)
    f.close()  
