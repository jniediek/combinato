#!/usr/bin/env python
# coding: utf-8
"""
Displays overview of ncs files with their extract/sort status
"""
# JN 2014-12-15
from __future__ import print_function, division, absolute_import
import sys
import os

from PyQt4 import QtCore as qc
from PyQt4 import QtGui as qg

from .ui_guioverview import Ui_MainWindow
from .model import (ChannelTableModel, DO_SORT_STR_POS,
                    DO_SORT_STR_NEG, DO_EXTRACT_STR, DONE_STR,
                    SORT_MANUAL_STR_POS, SORT_MANUAL_STR_NEG,
                    DROP_STR_POS, DROP_STR_NEG, SIGNAL, POSITIVE,
                    NEGATIVE, SORTED_POS_IM, SORTED_NEG_IM)

from .. import get_channels, check_status, options
DEBUG = False

SCROLL_AREA_MIN_WIDTH = 50
TABLE_HEIGHT = 50
IMAGE_LABELS = ['None', 'Continuous', 'Pos. spikes', 'Neg. spikes',
                'Sorted pos. spikes', 'Sorted neg. spikes']
IMG_BY_LABEL = {'None': None,
                'Continuous': SIGNAL,
                'Pos. spikes': POSITIVE,
                'Neg. spikes': NEGATIVE,
                'Sorted pos. spikes': SORTED_POS_IM,
                'Sorted neg. spikes': SORTED_NEG_IM}


def load_image(path, entity, fname, img_type, sign=None, label=None):
    # JN 2014-12-26 add support for 'spikes' images
    """
    simple image loading helper
    """
    fname_base = os.path.splitext(fname)[0]
    pattern = img_type + '_' + entity + '_' + fname_base

    if sign is not None:
        pattern += '_' + sign

    if label is not None:
        pattern += '_' + label

    pattern += '.png'

    path_pattern = os.path.join(path, pattern)
    image = None

    if os.path.exists(path_pattern):
        image = qg.QPixmap(qg.QImage(path_pattern))
    else:
        print(path_pattern + ' does not exist')
        # fix for some old folders, not really relevant
        #  pattern = 'overview_' + entity + '.png'
        #  path_pattern = os.path.join(path, pattern)
        # if os.path.exists(path_pattern):
        # image = qg.QImage(path_pattern)

    if DEBUG:
        if image is not None:
            print('Loaded ' + path_pattern)

    return image


class GuiOverview(qg.QMainWindow, Ui_MainWindow):
    """
    main window of channel overview program
    """
    def __init__(self, parent=None):
        super(GuiOverview, self).__init__(parent)
        self.setupUi(self)
        self.initialized = False
        self.pixmap = None
        self.pixmapRight = None
        self.image_to_show_left = SIGNAL
        self.image_to_show_right = POSITIVE

        self.channelmodel = ChannelTableModel()
        self.tableViewChannels.setModel(self.channelmodel)

        self.labelCurrentCh = qg.QLabel(self)
        self.labelCurrentCh.setMinimumWidth(200)
        self.statusBar().addWidget(self.labelCurrentCh)

        self.labelDirName = qg.QLabel(self)
        self.statusBar().addWidget(self.labelDirName)

        self.labelImage = qg.QLabel(self)
        self.labelImageRight = qg.QLabel(self)

        for label in (self.labelImage, self.labelImageRight):
            label.setSizePolicy(qg.QSizePolicy.Ignored, qg.QSizePolicy.Ignored)
            label.setScaledContents(True)

        self.scrollAreaImage.setWidget(self.labelImage)
        self.scrollAreaImageRight.setWidget(self.labelImageRight)

        for scroll_area in (self.scrollAreaImage, self.scrollAreaImageRight):
            # scroll_area.resizeEvent = self.new_resize_event
            scroll_area.setMinimumWidth(SCROLL_AREA_MIN_WIDTH)

        for box in (self.comboBoxLeftImage, self.comboBoxRightImage):
            box.addItems(IMAGE_LABELS)

        self.set_actions()
        self.label = None

    def set_actions(self):
        self.tableViewChannels.selectionModel().\
            currentChanged.connect(self.item_action)
        self.action_Initialize_from_current_folder.\
            triggered.connect(self.init_from_cwd)
        # self.actionFitHeight.triggered.connect(self.react_fit_height)
        # self.actionFitWidth.triggered.connect(self.react_fit_width)
        # self.action_1_1.triggered.connect(self.react_1_1)
        self.actionToggleSort.triggered.connect(self.toggle_sort_pos)
        self.actionToggle_sort_negative.triggered.connect(self.toggle_sort_neg)
        self.actionToggleExtract.triggered.connect(self.toggle_extract)
        self.action_Next_channel.triggered.connect(self.goto_next)
        self.action_Previous_channel.triggered.connect(self.goto_previous)
        self.actionSave_actions_to_file.triggered.connect(self.print_all)
        self.actionOne_Down.triggered.connect(self.goto_next)
        self.actionToggle_sorted_positive.\
            triggered.connect(self.toggle_sorted_pos)
        self.actionToggle_sorted_negative.\
            triggered.connect(self.toggle_sorted_neg)

        # image selection
        self.comboBoxLeftImage.currentIndexChanged.connect(self.set_image_left)
        self.comboBoxRightImage.currentIndexChanged.\
            connect(self.set_image_right)

    def init_from_cwd(self):
        """
        helper
        """
        self.init_from_path(os.getcwd())

        # relayout
        top_visible = 50  # px
        vsizes = self.splitter_2.sizes()
        self.splitter_2.setSizes([top_visible,
                                  sum(vsizes) - top_visible])

        hsizes = self.splitter.sizes()
        left_space = int(sum(hsizes) * .6)
        self.splitter.setSizes([left_space, sum(hsizes) - left_space])

    def init_from_path(self, path):
        """
        read in channel information from a path
        """
        self.channelmodel.channels = []
        self.labelDirName.setText(path)
        label = str(self.lineEditLabel.text())
        if not len(label):
            label = None
        self.current_label = label

        from_h5files = self.checkBoxInitH5.isChecked()
        channels = get_channels(path, from_h5files)

        dirname_overview = os.path.join(path, 'overview')
        has_overview = os.path.isdir(dirname_overview)

        sorted_channels = sorted(channels)

        print(sorted_channels, label)

        if DEBUG:
            sorted_channels = sorted_channels[:3]

        for chname in sorted_channels:
            channel_fname = channels[chname]
            if self.checkBoxSetStates.isChecked():
                ch_ex, n_pos, n_neg, n_sorted, h5fname =\
                    check_status(channel_fname)
            else:
                ch_ex = True 
                n_pos = n_neg = n_sorted = 0
                h5fname = None

            if has_overview:
                ch_overview_image = load_image(dirname_overview,
                                               chname,
                                               channel_fname, 'overview')
                ch_spikes_image_pos = load_image(dirname_overview,
                                                 chname,
                                                 channel_fname,
                                                 'spikes', 'pos')
                ch_spikes_image_neg = load_image(dirname_overview,
                                                 chname,
                                                 channel_fname,
                                                 'spikes', 'neg')
                ch_sorted_image_pos = load_image(dirname_overview,
                                                 chname,
                                                 channel_fname,
                                                 'sorted',
                                                 'pos', label)
                ch_sorted_image_neg = load_image(dirname_overview,
                                                 chname,
                                                 channel_fname,
                                                 'sorted',
                                                 'neg', label)

            else:
                ch_overview_image = None
                ch_spikes_image_pos = None
                ch_spikes_image_neg = None
                ch_sorted_image_pos = None
                ch_sorted_image_neg = None

            if ch_ex:
                ex_str = DONE_STR
            else:
                ex_str = DO_EXTRACT_STR

            if self.checkBoxSetStates.isChecked():
                if n_sorted > 0:
                    sort_str = DONE_STR
                else:
                    sort_str = DO_SORT_STR_POS
            else:
                sort_str = DONE_STR

            sort_str_neg = DONE_STR  # by default, never sort negative

            sorted_str_pos = DONE_STR
            sorted_str_neg = DONE_STR

            row = [chname,
                   channels[chname],
                   n_pos,
                   n_neg,
                   n_sorted,
                   ex_str,
                   sort_str,
                   sort_str_neg,
                   sorted_str_pos,
                   sorted_str_neg,
                   ch_overview_image,
                   ch_spikes_image_pos,
                   ch_spikes_image_neg,
                   ch_sorted_image_pos,
                   ch_sorted_image_neg,
                   h5fname]
            self.channelmodel.add_row(row)
        self.initialized = True

#    def new_resize_event(self, ev):
#        """
#        just a helper
#        """
#        if None not in  (self.image_to_show_left, self.image_to_show_right):
#            self.set_sizes()

    def item_action(self, index=qc.QModelIndex(), prev=qc.QModelIndex()):
        """
        typical action is to show image
        """
        if not self.initialized:
            return

        if self.image_to_show_left is not None:

            self.pixmap = self.channelmodel.\
                get_image(index.row(), self.image_to_show_left)
            if self.pixmap is not None:
                self.labelImage.setPixmap(self.pixmap)

        if self.image_to_show_right is not None:
            self.pixmapRight = self.channelmodel.\
                get_image(index.row(), self.image_to_show_right)
            if self.pixmapRight is not None:
                self.labelImageRight.setPixmap(self.pixmapRight)

        self.set_sizes()

        # set the status
        status = self.channelmodel.get_status(index.row())
        self.labelCurrentCh.setText(status)

#    def react_fit_height(self):
#        """
#        helper
#        """
#        self.set_sizes('h')
#
#    def react_fit_width(self):
#        """
#        helper
#        """
#        self.set_sizes('w')
#
#    def react_1_1(self):
#        """
#        helper
#        """
#        self.set_sizes('1')
#
    def set_sizes(self, clicked='w'):
        """
        set image size
        """
        # fit_h = self.actionFitHeight.isChecked()
        # fit_w = self.actionFitWidth.isChecked()
        # oneone = self.action_1_1.isChecked()

#        if clicked in 'hw':
#            if fit_h or fit_w:
#                self.action_1_1.setChecked(False)
#                oneone = False
#
#            else:
#                self.action_1_1.setChecked(True)
#                oneone = True
#
#        else:
#            if oneone:
#                self.actionFitHeight.setChecked(False)
#                self.actionFitWidth.setChecked(False)
#                fit_h = fit_w = False
#
        seq = ((self.labelImage, self.pixmap, self.scrollAreaImage),
               (self.labelImageRight, self.pixmapRight,
                self.scrollAreaImageRight))

        for label, image, area in seq:
            if image is not None:
                height = image.height()
                width = image.width()

                label.resize(qc.QSize(width, height))

    def toggle_sorted_pos(self):
        self.toggle('sorted pos')

    def toggle_sorted_neg(self):
        self.toggle('sorted neg')

    def toggle_sort_pos(self):
        self.toggle('sort pos')

    def toggle_sort_neg(self):
        self.toggle('sort neg')

    def toggle_extract(self):
        self.toggle('extract')

    def toggle(self, what):
        """
        toggle action for this channel
        """
        index = self.tableViewChannels.selectedIndexes()
        if index:
            self.channelmodel.toggle(index[0], what)
            self.tableViewChannels.selectionModel().\
                setCurrentIndex(index[0],
                                qg.QItemSelectionModel.Select |
                                qg.QItemSelectionModel.Current)

    def goto_next(self):
        self.goto(1)

    def goto_previous(self):
        self.goto(-1)

    def goto(self, shift):
        """
        go down one channel in table view
        """
        index = self.tableViewChannels.selectedIndexes()
        if index:
            row = index[0].row()
            col = index[0].column()
            if shift > 0:
                if row == len(self.channelmodel.channels) - shift:
                    return
            elif shift < 0:
                if row < -shift:
                    return

            new_index = self.channelmodel.createIndex(row + shift, col)
            self.tableViewChannels.selectionModel().\
                setCurrentIndex(new_index,
                                qg.QItemSelectionModel.Select |
                                qg.QItemSelectionModel.Current)

    def print_all(self):
        """
        print both extract and sort channels
        """
        self.print_action_channels(DO_EXTRACT_STR)
        self.print_action_channels(DO_SORT_STR_POS)
        self.print_action_channels(DO_SORT_STR_NEG)
        self.print_action_channels(SORT_MANUAL_STR_POS)
        self.print_action_channels(SORT_MANUAL_STR_NEG)
        self.print_action_channels(DROP_STR_POS)
        self.print_action_channels(DROP_STR_NEG)

    def print_action_channels(self, what):
        """
        print out sort/extract channels
        """
        infixes = {DO_EXTRACT_STR:      'extract',
                   DO_SORT_STR_POS:     'sort_pos',
                   DO_SORT_STR_NEG:     'sort_neg',
                   SORT_MANUAL_STR_POS: 'manual_pos',
                   SORT_MANUAL_STR_NEG: 'manual_neg',
                   DROP_STR_POS:        'drop_pos',
                   DROP_STR_NEG:        'drop_neg'}

        infix = infixes[what]

        if self.label is not None:
            infix += '_' + self.label

        chans = self.channelmodel.get_channels(what)

        if not chans:
            return

        out_fname = 'do_' + infix + '.txt'

        write = True

        if os.path.exists(out_fname):
            msgbox = qg.QMessageBox()
            msgbox.setText('Overwrite {} ?'.format(out_fname))
            msgbox.setStandardButtons(qg.QMessageBox.Yes | qg.QMessageBox.No)
            ret = msgbox.exec_()
            if ret == qg.QMessageBox.Yes:
                print('Overwriting ' + out_fname)
                os.rename(out_fname, out_fname + '.bak') 
            else:
                write = False

        if write:
            with open(out_fname, 'w') as fid:
                fid.write('\n'.join(chans))

            fid.close()

    def set_image_left(self):
        """
        helper
        """
        where = 'left'
        which_text = str(self.comboBoxLeftImage.currentText())
        which = IMG_BY_LABEL[which_text]
        print(which)
        self.set_image(where, which)

    def set_image_right(self):
        """
        helper
        """
        where = 'right'
        which_text = str(self.comboBoxRightImage.currentText())
        which = IMG_BY_LABEL[which_text]
        self.set_image(where, which)

    def set_image(self, where, which):
        """
        defines which type of image we show
        """
        if where == 'left':
            self.image_to_show_left = which
        else:
            self.image_to_show_right = which

        index = self.tableViewChannels.selectedIndexes()
        if index:
            self.item_action(index[0])


def main():
    APP = qg.QApplication(sys.argv)
    APP.setStyle(options['guistyle'])
    WIN = GuiOverview()
    WIN.setWindowTitle('Combinato channel overview')
    WIN.showMaximized()
    APP.exec_()

if __name__ == "__main__":
    main()
