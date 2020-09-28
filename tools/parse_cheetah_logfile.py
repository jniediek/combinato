#!/usr/bin/env python3
# JN 2015-07-29

"""
Log file parser for Cheetah by Johannes Niediek

This script reads out the reference settings
by sequentially following all crs, rbs, and gbd commands.

Please keep in mind that the following scenario is possible with Cheetah:
Start the recording
Stop the recording
Change the reference settings
Start the recording

If you do this there will be .ncs with their reference changing
at some point during the recording.

In most cases, this is probably not what you want,
so this script displays a warning message if you did it.

Cheetah ATLAS:
There is an undocumented channel nummber 32000038.
I reverse-engineered its use, but that might depend on the exact version
of ATLAS etc.

This script partially mirrors the system of variable definitions
in Cheeatah. For complex arithmethic with variables, the script might fail.

Please check the GitHub repository (github.com/jniediek/combinato.git)
for updates and manual.

Contact me (jonied@posteo.de) for access to the repository.
"""

from __future__ import print_function, division
import os
import re
from collections import defaultdict
import datetime
from csv import writer as csv_writer

DATE_FNAME = 'start_stop_datetime.txt'


def parse_times(setting):
    """
    read out the date and times of a recording
    """
    def timestr2timeobj(time_str):
        """
        convert a time string with milliseconds to a datetime object
        """
        time, milli = time_str.split('.')
        time = datetime.datetime.strptime(time, '%H:%M:%S')
        time += datetime.timedelta(seconds=int(milli)/1000)
        return time

    tstart, tstop = [timestr2timeobj(rec[1])
                     for rec in setting.start_rec, setting.stop_rec]
    if setting.folder is None:
        folder_date_obj = None
    else:
        date_str = date_pattern.match(setting.folder).groups()[0]
        folder_date_obj = datetime.datetime.strptime(date_str,
                                                     r'%Y-%m-%d_%H-%M-%S')
        tstart = datetime.datetime.combine(folder_date_obj, tstart.time())
        tstop = datetime.datetime.combine(folder_date_obj, tstop.time())

    # by default assume that recording is stopped once every day
    if tstop < tstart:
        tstop += datetime.timedelta(days=1)

    return folder_date_obj, tstart, tstop


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
        self.start_timestamp = None
        self.stop_timestamp = None
        self.folder = None

DEBUG = False
# The following are the interesting commands
# You can still trick the parser, e.g. by sending -SetChannelNumber commands
# via NetCom.
# But it's very easy to adapt the parser to such situations

set_drs_strings = ('Processing line: -SetDRS',  # old systems
                   'Processing line: -SetAcqEntReference')  # new systems

set_channel_pattern = re.compile(r'Processing line:\s*-SetChannelNumber')

channel_number_pattern = re.compile(r'.*\"(.*)\" (\d.*)')
channel_number_pattern_var = re.compile(r'.* (.*) (.*)')
drs_command_pattern = re.compile(r'DRS Command\(b(\w) (\w*)\s{1,2}'
                                 r'(\d*)\s{0,2}(\d*)')
variable_pattern = re.compile(r'.*(%\w*) = \"?(\w*)\"?')
date_pattern = re.compile(r'.*(\d{4}-\d{1,2}-\d{1,2}_'
                          '\d{1,2}-\d{1,2}-\d{1,2}).*')


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
    # print(chnum2name)
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
        time, timestamp, msg1, msg2 = line

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
            temp_setting.start_timestamp = timestamp

        elif 'StopRecording' in msg1:
            # here, the setting is definite and has to be saved
            temp_setting.stop_rec = (msg1, time)
            temp_setting.stop_timestamp = timestamp
            all_settings.append(temp_setting)
            temp_setting = None

        elif ' = ' in msg2:
            # assigning a variable
            var, val = variable_pattern.match(msg2).groups()
            variables[var] = val

        elif '%currentADChannel += 1' in msg2:
            # this is a hack, but it seems to work well
            print('Applying hack for += 1 syntax, check results!')
            var, val = msg2.split('+=')
            variables['%currentADChannel'] = str(int(variables['%currentADChannel']) + 1)

        if set_channel_pattern.match(msg2):
            # log channel numbers
            if '%' in msg2:
                var, ch_num = channel_number_pattern_var.match(msg2).groups()
                var = var.strip()
                ch_num = ch_num.strip()
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
                result = channel_number_pattern.match(msg2)
                if result is not None:
                    ch_name, ch_num = result.groups()
                else:
                    print('Parser skipped the following line: ' + msg2)
                    continue

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
            chlist = num2name[global_num]
            if len(chlist):
                ref_name = chlist[0]
            else:
                ref_name = 'UNDEF'

        if name == ref_name:
            board_str += ' ZERO'
        out_str.append(('{:03d}'.format(chan), name, ref_name, board_str))
    return out_str


def check_logfile(fname, write_csv=False, nback=0, write_datetime=False):
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

        print('Start: {} ({})'.format(setting.start_rec[1],
                                      setting.start_timestamp))
        print('Stop: {} ({})'.format(setting.stop_rec[1],
                                     setting.stop_timestamp))
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

    if write_datetime:
        setting = all_settings[-nback-1]
        date, start, stop = parse_times(setting)
        print(date, start, stop)
        if date is None:
            out = '# Date not guessed because Recording was stopped'\
                  ' and re-started without folder change!\n'

        else:
            out = '# {}\ncreate_folder {}\n'.\
                   format(setting.folder, date.strftime('%Y-%m-%d %H:%M:%S'))

        start_ts = setting.start_timestamp
        stop_ts = setting.stop_timestamp

        for name, d, t in (('start', start, start_ts),
                           ('stop', stop, stop_ts)):
            out += name + '_recording {} {} {}\n'.\
                   format(d.date().isoformat(), d.time().isoformat(), t)

        diff_time = (stop_ts - start_ts)/1e6 - (stop - start).seconds

        out += 'cheetah_ahead: {}\n'.format(diff_time)

        if os.path.exists(DATE_FNAME):
            print('{} exists, not overwriting!'.format(DATE_FNAME))
        else:
            with open(DATE_FNAME, 'w') as fid:
                fid.write(out)


if __name__ == '__main__':
    from argparse import ArgumentParser
    aparser = ArgumentParser(epilog='Johannes Niediek (jonied@posteo.de)')
    aparser.add_argument('--write-csv', action='store_true', default=False,
                         help='Write out to logfile_number.csv')
    aparser.add_argument('--write-datetime', action='store_true',
                         default=False, help='Write start/stop timestamps to'
                         ' file {}'.format(DATE_FNAME))
    aparser.add_argument('--logfile', nargs=1,
                         help='Logfile, default: CheetahLogFile.txt')
    aparser.add_argument('--nback', nargs=1, type=int,
                         help='Save last-n\'th setting', default=[0])
    args = aparser.parse_args()
    if not args.logfile:
        logfile = 'CheetahLogFile.txt'
    else:
        logfile = args.logfile[0]

    check_logfile(logfile, args.write_csv, args.nback[0], args.write_datetime)
