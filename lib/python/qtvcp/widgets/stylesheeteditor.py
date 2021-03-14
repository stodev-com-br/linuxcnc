#!/usr/bin/python3
############################################################################
##
## Copyright (C) 2010 Hans-Peter Jansen <hpj@urpla.net>.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
###########################################################################

import os
import sys
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QFile, QRegExp, Qt, QTextStream
from PyQt5.QtWidgets import (QApplication, QDialog, QFileDialog, QMessageBox,
        QStyleFactory, QWidget, QColorDialog)
from PyQt5 import QtGui, QtCore

from qtvcp.core import Info, Path
from qtvcp.qt_makegui import VCPWindow
INFO = Info()
PATH = Path()
WIDGETS = VCPWindow()

DATADIR = os.path.abspath( os.path.dirname( __file__ ) )

class StyleSheetEditor(QDialog):
    def __init__(self, parent=WIDGETS, path=None):
        super(StyleSheetEditor, self).__init__(parent)
        self.setMinimumSize(600, 400)
        # Load the widgets UI file:
        self.filename = os.path.join(INFO.LIB_PATH,'widgets_ui', 'style_dialog.ui')
        try:
            self.instance = uic.loadUi(self.filename, self)
        except AttributeError as e:
            LOG.critical(e)
        self.styleSheetCombo.setFixedWidth(200)

        self.setWindowTitle('Style Sheet Editor Dialog');
        self.parent = parent
        if PATH:
            self.setPath()
        self.styleSheetCombo.currentIndexChanged.connect(self.selectionChanged)
        self.preferencePath = 'DEFAULT'

    def load_dialog(self):
        if WIDGETS.PREFS_:
            path =  WIDGETS.PREFS_.getpref('style_QSS_Path', 'DEFAULT' , str, 'BOOK_KEEPING')
            self.preferencePath = path
            self.loadedItem.setData( path, role = QtCore.Qt.UserRole + 1)
            self.styleSheetCombo.setToolTip('<b>{}</b>'.format(path))
        self.origStyleSheet = self.parent.styleSheet()
        self.styleTextView.setPlainText(self.origStyleSheet)
        self.show()
        self.activateWindow()

    # keep areference to loadedItem because the path will be added when the
    # dialog is shown.
    # Model holds a title and a path
    # search in the builtin folder for the screen and
    # in the users's config directory
    def setPath(self):
        model = self.styleSheetCombo.model()
        self.loadedItem = QtGui.QStandardItem('As Loaded')
        self.loadedItem.setData( 'As Loaded', role = QtCore.Qt.UserRole + 1)
        model.appendRow(self.loadedItem)
        item = QtGui.QStandardItem('None')
        item.setData( 'None', role = QtCore.Qt.UserRole + 1)
        model.appendRow(item)
        # check for default qss from qtvcp's default folders
        if PATH.IS_SCREEN:
            DIR = PATH.SCREENDIR
            BNAME = PATH.BASENAME
        else:
            DIR = PATH.PANELDIR
            BNAME = PATH.BASENAME
        qssname = os.path.join(DIR, BNAME)
        try:
            fileNames= [f for f in os.listdir(qssname) if f.endswith('.qss')]
            for i in(fileNames):
                item = QtGui.QStandardItem(i)
                item.setData(os.path.join(qssname, i), role = QtCore.Qt.UserRole + 1)
                model.appendRow(item)
        except Exception as e:
            print(e)

        # check for qss in the users's config folder 
        localqss = PATH.CONFIGPATH
        try:
            fileNames= [f for f in os.listdir(localqss) if f.endswith('.qss')]
            for i in(fileNames):
                item = QtGui.QStandardItem(i)
                item.setData(os.path.join(localqss, i), role = QtCore.Qt.UserRole + 1)
                model.appendRow(item)
        except Exception as e:
            print(e)

    def selectionChanged(self,i):
        path = self.styleSheetCombo.itemData(i,role = QtCore.Qt.UserRole + 1)
        name = self.styleSheetCombo.itemData(i,role = QtCore.Qt.DisplayRole)
        self.styleSheetCombo.setToolTip('<b>{}</b>'.format(path))
        self.loadStyleSheet(path)

    @pyqtSlot()
    def on_styleTextView_textChanged(self):
        self.applyButton.setEnabled(True)

    @pyqtSlot()
    def on_applyButton_clicked(self):
        self.parent.setStyleSheet("")
        if self.tabWidget.currentIndex() == 0:
            self.parent.setStyleSheet(self.styleTextView.toPlainText())
            if WIDGETS.PREFS_:
                index = self.styleSheetCombo.currentIndex()
                path = self.styleSheetCombo.itemData(index,role = QtCore.Qt.UserRole + 1)
                WIDGETS.PREFS_.putpref('style_QSS_Path', path , str, 'BOOK_KEEPING')
        else:
            self.parent.setStyleSheet(self.styleTextEdit.toPlainText())

        # styles can have affect on the dialog widgets
        # make sure one can still read the combo box
        self.styleSheetCombo.setFixedWidth(200)

    @pyqtSlot()
    def on_openButton_clicked(self):
        dialog = QFileDialog(self)
        if PATH.IS_SCREEN:
            DIR = PATH.SCREENDIR
        else:
            DIR = PATH.PANELDIR
        dialog.setDirectory(DIR)
        fileName, _ = dialog.getOpenFileName()
        if fileName:
            file = QFile(fileName)
            file.open(QFile.ReadOnly)
            styleSheet = file.readAll()
            if sys.version_info.major > 2:
                styleSheet = str(styleSheet, encoding='utf8')
            else:
                # Python v2.
                styleSheet = unicode(styleSheet, encoding='utf8')


            self.styleTextView.setPlainText(styleSheet)
            model = self.styleSheetCombo.model()
            item = QtGui.QStandardItem(os.path.basename(fileName))
            item.setData( fileName, role = QtCore.Qt.UserRole + 1)
            model.appendRow(item)
            self.styleSheetCombo.setCurrentIndex(self.styleSheetCombo.count()-1)

    @pyqtSlot()
    def on_saveButton_clicked(self):
        fileName, _ = QFileDialog.getSaveFileName(self)
        if fileName:
            self.saveStyleSheet(fileName)

    @pyqtSlot()
    def on_closeButton_clicked(self):
        self.close()

    @pyqtSlot()
    def on_clearButton_clicked(self):
        self.styleTextEdit.clear()

    @pyqtSlot()
    def on_copyButton_clicked(self):
        self.styleTextEdit.setPlainText(self.styleTextView.toPlainText())

    @pyqtSlot()
    def on_colorButton_clicked(self):
        _color = QColorDialog.getColor()
        if _color.isValid():
            Color = _color.name()
            self.colorButton.setStyleSheet('QPushButton {background-color: %s ;}'% Color)
            self.styleTextEdit.insertPlainText(Color)

    def loadStyleSheet(self, sheetName):
        if sheetName == 'None':
            self.styleTextView.setPlainText('')
            styleSheet = ''
            self.styleTextView.setPlainText(styleSheet)
            return
        if sheetName == 'As Loaded':
            styleSheet = self.origStyleSheet
        else:
            if PATH.IS_SCREEN:
                DIR = PATH.SCREENDIR
                BNAME = PATH.BASENAME
            else:
                DIR =PATH.PANELDIR
                BNAME = PATH.BASENAME
            qssname = os.path.join(DIR, BNAME, sheetName)
            file = QFile(qssname)
            file.open(QFile.ReadOnly)
            styleSheet = file.readAll()
            if sys.version_info.major > 2:
                # Python v3.
                styleSheet = str(styleSheet, encoding='utf8')
            else:
                styleSheet = str(styleSheet)
        self.styleTextView.setPlainText(styleSheet)

    def saveStyleSheet(self, fileName):
        styleSheet = self.styleTextEdit.toPlainText()
        file = QFile(fileName)
        if file.open(QFile.WriteOnly):
            QTextStream(file) << styleSheet
        else:
            QMessageBox.information(self, "Unable to open file",
                    file.errorString())
