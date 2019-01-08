# -*- coding: utf-8 -*-
#! JN 2014-10-23 Add spike viewer to SWR viewer

from PyQt5.QtWidgets import QDialog
#from PyQt5.QtCore import *
#from PyQt5.QtGui import *


from .sWidgets import *
from ui_spikes import Ui_Dialog

import numpy as np
from matplotlib.gridspec import GridSpec

gs = GridSpec(1, 1, top=.95, bottom=.05, left=.05, right=.95)


class SpikeView(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super(SpikeView, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent

        
        self.pushButton.clicked.connect(self.update)
        
        self.figure = MplCanvas(self)
        self.verticalLayout.addWidget(self.figure)
        self.ax = self.figure.fig.add_subplot(gs[0])
        self.update()

    def update(self):
        self.ax.cla()

        # get the current list of channels
        ctext = self.comboBoxChannel.currentText()
        chs = self.parent.checked_channels
        self.comboBoxChannel.clear()
        setidx = None
        for i, ch in enumerate(chs):
            self.comboBoxChannel.addItem(ch)
            if ch == ctext:
                setidx = i

        if setidx is not None:
            self.comboBoxChannel.setCurrentIndex(setidx)

        key = self.comboBoxChannel.currentText()

        spikes = self.parent.h5man.spm.get_sp_data(key, 'spikes')
        print(spikes)

        x = np.arange(spikes.shape[1])
        self.ax.plot(x, spikes.T, 'b', lw=1)
        self.ax.plot(x, spikes.mean(0), 'k', lw=2)
        self.ax.set_xlim((x[0], x[-1]))

        self.figure.draw()
