"""
list model for guisort
"""

from __future__ import print_function, division, absolute_import

import numpy as np

from PyQt4.QtCore import QAbstractListModel, Qt,\
    QModelIndex, QSize, QPoint, QVariant
from PyQt4.QtGui import QStyledItemDelegate, QPen, QStyle
from .. import options


class GroupListModel(QAbstractListModel):
    """
    represents a group of clusters
    """
    def __init__(self, name, groupId, clusters, group_type):
        super(GroupListModel, self).__init__()
        self.name = name
        self.groupId = groupId
        self.clusters = clusters
        self.group_type = group_type
        self.assignAxis = None
        self.densitydata = None
        self.upto = options['compute_isi_upto_ms']
        # self.bins = options['density_hist_bins']
        self.bins = None
        self.times = None
        self.meandata = None
        self.maximadata = None
        self.isidata = None
        self.update()

    def update(self):
        """
        update information about the group
        """
        if not len(self.clusters):
            self.meandata = []
            self.densitydata = []
            self.times = []
            self.isidata = []
            return
        allspikes = np.vstack([c.spikes for c in self.clusters]).T
        self.meandata = [c.meanspike for c in self.clusters]

        max_of_means = np.max(np.abs(self.meandata))
        bins_density = np.linspace(-2*max_of_means,
                                   2*max_of_means,
                                   2*max_of_means)

        density = [np.histogram(row, bins=bins_density)[0]
                   for row in allspikes]
        timelist = [c.times for c in self.clusters]
        self.times = np.concatenate(timelist)
        self.times.sort()
        data = np.diff(self.times)
        self.isidata = data[data <= self.upto]
        maxima = [c.spikes.max(1) for c in self.clusters]

        self.densitydata = np.array(density).T
        self.maximadata = np.concatenate(maxima)

#        for obj in (self.densitydata,
#                    #self.meandata,
#                    self.isidata,
#                    self.maximadata,
#                    self.times):
#            #print(obj.shape)

    def addCluster(self, cluster):
        """
        add a cluster
        """
        self.clusters.append(cluster)
        self.update()

    def popCluster(self, index):
        cl = self.clusters.pop(index)
        self.update()
        return cl

    def removeClusters(self):
        ret = list(self.clusters)
        self.clusters = []
        self.update()
        return ret

    def addClusters(self, clusters):
        self.clusters += clusters
        self.update()

    def __len__(self):
        return(len(self.clusters))

    def data(self, index, role=Qt.DisplayRole):
        if (not index.isValid() or
            not (0 <= index.row() < len(self.clusters))):
            return QVariant()
        
        if role == Qt.DisplayRole:
            # maybe some different information?
            cluster = self.clusters[index.row()]
            return QVariant(str(cluster.name))

        return QVariant()

    def rowCount(self, index=QModelIndex()):
        return len(self.clusters)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        return QVariant()


class ClusterDelegate(QStyledItemDelegate):

    def __init__(self, parent=None):
        super(ClusterDelegate, self).__init__(parent)

    def paint(self, painter, option, index):
        if index.model() is None:
            return
        image = index.model().clusters[index.row()].image
        painter.save()

        if option.state & QStyle.State_Selected:
            pen = QPen(Qt.black, 2)
            painter.setPen(pen)
            painter.drawRect(option.rect.adjusted(+2, +2, -2, -2))

        painter.drawPixmap(QPoint(option.rect.x() + 5, option.rect.y() + 5) , image)
        painter.restore()

    def sizeHint(self, option, index):
        return(QSize(210, 210))
