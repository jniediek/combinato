#!/usr/bin/env python
# JN 2015-07-29

"""
Log file parser for Cheetah
At the moment, this script reads out the reference settings
by sequentially following all crs, rbs, and gbd commands
"""

from __future__ import print_function, absolute_import, division
import os
import re
from collections import defaultdict
from csv import writer as csv_writer


class Setting(object):
    """
    simple class that stores reference settings
    """
    def __init__(self):
        self.num2name = None
        self.name2num = None
        self.lrefs = None
        self.grefs = None
        self.crefs = None
        self.start_rec = None
        self.stop_rec = None
        self.folder = None

DEBUG = False
# The following are the interesting commands
# You can still trick the parser, e.g. by sending -SetChannelNumber commands
# via NetCom.
# But it's very easy to adapt the parser to such situations

set_drs_strings = ('Processing line: -SetDRS',  # old systems
                   'Processing line: -SetAcqEntReference')  # new systems

set_channel_string = 'Processing line: -SetChannelNumber'

channel_number_pattern = re.compile(r'.*\"(.*)\" (\d.*)')
channel_number_pattern_var = re.compile(r'.* (.*) (.*)')
drs_command_pattern = re.compile(r'DRS Command\(b(\w) (\w*)\s{1,2}'
                                 r'(\d*)\s{0,2}(\d*)')
variable_pattern = re.compile(r'.*(%\w*) = \"?(\w*)\"?')


def board_num_to_chan(board, num):
    return (board - 1) * 16 + num


def chan_to_board_num(chan):
    return 2 * int(chan/32) + 1, chan % 32


def parser(fname):
    """
    transform logfile into header, log, and ignored lines
    """
    with open(fname, 'r') as fid:
        lines = fid.readlines()

    fid.close()
    in_header = True
    is_notice = False
    ignored_lines = []
    protocol = []
    header = {}

    for line in lines:
        if line[:13] == '-* NOTICE  *-':
            is_notice = True
        else:
            is_notice = False

        if in_header:
            # this means header is over
            if is_notice:
                in_header = False
            else:
                if len(line) > 3:
                    key, value = line.split(':', 1)
                    header[key] = value.strip()

        else:
            if is_notice:
                fields = line[15:].split(' - ', 4)
                time = fields[0]
                stamp = int(fields[1])
                msg = fields[2].strip().replace('\r', '')

                if len(fields) == 4:
                    msg2 = fields[3].strip().replace('\r', '')
                else:
                    msg2 = ''

                protocol.append((time, stamp, msg, msg2))

            elif line.startswith('Log file successfully moved to'):
                target = line.split()[-1]
                # this indicates a log file move
                # mov is our key
                protocol.append((0, 0, 'mov', target))

            else:
                ignored_lines.append(line.strip())

    try:
        bn = 'Cheetah ' + header['Cheetah Build Number']
    except KeyError:
        bn = 'ATLAS ' + header['Cheetah ATLAS Build Number']
    print(bn)
    return header, protocol, ignored_lines


def all_defined_check(chnum2name, crefs):
    """
    check if a reference has been defined for all existing channels
    """
    for chnum in chnum2name:
        board, lnum = chan_to_board_num(chnum)
        try:
            ref = crefs[chnum]
            if DEBUG:
                print('Channel {} (board {} channel {}) - {}'.
                      format(chnum, board, lnum, ref))
        except KeyError:
            print('No reference defined for channel {} ({})'.
                  format(chnum, chnum2name[chnum][0]))


def print_refs(lrefs, grefs):
    """
    overview of local and global refrences
    """
    sorted_keys = sorted(lrefs.keys())
    for board, ref in sorted_keys:
        lref = lrefs[(board, ref)]
        if lref in grefs:
            gboard = grefs[lref]
            stri = 'global, board {}'.format(gboard)
        else:
            stri = 'local'
        print('board {} ref {} - {} ({})'.
              format(board, ref, lrefs[(board, ref)], stri))


def analyze_drs(protocol):
    """
    go through a protocol and analyze all drs settings
    """

    # for each board, store the 8 local refs
    # 32..35 are the 4 local reference wires
    # 36, 37 are subject ground, patient ground
    # 38 seems to be specific to ATLAS
    # this is a (board, ref) -> local_num dict
    local_refs = dict()

    # 8 ref numbers can be driven globally
    # this is a ref_num -> board dict
    global_refs = dict()

    # each channel has a reference which
    # refers to its board's local referenes
    # this is a ch_num -> ref_num dict
    channel_refs = dict()

    # name2num is unique
    ch_name2num = dict()

    # num2name is *not* unique, values are lists
    ch_num2name = defaultdict(list)

    # save the settings
    all_settings = []
    variables = dict()
    temp_setting = None

    for line in protocol:
        time, _, msg1, msg2 = line

        if temp_setting is None:
            temp_setting = Setting()

        if msg1 == 'mov':
            temp_setting.folder = msg2

        elif '::SendDRSCommand()' in msg1:
            # log all reference settings (command file and GUI interaction)
            board, cmd, arg1, arg2 = drs_command_pattern.match(msg2).groups()
            arg1 = int(arg1)
            board = int(board, 16)

            if cmd != 'hsp':
                arg2 = int(arg2)
            else:
                arg2 = ''

            if cmd == 'gbd':
                # this is the global drive
                # if a reference is driven globally, it overrides
                # the local settings of that reference
                if arg2 == 1:
                    global_refs[arg1] = board
                    print('{} is now driven by board {}'.format(arg1, board))

                elif arg2 == 0:
                    if arg1 in global_refs:
                        del global_refs[arg1]

            if cmd == 'rbs':
                # each board stores 8 references
                # arg1 is the stored number
                # arg2 is the channel it points to
                if (board, arg1) in local_refs:
                    if DEBUG:
                        print('board {} ref {} was {}, is now {}'.
                              format(board, arg1,
                                     local_refs[(board, arg1)], arg2))
                local_refs[(board, arg1)] = arg2

            elif cmd == 'crs':
                # each channel is indexed by board and local number
                # arg1 is the local channel number
                # arg2 is the local reference it points to
                # try:
                #    local_ref = local_refs[(board, arg2)]
                # except KeyError:
                #    print(msg2)
                #    raise Warning('Using undefined reference!')

                chnum = board_num_to_chan(board, arg1)
                channel_refs[chnum] = arg2
                # print(cmd, board, arg1, chnum, local_ref)

        elif 'StartRecording' in msg1:
            temp_setting.num2name = ch_num2name.copy()
            temp_setting.name2num = ch_name2num.copy()
            temp_setting.lrefs = local_refs.copy()
            temp_setting.grefs = global_refs.copy()
            temp_setting.crefs = channel_refs.copy()
            temp_setting.start_rec = (msg1, time)
            # print(msg1, time)

        elif 'StopRecording' in msg1:
            # here, the setting is definite and has to be saved
            temp_setting.stop_rec = (msg1, time)
            all_settings.append(temp_setting)
            temp_setting = None
            # print(msg1, time)
        elif ' = ' in msg2:
            # assigning a variable
            var, val = variable_pattern.match(msg2).groups()
            variables[var] = val
        if msg2.startswith(set_channel_string):
            # log channel numbers
            if '%' in msg2:
                var, ch_num = channel_number_pattern_var.match(msg2).groups()
                try:
                    ch_name = variables[var]
                except KeyError:
                    print('{}, but something is wrong with setting channel'
                          'numbers. Check for errors'
                          ' in the Cheetah logfile itself.'.format(msg2))
                    continue
                if '%' in ch_num:
                    ch_num = variables[ch_num]
            else:
                ch_name, ch_num = channel_number_pattern.match(msg2).groups()

            ch_num = int(ch_num)

            if ch_name in ch_name2num:
                raise Warning('channel number reset')

            ch_name2num[ch_name] = ch_num
            ch_num2name[ch_num].append(ch_name)

        elif msg2.startswith(set_drs_strings):
            # if needed, insert code to
            # log reference settings from command file
            pass

    return all_settings


def create_rep(num2name, name2num, crefs, lrefs, grefs):
    """
    create a human readable representation of the referencing
    """
    all_defined_check(num2name, crefs)
    if DEBUG:
        print_refs(lrefs, grefs)
    chnames = []
    for num in sorted(num2name.keys()):
        chnames += num2name[num]

    out_str = []
    for name in chnames:
        try:
            chan = name2num[name]
        except KeyError:
            print('Processing {}, but no channel number was '
                  'assigned. Check results carefully!'.format(name))
            continue
        ch_board, ch_board_num = chan_to_board_num(chan)

        local_ref_num = crefs[chan]  # gives the local ref number
        # this is now a local number, so it's in 0..7
        maybe_global = False

        if local_ref_num in grefs:
            ref_board = grefs[local_ref_num]
            if ref_board != ch_board:
                maybe_global = True
            # here, I have to check whether the
            # driving channel is the same number on my local board
            # i.e., if b1_15 is b1_ref_2 and b1_ref_2 is gd
            # and b3_7 has ref_2, then it's global only if b3_15 is b3_ref_2

        else:
            ref_board = ch_board

        ref_num = lrefs[(ref_board, local_ref_num)]
        ref_num2 = lrefs[(ch_board, local_ref_num)]
        add_str = ''
        if maybe_global:
            # print('Special case, global ref {}, local ref {}'
            #     .format(ref_num, lrefs[(ch_board, local_ref_num)]))
            if ref_num2 != 38:
                add_str = ' ?'
                if ref_num != ref_num2:
                    # print(ref_num, lrefs[(ch_board, local_ref_num)])
                    ref_board = ch_board
                    ref_num = ref_num2
                else:
                    add_str = ' ???'
                    ref_board = ch_board
                    ref_num = ref_num2
                    pass
                # print('Using channel 38')

        if ref_board == ch_board:
            board_str = 'local{}'.format(add_str)
        else:
            board_str = 'global{}'.format(add_str)

        if ref_num > 31:
            # these are the reference wires
            if ref_num == 38:
                ref_name = 'board {} Unknown Ground'.format(ref_board)
            elif ref_num == 36:
                ref_name = 'board {} Patient Ground'.format(ref_board)
            else:
                tnum = (ref_num - 32) * 8
                refchan = board_num_to_chan(ref_board, tnum)
                if refchan in num2name:
                    pref_name = num2name[refchan]
                    idx = 0
                    if len(pref_name) == 2:
                        if pref_name[0][0] == 'u':
                            idx = 1
                    ref_name = pref_name[idx][:-1] + ' reference wire'

                else:
                    ref_name = 'board {} head stage {} reference wire'.\
                               format(ref_board, ref_num - 32)
        else:
            global_num = board_num_to_chan(ref_board, ref_num)
            ref_name = num2name[global_num][0]

        if name == ref_name:
            board_str += ' ZERO'
        out_str.append(('{:03d}'.format(chan), name, ref_name, board_str))
    return out_str


def check_logfile(fname, write_csv=False, nback=0):
    """
    run over a Cheetah logfile and analyzed reference settings etc
    """
    _, protocol, _ = parser(fname)
    base_name = os.path.splitext(os.path.basename(fname))[0]
    all_settings = analyze_drs(protocol)

    for i_setting, setting in enumerate(all_settings):
        print()
        if setting.folder is None:
            msg = 'Warning: Recording Stop -> Start without folder change!'
        else:
            msg = setting.folder

        print(msg)
        print('Start: {}'.format(setting.start_rec[1]))
        print('Stop: {}'.format(setting.stop_rec[1]))
        # print('Duration: {} min'.
        #      format((setting.stop_rec[1] - setting.start_rec[1])))
        out_str = create_rep(setting.num2name, setting.name2num,
                             setting.crefs, setting.lrefs, setting.grefs)
    if write_csv:
        setting = all_settings[-nback-1]

        if setting.folder is None:
            msg = 'Warning: Recording Stop -> Start without folder change!'
        else:
            msg = setting.folder

        out_str = create_rep(setting.num2name, setting.name2num,
                             setting.crefs, setting.lrefs, setting.grefs)
        outfname = base_name + '_{:02d}.csv'.\
            format(len(all_settings) - nback - 1)
        with open(outfname, 'w') as outf:
            outf.write('# {} {} {}\n'.format(msg,
                                             setting.start_rec[1],
                                             setting.stop_rec[1]))
            csvwriter = csv_writer(outf)
            for line in out_str:
                csvwriter.writerow(line)


if __name__ == '__main__':
    from argparse import ArgumentParser
    aparser = ArgumentParser(epilog='Johannes Niediek (jonied@posteo.de)')
    aparser.add_argument('--write-csv', action='store_true', default=False,
                         help='Write out to logfile_number.csv')
    aparser.add_argument('--logfile', nargs=1,
                         help='Logfile, default: CheetahLogFile.txt')
    aparser.add_argument('--nback', nargs=1, type=int,
                         help='Save last-n\'th setting', default=[0])
    args = aparser.parse_args()
    if not args.logfile:
        logfile = 'CheetahLogFile.txt'
    else:
        logfile = args.logfile[0]

    check_logfile(logfile, args.write_csv, args.nback[0])
