# JN 2015-06-06 refactoring
from __future__ import print_function, division, absolute_import

import os
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox,
    QListWidget, QVBoxLayout, QLabel)

from .. import get_relevant_folders, get_time_files

POS_FNAME = 'do_manual_pos.txt'
NEG_FNAME = 'do_manual_neg.txt'


class PickJobList(QDialog):
    """
    pick a session for sorting
    """

    def __init__(self, folder, parent=None):
        super(PickJobList, self).__init__(parent)

        jobs = []
        for fname in (POS_FNAME, NEG_FNAME):
            if os.path.exists(fname):
                jobs.append(fname)

        items = get_relevant_folders(folder)
        labels = sorted(set([item[2] for item in items]))

        items = get_time_files(folder)
        timefiles = ['{} {} {}'.format(*item) for item in items]

        self.labelList = QListWidget()
        self.labelList.addItems(labels)
        self.labelList.setCurrentRow(0)

        self.jobfileList = QListWidget()
        self.jobfileList.addItems(jobs)
        self.jobfileList.setCurrentRow(0)

        self.timesList = QListWidget()
        self.timesList.addItem('All')
        self.timesList.addItems(timefiles)
        self.timesList.setCurrentRow(0)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonBox.setShortcutEnabled(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Job Files"))
        layout.addWidget(self.jobfileList)
        layout.addWidget(QLabel("Labels"))
        layout.addWidget(self.labelList)
        layout.addWidget(QLabel("Time Files"))
        layout.addWidget(self.timesList)

        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)


class GotoJob(QDialog):
    """
    pick a session for sorting
    """

    def __init__(self, jobs, parent=None):
        super(GotoJob, self).__init__(parent)

        self.joblist = QListWidget()
        items = ['{} {}'.format(i, name) for i, name in enumerate(jobs)]
        self.joblist.addItems(items)
        self.joblist.setCurrentRow(0)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonBox.setShortcutEnabled(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Jobs"))
        layout.addWidget(self.joblist)

        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
