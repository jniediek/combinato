# JN 2015-01-06 refactoring
from __future__ import print_function, division, absolute_import

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QVBoxLayout, QLabel, QSizePolicy

from .. import get_relevant_folders, get_time_files


class PickSessionDialog(QDialog):
    """
    pick a session for sorting
    """

    def __init__(self, folder, parent=None):
        super(PickSessionDialog, self).__init__(parent)

        items = get_relevant_folders(folder)
        sortings = ['{} {} {}'.format(*item) for item in items]

        items = get_time_files(folder)
        timefiles = ['{} {} {}'.format(*item) for item in items]

        self.sessionList = QListWidget()
        self.sessionList.addItems(sortings)
        self.sessionList.setCurrentRow(0)

        self.timesList = QListWidget()
        self.timesList.addItem('All')
        self.timesList.addItems(timefiles)
        self.timesList.setCurrentRow(0)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        buttonBox.setShortcutEnabled(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Sorted Data"))
        layout.addWidget(self.sessionList)
        layout.addWidget(QLabel("Time Files"))
        layout.addWidget(self.timesList)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.setMinimumWidth(self.sessionList.width())
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.adjustSize()
