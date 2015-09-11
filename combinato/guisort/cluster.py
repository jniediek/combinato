# -*- encoding: utf-8 -*-
# JN 2015-01-06
# refactoring
from __future__ import print_function, division, absolute_import
from PyQt4.QtGui import QPixmap


class Cluster(object):
    """
    represents a cluster
    could as well be a dictionary
    can objects vanish from memory, so that the
    'value' problem of dictionaries is solved?
    """
    def __init__(self, name, imagepath, spikes, times):
        self.name = name
        self.imagepath = imagepath
        self.image = QPixmap(imagepath)
        self.spikes = spikes
        self.meanspike = self.spikes.mean(0)
        self.times = times
