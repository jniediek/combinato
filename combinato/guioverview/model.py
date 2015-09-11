# coding: utf-8
"""
class for channel table
"""
# JN 2014-12-16
from __future__ import division, print_function, absolute_import
from PyQt4 import QtCore as qc

NCOLS = 16
OBJECT, FNAME, POS_SP, NEG_SP, SORTED_SES, EXTR,\
    SORT_POS, SORT_NEG, SORTED_POS, SORTED_NEG, SIGNAL, POSITIVE, NEGATIVE,\
    SORTED_POS_IM, SORTED_NEG_IM, H5FNAME = range(NCOLS)

DO_SORT_STR_POS = 'sort pos'
DO_SORT_STR_NEG = 'sort neg'
DO_EXTRACT_STR = 'extract'
DONE_STR = 'done'
NONE_STR = 'none'
SORT_MANUAL_STR_POS = 'manual pos'
DROP_STR_POS = 'drop pos'
SORT_MANUAL_STR_NEG = 'manual neg'
DROP_STR_NEG = 'drop neg'


class ChannelTableModel(qc.QAbstractTableModel):
    """
    Table of channels with properties such as extracted, sorted etc
    """
    def __init__(self):
        super(ChannelTableModel, self).__init__()
        self.channels = []

    def rowCount(self, index=qc.QModelIndex()):
        return len(self.channels)

    def columnCount(self, index=qc.QModelIndex()):
        return NCOLS - 6

    def data(self, index, role=qc.Qt.DisplayRole):
        if not (index.isValid() and
                0 <= index.row() < len(self.channels)):
            return qc.QVariant()

        this_channel = self.channels[index.row()]
        col = index.column()

        if role == qc.Qt.DisplayRole:
            data = this_channel[col]
            if col in [POS_SP, NEG_SP, SORTED_SES]:
                if data > 1000:
                    data = str(int(round(data/1000))) + ' K'
                data = str(data)
            return qc.QVariant(data)

    def headerData(self, section, orientation, role=qc.Qt.DisplayRole):
        if role == qc.Qt.TextAlignmentRole:
            if orientation == qc.Qt.Horizontal:
                return qc.QVariant(int(qc.Qt.AlignLeft|qc.Qt.AlignVCenter))

        elif role == qc.Qt.DisplayRole:
            if orientation == qc.Qt.Horizontal:
                if section == OBJECT:
                    ret = 'Acquisition Entity'
                elif section == FNAME:
                    ret = 'File Name'
                elif section == POS_SP:
                    ret = 'Pos. spikes'
                elif section == NEG_SP:
                    ret = 'Neg. spikes'
                elif section == SORTED_SES:
                    ret = 'Sorted sessions'
                elif section == EXTR:
                    ret = 'Extraction action'
                elif section == SORT_POS:
                    ret = 'Sort positive action'
                elif section == SORT_NEG:
                    ret = 'Sort negative action'
                elif section == SORTED_POS:
                    ret = 'Sorted positive action'
                elif section == SORTED_NEG:
                    ret = 'Sorted negative action'

                return qc.QVariant(ret)
            return qc.QVariant(int(section) + 1)


    def add_row(self, row):
        """
        simply add a channel to table
        """
        self.channels.append(row)
        print('Added ' + row[0])
        self.reset()

    def get_image(self, row, which):
        """
        just return the image
        """
        ch_row = self.channels[row]
        image = ch_row[which]
        return image

    def get_status(self, row):
        """
        return a status row text
        """
        ch_row = self.channels[row]
        act = ''

        if ch_row[EXTR] != DONE_STR:
            act += ' ' + DO_EXTRACT_STR

        if ch_row[SORT_POS] != DONE_STR:
            act += ' ' + DO_SORT_STR_POS

        if ch_row[SORT_NEG] != DONE_STR:
            act += ' ' + DO_SORT_STR_NEG

        if act == '':
            act = NONE_STR

        ret = ch_row[OBJECT] + ' actions: ' + act
        return ret


    def toggle(self, index, what):
        """
        toggle sort/extract attributes
        """
        if what == DO_EXTRACT_STR:
            col = EXTR
        elif what == DO_SORT_STR_POS:
            col = SORT_POS
        elif what == DO_SORT_STR_NEG:
            col = SORT_NEG
        elif what[:6] == 'sorted':
            if what[-3:] == 'pos':
                col = SORTED_POS
            else:
                col = SORTED_NEG
            
        ch_row = self.channels[index.row()]
        now = ch_row[col]
        
        if col in (EXTR, SORT_POS, SORT_NEG):

            if now == DONE_STR:
                ch_row[col] = what
            else:
                ch_row[col] = DONE_STR

        elif col == SORTED_POS:
            if ch_row[col] == SORT_MANUAL_STR_POS:
                ch_row[col] = DROP_STR_POS
            elif ch_row[col] == DROP_STR_POS:
                ch_row[col] = DONE_STR
            elif ch_row[col] == DONE_STR:
                ch_row[col] = SORT_MANUAL_STR_POS

        elif col == SORTED_NEG:
            if ch_row[col] == SORT_MANUAL_STR_NEG:
                ch_row[col] = DROP_STR_NEG
            elif ch_row[col] == DROP_STR_NEG:
                ch_row[col] = DONE_STR
            elif ch_row[col] == DONE_STR:
                ch_row[col] = SORT_MANUAL_STR_NEG

        self.reset()

    def get_channels(self, what):
        """
        returns channels that have action sort or extract set
        """
        field = H5FNAME

        if what == DO_EXTRACT_STR:
            col = EXTR
            field = FNAME
        elif what == DO_SORT_STR_POS:
            col = SORT_POS
        elif what == DO_SORT_STR_NEG:
            col = SORT_NEG
        elif what in (SORT_MANUAL_STR_POS, DROP_STR_POS):
            col = SORTED_POS
        elif what in (SORT_MANUAL_STR_NEG, DROP_STR_NEG):
            col = SORTED_NEG

        ret = []

        if what in (DROP_STR_POS, DROP_STR_NEG):
            exclude = (DONE_STR, SORT_MANUAL_STR_POS, SORT_MANUAL_STR_NEG)
        elif what in (SORT_MANUAL_STR_POS, SORT_MANUAL_STR_NEG):
            exclude = (DONE_STR, DROP_STR_POS, DROP_STR_NEG)
        else:
            exclude = (DONE_STR, )

        for chan in self.channels:
            if chan[col] not in exclude:
                if chan[field] is not None:
                    ret.append(chan[field])

        return ret
