#!/usr/bin/env python3
"""
this file contains the code for the spike sorting GUI
"""
from __future__ import print_function, division, absolute_import
import sys
import os
from getpass import getuser
from time import strftime
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow, QApplication, QListView,
        QMessageBox, QFileDialog)

from .ui_sorter import Ui_MainWindow

from .sort_widgets import AllGroupsFigure, ComparisonFigure,\
    GroupOverviewFigure
from .raster_figure import RasterFigure
from .backend import Backend
from .load_joblist import PickJobList, GotoJob
from .picksession import PickSessionDialog
from .group_list_model import ClusterDelegate
from .basics import spikeDist

import numpy as np

from .. import options, TYPE_ART, TYPE_MU, TYPE_SU, TYPE_NO

imageSize = 260
stylesheet = 'QListView:focus { background-color: rgb(240, 255, 255)}'
DEBUG = options['Debug']
LOGFILENAME = 'css_gui_log.txt'


class SpikeSorter(QMainWindow, Ui_MainWindow):
    """
    main class
    """
    def __init__(self, parent=None, arg=None):
        super(SpikeSorter, self).__init__(parent)

        self.setupUi(self)
        self.backend = None
        self.groupOverviewFigure = GroupOverviewFigure(self.centralwidget)
        self.allGroupsFigureDirty = True

        self.oneGroupLayout.addWidget(self.groupOverviewFigure)

        self.allGroupsFigure = AllGroupsFigure(self.centralwidget)
        self.allGroupsFigure.fig.canvas.mpl_connect('button_press_event',
                                                    self.onclick)
        self.allGroupsLayout.addWidget(self.allGroupsFigure)
        self.groupsComparisonFigure = ComparisonFigure(self.centralwidget)
        self.compareFigureLayout.addWidget(self.groupsComparisonFigure)
        view = self.listView
        view.setViewMode(QListView.IconMode)
        view.setResizeMode(QListView.Adjust)
        view.setItemDelegate(ClusterDelegate(self))
        view.setStyleSheet(stylesheet)
        view.addAction(self.actionMakeArtifact)
        view.addAction(self.actionMarkCluster)

        self.allGroupsTab.addAction(self.actionAutoassign)

        for action in (self.actionMakeArtifact,
                       self.actionMarkCluster):
            action.setShortcutContext(Qt.WidgetShortcut)

        self.groupComboBox.addAction(self.actionNextGroup)
        self.actionNewGroup.triggered.connect(self.actionNewGroup_triggered)
        self.pushButtonSave.clicked.connect(self.save_one_group)
        self.pushButtonMerge.clicked.connect(self.actionMerge_triggered)
        self.pushButtonTidy.clicked.connect(self.actionTidyGroups_triggered)

        self.groupComboBox.currentIndexChanged.\
            connect(self.updateListView)
        self.tabWidget.setTabEnabled(3, False)

        self.tabWidget.currentChanged.\
            connect(self.updateActiveTab)

        self.autoassignPushButton.clicked.\
            connect(self.on_actionAutoassign_triggered)

        self.multiRadioButton.toggled.connect(self.saveTypeMU)
        self.singleRadioButton.toggled.connect(self.saveTypeSU)
        self.artifactRadioButton.toggled.connect(self.saveTypeArti)

        self.actionOpen.triggered.connect(self.actionOpen_triggered)
        self.comparePlotpushButton.clicked.connect(self.compare_groups)

        self.actionSave.triggered.connect(self.actionSave_triggered)
        self.actionOpenJobs.triggered.connect(self.actionOpenJobs_triggered)
        self.actionNextJob.triggered.connect(self.actionNextJob_triggered)
        self.actionMergeAll.triggered.connect(self.actionMergeAll_triggered)
        self.actionGotoJob.triggered.connect(self.actionGotoJob_triggered)
        self.actionMerge.triggered.connect(self.actionMerge_triggered)
        self.actionMerge_one_unit_groups.triggered.\
            connect(self.action_MergeOnes_triggered)
        self.actionSave_to_Matfile.triggered.connect(self.action_export_triggered)

        if len(arg) > 1:
            self.basedir = os.path.dirname(arg)
        else:
            self.basedir = os.getcwd()

        try:
            self.logfid = open(LOGFILENAME, 'a')
        except PermissionError:
            print('Not logging!')
            self.logfid = None

        self.user = getuser()

        self.rasterFigure = None

        if 'RunGuiWithRaster' in options:
            if options['RunGuiWithRaster']:
                self.tabWidget.setTabEnabled(3, True)
                self.init_raster()

    def init_raster(self):
        import pandas as pd
        from .. import raster_options

        # the following should read all standard experiment codes
        # e.g. 'fn2' or 'ospr3' (string plus one digit)
        base = os.path.basename(self.basedir)
        try:
            pat = base[:3]
            paradigm = ''
            for char in base[6:]:
                paradigm += char
                if char.isdigit():
                    break

        except ValueError:
            print('Unable to initialize raster meta data')
            return
        #infix = '{:03d}{}{}'.format(pat, raster_options['infix'], run)
        infix = pat+paradigm
        fname_frame = 'frame_{}.h5'.format(infix)
        frame = pd.read_hdf(fname_frame, raster_options['frame_name'])
        meta_prefix = raster_options['meta_prefix']
        image_path = os.path.join(meta_prefix, infix)
        if paradigm.startswith('fn'):
            image_path = os.path.join(meta_prefix, infix, infix)

        # now initialize the data
        self.rasterFigure = RasterFigure(self.centralwidget)
        self.rasterLayout.addWidget(self.rasterFigure)
        self.rasterFigure.set_paradigm_data(frame, image_path)
        self.pushButtonUpdateRasters.setEnabled(True)
        self.lineEditStimSelect.setEnabled(True)
        self.pushButtonUpdateRasters.clicked.connect(self.actionUpdateRasters.trigger)
        self.actionUpdateRasters.triggered.connect(self.update_rasters)

    def update_rasters(self):
        if self.backend is None:
            return
        gid = str(self.groupComboBox.currentText())
        group = self.backend.sessions.groupsByName[gid]
        current_paradigm = str(self.lineEditStimSelect.text())

        indexes = self.listView.selectedIndexes()
        if indexes:
            index = indexes[0].row()
        else:
            index = -4

        tlist = []
        clist = []
        for i, cluster in enumerate(group.clusters):
            if i == index:
                clist.append(cluster.times)
            else:
                tlist.append(cluster.times)

        times = []
        for mylist in (tlist, clist):
            if mylist:
                times.append(np.hstack(mylist))

        self.rasterFigure.update_figure(times, current_paradigm)

    def save_one_group(self):
        """
        save a plot of one group
        """
        fout = QFileDialog.getSaveFileName(self,
               "Save as Image", os.getcwd(),
               "Image files (*.jpg *.pdf *.png)")
        self.groupOverviewFigure.save_as_file(str(fout[0]), dpi=300)

    def on_actionAutoassign_triggered(self):
        print(self.sender().text())

        if self.backend is None:
            return
        elif self.backend.sessions is None:
            return

        groupName = str(self.groupComboBox.currentText())
        group = self.backend.sessions.groupsByName[groupName]
        print('Auto-assigning group {}'.format(group))

        if group == '':
            return

        indices = self.listView.selectedIndexes()
        if len(indices) == 0:
            return
        index = indices[0].row()

        selectedMean = group.clusters[index].meanspike
        means = dict()

        for name, group in self.backend.sessions.groupsByName.items():
            if name not in ['Unassigned', 'Artifacts']:
                means[name] = np.array(group.meandata).mean(0)

        dist = np.inf
        minimizer = None

        for name, mean in means.items():
            if name != groupName:
                d = spikeDist(mean, selectedMean)
                if d < dist:
                    dist = d
                    minimizer = name

        print('Moving to ' + minimizer + ', distance {:2f}'.format(dist))
        self.move(self.backend.sessions.groupsByName[minimizer])
        self.updateActiveTab()
        l = self.backend.sessions.groupsByName[minimizer].assignAxis.get_lines()
        l[-1].set_color('r')
        self.allGroupsFigure.draw()

    def onclick(self, event):

        if (event.inaxes is not None) and\
           (self.backend is not None) and\
           (self.backend.sessions is not None):
            num = int(event.inaxes.get_label())
            src = self.listView
            dst = self.backend.sessions.groupsById[num]
            self.move(dst, src)
            self.updateActiveTab()

    def actionOpen_triggered(self, checked, filename=None):
        if self.backend is not None:
            if self.backend.sessions is not None:
                if self.backend.sessions.dirty:
                    self.actionSave.trigger()

                    del self.backend
                    self.backend = None

        dialog = PickSessionDialog(self.basedir, self)

        if dialog.exec_():
            item = str(dialog.sessionList.selectedItems()[0].text()).split()
            folder = ' '.join(item[0:-2])
            datafile = item[-2]
            sortingfile = item[-1]
            print(folder, datafile, sortingfile)
            item = str(dialog.timesList.selectedItems()[0].text()).split()
            try:
                start_time_ms = int(item[1])/1000
                stop_time_ms = int(item[2])/1000
            except IndexError:
                start_time_ms = 0
                stop_time_ms = np.inf

            print('Opening {} {} {} ({} ms to {} ms)'.
                  format(folder, datafile, sortingfile,
                         start_time_ms, stop_time_ms))

            datapath = os.path.join(folder, datafile)
            sessionpath = os.path.join(folder, sortingfile)

            self.backend = Backend(datapath, sessionpath,
                                   start_time_ms, stop_time_ms)

            self.status_string = 'Datafile: {} Sorting: {}'.format(datafile,
                                                                   sortingfile)
            self.folderLabel.setText(self.status_string)
        else:
            return

        self.update_after_open()

    def open_job(self, job_to_open):
        """
        open a job from the list
        """
        if self.backend is not None:
            if self.backend.sessions is not None:
                if self.backend.sessions.dirty:
                    self.actionSave.trigger()

                    del self.backend
                    self.backend = None

        job = self.job_names[job_to_open]

        datapath = os.path.join(self.basedir, job)
        sessionpath = os.path.join(self.basedir, os.path.dirname(job),
                                   self.job_label)

        self.backend = Backend(datapath, sessionpath,
                               self.job_start_time_ms, self.job_stop_time_ms)
        self.current_job = job_to_open
        self.status_string = 'Job: {}/{} Datafile: {}\
             Sorting: {}'.format(self.current_job + 1,
                                 len(self.job_names),
                                 job, self.job_label)

        self.folderLabel.setText(self.status_string)
        self.update_after_open()

    def update_after_open(self):
        self.allGroupsFigureDirty = True
        self.actionNewGroup.setEnabled(True)

        sps = self.backend.sorting_manager.\
            get_samples_per_spike()

        t = (self.backend.sessions.start_time,
             self.backend.sessions.stop_time)

        thresholds = self.backend.get_thresholds()
        self.groupOverviewFigure.setOptions((0, sps),
                                            t,
                                            self.backend.sign,
                                            thresholds)

        self.updateGroupsList()
        self.updateActiveTab()

    def actionNextJob_triggered(self):
        """
        go to the next job
        """
        cj = self.current_job
        if cj + 1 < len(self.job_names):
            self.open_job(cj + 1)
        else:
            print('Last job open')
            return

    def actionGotoJob_triggered(self):
        if self.backend is not None:
            if self.backend.sessions is not None:
                if self.backend.sessions.dirty:
                    self.actionSave.trigger()

                    del self.backend
                    self.backend = None

        dialog = GotoJob(self.job_names, self)

        if dialog.exec_():
            item = str(dialog.joblist.selectedItems()[0].text())
            print(item)
            jobid = int(item.split()[0])
            print(jobid)
            self.open_job(jobid)

    def actionOpenJobs_triggered(self):
        """
        open a job list
        """
        if self.backend is not None:
            if self.backend.sessions is not None:
                if self.backend.sessions.dirty:
                    self.actionSave.trigger()

                    del self.backend
                    self.backend = None

        dialog = PickJobList(self.basedir, self)

        if dialog.exec_():
            jobfile = str(dialog.jobfileList.selectedItems()[0].text())
            with open(jobfile, 'r') as fid:
                jobs = [line.strip() for line in fid.readlines()]
            fid.close()

            label = str(dialog.labelList.selectedItems()[0].text())

            item = str(dialog.timesList.selectedItems()[0].text()).split()
            try:
                start_time_ms = int(item[1])/1000
                stop_time_ms = int(item[2])/1000
            except IndexError:
                start_time_ms = 0
                stop_time_ms = np.inf

            # store info for later loading
            self.job_names = jobs
            self.job_label = label
            self.job_start_time_ms = start_time_ms
            self.job_stop_time_ms = stop_time_ms
            job_to_open = 0

            print('Loaded {} jobs from {} {} ({} ms to {} ms)'.
                  format(len(jobs), self.basedir, jobfile,
                         start_time_ms, stop_time_ms))

            self.open_job(job_to_open)

    def actionNewGroup_triggered(self):
        if self.backend.sessions is None:
            return

        self.backend.sessions.newGroup()
        oldtext = self.groupComboBox.currentText()
        self.updateGroupsList(oldtext)
        self.allGroupsFigureDirty = True
        self.updateActiveTab()

    def actionSetTime_triggered(self, checked):
        if self.backend is None:
            return

        dialog = PickTimeDialog(self)

        if dialog.exec_():
            item = [str(item.text()) for
                    item in dialog.widget.selectedItems()][0]
            start, _, stop, fname = item.split()
            print(start, stop, fname[1:-2])
            start, stop = [int(x)/1000 for x in (start, stop)]
            self.backend.set_sign_start_stop('pos', start, stop)

    def actionSelectSession_triggered(self, checked):

        if self.backend is None:
            return

        if self.backend.sessions is not None:
            if self.backend.sessions.dirty:
                self.actionSave.trigger()

        dialog = PickSessionDialog(self)

        if dialog.exec_():
            item = [str(item.text()) for
                    item in dialog.widget.selectedItems()][0]
            # print('Opening ' + item)
            self.backend.open_sessions(item)

        else:
            return

        # self.sessionLabel.setText(text)

        self.allGroupsFigureDirty = True
        self.actionNewGroup.setEnabled(True)
        x = self.backend.sorting_manager.\
            get_samples_per_spike()
        # total time in seconds
        t = (self.backend.sessions.start_time,
             self.backend.sessions.stop_time)

        # wrong place, should be executed only once!
        self.groupOverviewFigure.setOptions((0, x), t,
                                            self.backend.sign)

        self.updateGroupsList()
        self.updateActiveTab()

    def actionMergeAll_triggered(self):
        """
        move all clusters to the first group
        """
        groups = self.backend.sessions.groupsByName
        names = sorted(groups.keys())
        if len(names) <= 3:
            print('Nothing to move, only groups: {}'.format(names))
            return

        target = names[0]
        print('Moving everything to group {}'.format(target))

        for name in names[1:]:
            try:
                int(name)
                self.merge_groups(name, target)
            except ValueError:
                print('not moving {}'.format(name))

    def actionMerge_triggered(self):
        """
        move all clusters from second group to first group
        """

        current = str(self.tabWidget.currentWidget().objectName())
        if current == 'compareTab':
            tgt = str(self.groupOnecomboBox.currentText())
            src = str(self.groupTwoComboBox.currentText())
            msg = "Would you like to merge "\
                  "group {} into group {}?".format(src, tgt)
        else:
            return

        try:
            int(tgt)
            int(src)
        except ValueError:
            print('Not merging {} and {}!'.format(src, tgt))
            return

        if not len(tgt) * len(src):
            return

        box = QMessageBox(QMessageBox.Question, 'Merging groups', msg,
                          buttons=(QMessageBox.Ok | QMessageBox.Cancel))

        box.exec_()
        if box.result() == QMessageBox.Ok:
            self.merge_groups(src, tgt)

    def action_MergeOnes_triggered(self):
        """
        merge all groups with only one member
        """
        groups = self.backend.sessions.groupsById
        shorties = []

        for gid in groups.keys():
            if (gid > 0) and (len(groups[gid].clusters) == 1):
               shorties.append(gid)

        if len(shorties):
            tgt = shorties[0]

        for src in shorties[1:]:
            print('Merging {} to {}'.format(src, tgt))
            self.merge_groups(src, tgt, mode='by-id', finalize=False)

        self.listView.reset()
        self.updateActiveTab()


    def merge_groups(self, src, tgt, mode='by-name', finalize=True):
        """
        merge two groups
        """
        if mode == 'by-name':
            groups = self.backend.sessions.groupsByName
        elif mode == 'by-id':
            groups = self.backend.sessions.groupsById
        else:
            return
        clusters = groups[src].removeClusters()
        groups[tgt].addClusters(clusters)
        self.backend.sessions.dirty = True

        if finalize:
            self.listView.reset()
            self.updateActiveTab()

    def compare_groups(self):
        group1name = str(self.groupOnecomboBox.currentText())
        group2name = str(self.groupTwoComboBox.currentText())

        group1 = self.backend.sessions.groupsByName[group1name]
        group2 = self.backend.sessions.groupsByName[group2name]

        self.groupsComparisonFigure.xcorr(group1, group2)

    def actionSave_triggered(self):
        msgBox = QMessageBox()
        msgBox.setText("Save changes to current session?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgBox.setDefaultButton(QMessageBox.Yes)
        ret = msgBox.exec_()
        if ret == QMessageBox.Yes:
            self.backend.sessions.save()
            now = strftime('%Y-%m-%d_%H-%M-%S')
            if self.logfid is not None:
                self.logfid.write('{} {} saved {}\n'.format(now, self.user,
                                                        self.status_string))
            self.backend.sessions.dirty = False

    def on_actionMarkCluster_triggered(self):

        name = self.tabWidget.currentWidget().objectName()
        indexes = self.listView.selectedIndexes()
        if len(indexes) == 0:
            return
        index = indexes[0].row()

        groupName = str(self.groupComboBox.currentText())
        if groupName == '':
            return

        if name == 'oneGroupTab':
            group = self.backend.sessions.groupsByName[groupName]
            clusterdata = np.diff(group.clusters[index].times)
            idx = (clusterdata < options['compute_isi_upto_ms']) & (clusterdata > 0)
            clusterdata = clusterdata[idx]
            self.groupOverviewFigure.mark(index, clusterdata)

        elif name == 'allGroupsTab':
            self.allGroupsFigure.mark(groupName, index)


    def on_actionMakeArtifact_triggered(self):
        self.move(self.backend.sessions.groupsByName['Artifacts'])
        self.updateGroupInfo()
        self.updateActiveTab()

    def on_actionNextGroup_triggered(self):
        """
        rotate through groups
        """
        ngroups = len(self.backend.sessions.groupsByName)
        if self.backend is not None:
            index = self.groupComboBox.currentIndex()
            if index + 1 < ngroups:
                self.groupComboBox.setCurrentIndex(index + 1)
            elif index + 1 == ngroups:
                self.groupComboBox.setCurrentIndex(0)

    def updateListView(self, e):
        index = str(self.groupComboBox.currentText())
        if index == '':
            return
        model = self.backend.sessions.groupsByName[index]
        self.listView.setModel(model)
        self.listView.selectionModel().currentChanged.\
            connect(self.on_actionMarkCluster_triggered)
        self.setRadioButtons(index)
        self.updateActiveTab()

    def setRadioButtons(self, index):
        model = self.backend.sessions.groupsByName[index]
        group_type = model.group_type
        if group_type == TYPE_MU:
            button = self.multiRadioButton
        elif group_type in (TYPE_ART, TYPE_NO):
            button = self.artifactRadioButton
        elif group_type == TYPE_SU:
            button = self.singleRadioButton
        else:
            raise Warning('Type not defined')

        button.setChecked(True)

    def save_type(self, new_type):
        index = str(self.groupComboBox.currentText())
        model = self.backend.sessions.groupsByName[index]
        model.group_type = new_type
        self.backend.sessions.dirty = True
        self.allGroupsFigureDirty = True
        self.updateActiveTab()

    def saveTypeMU(self, checked):
        """
        dispatch
        """
        if checked:
            self.save_type(TYPE_MU)

    def saveTypeSU(self, checked):
        """
        dispatch
        """
        if checked:
            self.save_type(TYPE_SU)

    def saveTypeArti(self, checked):
        """
        dispatch
        """
        if checked:
            self.save_type(TYPE_ART)

    def move(self, dst, src=None):
        self.backend.sessions.dirty = True
        if src is None:
            src = self.listView
        indexes = src.selectedIndexes()

        for obj in (src.model(), dst):
            obj.beginResetModel()
       
        for index in indexes:
            cl = src.model().popCluster(index.row())
            dst.addCluster(cl)

        for obj in (src.model(), dst):
            obj.endResetModel()

        src.reset()

        self.updateGroupInfo()

    def updateGroupsList(self, oldtext=None):
        groupsById = self.backend.sessions.groupsById
        box = self.groupComboBox
        box.clear()
        index = 0
        setindex = None
        for group in sorted(groupsById.keys()):
            name = groupsById[group].name
            box.addItem(name)
            if name == oldtext:
                setindex = index
            index += 1

        if setindex is not None:
            box.setCurrentIndex(setindex)

        box.setEnabled(True)

    def updateActiveTab(self):

        current = self.tabWidget.currentWidget().objectName()

        if current == 'allGroupsTab':
            self.updateAssignPlot()

        elif current == 'oneGroupTab':
            self.updateGroupInfo()

        elif current == 'compareTab':
            self.updateCompareTab()

    def updateCompareTab(self):
        if self.backend is None:
            return
        groupsById = self.backend.sessions.groupsById
        box1 = self.groupOnecomboBox
        box2 = self.groupTwoComboBox
        boxes = (box1, box2)
        for box in boxes:
            box.clear()

        for group in sorted(groupsById.keys()):
            for box in boxes:
                name = groupsById[group].name
                box.addItem(name)
                box.setEnabled(True)

    def updateGroupInfo(self):

        groupName = str(self.groupComboBox.currentText())
        if groupName == '':
            return
        group = self.backend.sessions.groupsByName[groupName]
        self.groupOverviewFigure.updateInfo(group)

    def updateAssignPlot(self):
        """
        make sure plot with all mean spikes is up-to-date
        """

        # The speed could still be improved in this function
        if (self.backend is None) or\
           (self.backend.sessions is None):
            return

        session = self.backend.sessions

        index = []

        for name, group in session.groupsById.items():
            if group.group_type not in [TYPE_ART, TYPE_NO]:
                index.append(name)

        index.sort()
        if self.allGroupsFigureDirty:
            self.allGroupsFigure.\
                addAxes(self.backend.x, session, index)
            self.allGroupsFigureDirty = False
        else:
            self.allGroupsFigure.updateInfo(index)

    def actionTidyGroups_triggered(self):
        if self.backend is None:
            return
        if self.backend.sessions is None:
            return

        t1 = time.time()
        self.backend.sessions.reorganize_groups()
        print('Reorganization took {:.3f} seconds'.format(time.time() - t1))
        self.allGroupsFigureDirty = True
        self.updateGroupsList()
        self.updateActiveTab()

    def action_export_triggered(self):
        if self.backend is None:
            return
        if self.backend.sessions is None:
            return
        datafilename, extn = os.path.splitext(self.backend.datafile)
        outfname = os.path.join(self.backend.folder, datafilename + '.mat')
        print('Saving to {}'.format(outfname))
        self.backend.sessions.export_to_matfile(outfname)


def except_hook(cls, exception, traceback):
    sys.__excepthook__(cls, exception, traceback)


def main():
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    app.setStyle(options['guistyle'])
    win = SpikeSorter(parent=None, arg=sys.argv)
    win.setWindowTitle('Combinato Spike Sorter')
    win.showMaximized()
    app.exec_()
