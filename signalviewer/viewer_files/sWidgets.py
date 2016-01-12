import os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
# would like to migrate to QT5, but matplotlib in Debian isn't ready
# it doesn't have the backend
import numpy  as np
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as mpl
from matplotlib.figure import Figure


class MplCanvas(FigureCanvas):
    
    def __init__(self, parent=None, width=5, height=5, dpi=75):
        self.fig = Figure(figsize=(width, height),dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        color = QPalette().color(QPalette.Light)
        self.fig.patch.set_color((color.red()/255., color.green()/255., color.blue()/255.))

    def setFixedSize(self):
        self.setSizePolicy(QSizePolicy.Fixed,  QSizePolicy.Fixed)
        self.updateGeometry()

    def delAxes(self):
        pass

    def __del__(self):
        mpl.close(self.fig)
