#!/usr/bin/env python3
# QTVcp Widget
#
# Copyright (c) 2017 Chris Morley
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.



import os
import hal

from PyQt5.QtWidgets import (QMessageBox, QFileDialog, QDesktopWidget,
        QDialog, QDialogButtonBox, QVBoxLayout, QPushButton, QHBoxLayout,
        QHBoxLayout, QLineEdit, QPushButton, QDialogButtonBox, QTabWidget)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSlot, pyqtProperty, QEvent
from PyQt5 import uic

from qtvcp.widgets.widget_baseclass import _HalWidgetBase, hal
from qtvcp.widgets.origin_offsetview import OriginOffsetView as OFFVIEW_WIDGET
from qtvcp.widgets.tool_offsetview import ToolOffsetView as TOOLVIEW_WIDGET
from qtvcp.widgets.macro_widget import MacroTab
from qtvcp.widgets.versa_probe import VersaProbe
from qtvcp.widgets.entry_widget import SoftInputWidget
from qtvcp.widgets.virtualkeyboard import VirtualKeyboard
from qtvcp.widgets.calculator import Calculator
from qtvcp.widgets.machine_log import MachineLog
from qtvcp.lib.notify import Notify
from qtvcp.core import Status, Action, Info, Tool
from qtvcp import logger

# Instantiate the libraries with global reference
# STATUS gives us status messages from linuxcnc
# ACTION gives commands to linuxcnc
# INFO holds INI file details
# TOOL gives tool file access
# NOTICE is for the desktop notify system
# LOG is for running code logging
STATUS = Status()
ACTION = Action()
INFO = Info()
TOOL = Tool()
NOTICE = Notify()
LOG = logger.getLogger(__name__)

# Force the log level for this module
#LOG.setLevel(logger.DEBUG) # One of DEBUG, INFO, WARNING, ERROR, CRITICAL

    #########################################
    # geometry helper functions
    #########################################

    # This general function parses the geometry string and places
    # the dialog based on what it finds.
    # there are directive words allowed.
    # If there are no letters in the string, it will check the
    # preference file (if there is one) to see what the last position
    # was. If all else fails it uses it's natural Designer stated
    # geometry
class GeometryMixin(_HalWidgetBase):
    def __init__(self, ):
        super(GeometryMixin, self).__init__()
        self._geometry_string = 'default'

    def set_default_geometry(self):
        x = self.geometry().x()
        y = self.geometry().y()
        w = self.geometry().width()
        h = self.geometry().height()
        self._default_geometry=[x,y,w,h]
        return x,y,w,h

    def read_preference_geometry(self,name):
        self._geoName = name
        if self.PREFS_:
            self._geometry_string = self.PREFS_.getpref(name, self.get_default_geometry(), str, 'DIALOG_GEOMETRY')
        else:
            self._geometry_string = 'default'

    def get_default_geometry(self):
        a,b,c,d = self._default_geometry
        return '%s %s %s %s'% (a,b,c,d)

    def set_geometry(self):
        def go(x,y,w,h):
            self.setGeometry(x,y,w,h)
        try:
            if self._geometry_string.replace(' ','').isdigit():
                self._geometry_string = self.PREFS_.getpref(self._geoName, '', str, 'DIALOG_GEOMETRY')
            # If there is a preference file object use it to load the geometry
            if self._geometry_string in('default',''):
                x,y,w,h = self._default_geometry
                go(x,y,w,h)
            elif 'center' in self._geometry_string.lower():
                geom = self.frameGeometry()
                geom.moveCenter(QDesktopWidget().availableGeometry().center())
                self.setGeometry(geom)
                return
            elif 'bottomleft' in self._geometry_string.lower():
                # move to bottom left of parent
                ph = self.topParent.geometry().height()
                px = self.topParent.geometry().x()
                py = self.topParent.geometry().y()
                dw = self.geometry().width()
                dh = self.geometry().height()
                go(px, py+ph-dh, dw, dh)
            elif 'onwindow' in self._geometry_string.lower():
                # move relative to parent position
                px = self.topParent.geometry().x()
                py = self.topParent.geometry().y()
                # remove everything except digits and spaces
                temp =  [x for x in self._geometry_string if (x.isdigit() or x == ' ')]
                # remove lead and trailing spaces and then slit on spaces
                temp = temp.strip(' ').split(' ')
                go(px+int(temp[0]), py+int(temp[1]), int(temp[2]), int(temp[3]))
            else:
                temp = self._geometry_string.split(' ')
                go(int(temp[0]), int(temp[1]), int(temp[2]), int(temp[3]))
        except Exception as e:
            LOG.error('Calculating geometry of {} using natural placement.'.format(self.HAL_NAME_))
            LOG.debug('Dialog gometry python error: {}'.format(e))
            x = self.geometry().x()
            y = self.geometry().y()
            w = self.geometry().width()
            h = self.geometry().height()
            go( x,y,w,h)

    def record_geometry(self):
        if self.PREFS_ :
            temp = self._geometry_string.replace(' ','')
            temp = temp.strip('-')
            if temp =='' or temp.isdigit():
                LOG.debug('Saving {} data from widget {} to file.'.format( self._geoName,self.HAL_NAME_))
                x = self.geometry().x()
                y = self.geometry().y()
                w = self.geometry().width()
                h = self.geometry().height()
                geo = '%s %s %s %s'% (x,y,w,h)
                self.PREFS_.putpref(self._geoName, geo, str, 'DIALOG_GEOMETRY')

################################################################################
# Generic messagebox Dialog
################################################################################
class LcncDialog(QMessageBox, GeometryMixin):
    def __init__(self, parent=None):
        super(LcncDialog, self).__init__(parent)
        self.setTextFormat(Qt.RichText)
        self.setText('<b>Sample Text?</b>')
        self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        self.setIcon(QMessageBox.Critical)
        self.setDetailedText('')
        self.mtype = 'OK'
        self._possibleTypes = ('OK','YESNO','OKCANCEL','CLOSEPROMPT')
        self._state = False
        self._color = QColor(0, 0, 0, 150)
        self._request_name = 'MESSAGE'
        self._nblock = False
        self._massage = None
        self._title = 'Message Dialog'
        self.hide()

    def _hal_init(self):
        self.set_default_geometry()
        STATUS.connect('dialog-request', self._external_request)

    # this processes STATUS called dialog requests
    # We check the cmd to see if it was for us
    # then we check for a id string
    # if all good show the dialog
    # and then send back the dialog response via a general message
    def _external_request(self, w, message):
        self._message = message
        if message.get('NAME') == self._request_name:
            geo = message.get('GEONAME') or 'LncMessage-geometry'
            self.read_preference_geometry(geo)
            t = message.get('TITLE')
            if t:
                self._title = t

            mess = message.get('MESSAGE') or None
            more = message.get('MORE') or None
            details = message.get('DETAILS') or None
            mtype = message.get('TYPE')
            if mtype is None: mtype = 'OK'
            icon = message.get('ICON') or 'INFO'
            pin = message.get('PINNAME')
            ftext = message.get('FOCUSTEXT')
            fcolor = message.get('FOCUSCOLOR')
            alert = message.get('PLAYALERT')
            nblock = message.get('NONBLOCKING')
            rtrn = self.showdialog(mess, more, details, mtype, 
                                    icon, pin, ftext, fcolor, alert, nblock)
            if not nblock:
                message['RETURN'] = rtrn
                STATUS.emit('general', message)

    def showdialog(self, message, more_info=None, details=None, display_type='OK',
                   icon=QMessageBox.Information, pinname=None, focus_text=None,
                   focus_color=None, play_alert=None, nblock=False):

        self._nblock = nblock
        if nblock:
            self.setWindowModality(Qt.NonModal)
            self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog | Qt.WindowStaysOnTopHint
                            | Qt.WindowSystemMenuHint)
        else:
            self.setWindowModality(Qt.ApplicationModal)
            self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.FramelessWindowHint | Qt.Dialog |
                            Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)

        self.setWindowTitle(self._title)

        if focus_color is not None:
            color = focus_color
        else:
            color = self._color

        if icon == 'QUESTION': icon = QMessageBox.Question
        elif icon == 'INFO' or isinstance(icon,str): icon = QMessageBox.Information
        elif icon == 'WARNING': icon = QMessageBox.Warning
        elif icon == 'CRITICAL': icon = QMessageBox.Critical
        self.setIcon(icon)

        self.setText('<b>%s</b>' % message)

        if more_info is not None:
            self.setInformativeText(more_info)
        else:
            self.setInformativeText('')

        if details is not None:
            self.setDetailedText(details)
        else:
            self.setDetailedText('')

        display_type = display_type.upper()
        if display_type not in self._possibleTypes:
            display_type = 'OK'
        if display_type == 'OK':
            self.setStandardButtons(QMessageBox.Ok)
        elif display_type == 'YESNO':
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        elif display_type == 'OKCANCEL':
            self.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        self.buttonClicked.connect(self.msgbtn)
        if not nblock:
            STATUS.emit('focus-overlay-changed', True, focus_text, color)
        if play_alert:
            STATUS.emit('play-sound', play_alert)
        if not nblock:
            retval = self.exec_()
            STATUS.emit('focus-overlay-changed', False, None, None)
            LOG.debug('Value of pressed button: {}'.format(retval))
            return self.qualifiedReturn(retval)
        else:
            self.show()

    def qualifiedReturn(self, retval):
        if retval in(QMessageBox.No, QMessageBox.Cancel):
            return False
        elif retval in(QMessageBox.Ok, QMessageBox.Yes):
            return True
        else:
            return retval

    def showEvent(self, event):
        if self._nblock:
            self.set_geometry()
        else:
            geom = self.frameGeometry()
            geom.moveCenter(QDesktopWidget().availableGeometry().center())
            self.setGeometry(geom)
        super(LcncDialog, self).showEvent(event)

    def msgbtn(self, i):
        LOG.debug('Button pressed is: {}'.format(i.text()))
        if self._nblock:
            self.hide()
            btn = i.text().encode('utf-8')
            if btn in ('&OK','&Yes'):
                self._message['RETURN'] = True
            else:
                self._message['RETURN'] = False
            self.record_geometry()
            STATUS.emit('general', self._message)
            self._massage = None

    # **********************
    # Designer properties
    # **********************
    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'MESSAGE'

    overlay_color = pyqtProperty(QColor, getColor, setColor)
    state = pyqtProperty(bool, getState, setState, resetState)
    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)

################################################################################
# Close Dialog
################################################################################
class CloseDialog(LcncDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(CloseDialog, self).__init__(parent)
        self.shutdown = self.addButton('System\nShutdown',QMessageBox.DestructiveRole)
        self._request_name = 'CLOSEPROMPT'
        self._title = 'QtVCP'

################################################################################
# Tool Change Dialog
################################################################################
class ToolDialog(LcncDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(ToolDialog, self).__init__(parent)
        self.setText('<b>Manual Tool Change Request</b>')
        self.setInformativeText('Please Insert Tool 0')
        self.setStandardButtons(QMessageBox.Ok)
        self.useDesktopDialog = False
        self._curLine = 0
        self._actionbutton = self.addButton('Pause For Jogging', QMessageBox.ActionRole)
        self._actionbutton.setEnabled(False)

    # We want the tool change HAL pins the same as what's used in AXIS so it is
    # easier for users to connect to.
    # So we need to trick the HAL component into doing this for these pins,
    # but not any other Qt widgets.
    # So we record the original base name of the component, make our pins, then
    # switch it back
    def _hal_init(self):
        self.set_default_geometry()
        self.read_preference_geometry('ToolChangeDialog-geometry')
        #_HalWidgetBase._hal_init(self)

        if not hal.component_exists('hal_manualtoolchange'):
            oldname = self.HAL_GCOMP_.comp.getprefix()
            self.HAL_GCOMP_.comp.setprefix('hal_manualtoolchange')
            self.hal_pin = self.HAL_GCOMP_.newpin('change', hal.HAL_BIT, hal.HAL_IN)
            self.hal_pin.value_changed.connect(self.tool_change)
            self.tool_number = self.HAL_GCOMP_.newpin('number', hal.HAL_S32, hal.HAL_IN)
            self.changed = self.HAL_GCOMP_.newpin('changed', hal.HAL_BIT, hal.HAL_OUT)
            #self.hal_pin = self.HAL_GCOMP_.newpin(self.HAL_NAME_ + 'change_button', hal.HAL_BIT, hal.HAL_IN)
            self.HAL_GCOMP_.comp.setprefix(oldname)
        else:
            LOG.warning("""Detected hal_manualtoolchange component already loaded
   Qtvcp recommends to allow use of it's own component by not loading the original. 
   Qtvcp Integrated toolchange dialog will not show until then""")
        if self.PREFS_:
            self.play_sound = self.PREFS_.getpref('toolDialog_play_sound', True, bool, 'DIALOG_OPTIONS')
            self.speak = self.PREFS_.getpref('toolDialog_speak', True, bool, 'DIALOG_OPTIONS')
            self.sound_type = self.PREFS_.getpref('toolDialog_sound_type', 'READY', str, 'DIALOG_OPTIONS')
        else:
            self.play_sound = False

    def tool_change(self, change):
        if change:
            STATUS.stat.poll()
            self._curLine = STATUS.stat.motion_line
            MORE = 'Please Insert Tool %d' % self.tool_number.get()
            tool_table_line = TOOL.GET_TOOL_INFO(self.tool_number.get())
            comment = str(tool_table_line[TOOL.COMMENTS])
            MESS = 'Manual Tool Change Request'
            DETAILS = ' Tool Info: %s'% comment

            STATUS.emit('focus-overlay-changed', True, MESS, self._color)
            if self.PREFS_:
                if self.speak:
                    STATUS.emit('play-sound', 'speak %s' % MORE)
                if self.play_sound:
                    STATUS.emit('play-sound', self.sound_type)

                # desktop notify dialog
                if self.useDesktopDialog:
                    NOTICE.notify_ok(MESS, MORE, None, 0, self._pin_change)
                    return
            # Qt dialog
            if self._curLine > 0:
                self._actionbutton.setEnabled(True)
            else:
                self._actionbutton.setEnabled(False)
            answer = self.showdialog(MESS, MORE, DETAILS, display_type='OK')
            STATUS.emit('focus-overlay-changed', False, None, None)
            self._pin_change(answer)
        elif not change:
            self.changed.set(False)

    # This also is called from DesktopDialog
    def _pin_change(self,answer):
        if answer == True:
            self.changed.set(True)
        elif answer == 0:
            self.changed.set(True)
            ACTION.ABORT()
            STATUS.emit('update-machine-log', 'tool change Aorted with run from line', 'TIME')
            STATUS.emit('dialog-request', {'NAME': 'RUNFROMLINE',
                        'LINE':self._curLine+2, 'NONBLOCKING':True})
        else:
            ACTION.ABORT()
            STATUS.emit('update-machine-log', 'tool change Aorted', 'TIME')

    # **********************
    # Designer properties
    # **********************
    # inherited


################################################################################
# File Open Dialog
################################################################################
class FileDialog(QFileDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(FileDialog, self).__init__(parent)
        self._state = False
        self._load_request_name = 'LOAD'
        self._save_request_name = 'SAVE'
        self._color = QColor(0, 0, 0, 150)
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        self.setOptions(options)
        self.setWindowModality(Qt.ApplicationModal)
        self.INI_exts = INFO.get_qt_filter_extensions()
        self.setNameFilter(self.INI_exts)
        self.default_path = (os.path.join(os.path.expanduser('~'), 'linuxcnc/nc_files/examples'))

    def _hal_init(self):
        self.set_default_geometry()

        STATUS.connect('dialog-request', self._external_request)
        if self.PREFS_:
            self.play_sound = self.PREFS_.getpref('fileDialog_play_sound', True, bool, 'DIALOG_OPTIONS')
            self.sound_type = self.PREFS_.getpref('fileDialog_sound_type', 'READY', str, 'DIALOG_OPTIONS')
            last_path = self.PREFS_.getpref('last_loaded_directory', self.default_path, str, 'BOOK_KEEPING')
            self.setDirectory(last_path)
        else:
            self.play_sound = False

    def _external_request(self, w, message):
        name = message.get('NAME')
        if name in (self._load_request_name,self._save_request_name):
            ext = message.get('EXTENSIONS')
            pre = message.get('FILENAME')
            dir = message.get('DIRECTORY')
            if dir is None:
                dir = self.PREFS_.getpref('last_loaded_directory', self.default_path, str, 'BOOK_KEEPING')
            geo = message.get('GEONAME') or 'FileDialog-geometry'
            self.read_preference_geometry(geo)
            if name == self._load_request_name:
                # if there is an ID then a file name response is expected
                if message.get('ID'):
                    message['RETURN'] = self.load_dialog(ext, pre, dir, True)
                    STATUS.emit('general', message)
                else:
                    self.load_dialog(extensions = ext, preselect = pre, directory = dir,)
            else:
                if message.get('ID'):
                    message['RETURN'] = self.save_dialog(ext, pre, dir)
                    STATUS.emit('general', message)

    def showdialog(self):
        self.load_dialog()

    def load_dialog(self, extensions = None, preselect = None, directory = None, return_path=False):
        self.setFileMode(QFileDialog.ExistingFile)
        self.setAcceptMode(QFileDialog.AcceptOpen)
        if extensions:
            self.setNameFilter(extensions)
        else:
            self.setNameFilter(self.INI_exts)
        if preselect:
            self.selectFile(preselect)
        else:
            self.selectFile('')
        if directory:
            self.setDirectory(directory)
        else:
            self.setDirectory(self.default_path)
        self.setWindowTitle('Open')
        STATUS.emit('focus-overlay-changed', True, 'Open Gcode', self._color)
        if self.play_sound:
            STATUS.emit('play-sound', self.sound_type)
        self.set_geometry()
        fname = None
        if (self.exec_()):
            fname = self.selectedFiles()[0]
            path = self.directory().absolutePath()
            self.setDirectory(path)

        self.record_geometry()
        if fname and not return_path:
            if self.PREFS_:
                self.PREFS_.putpref('last_loaded_directory', path, str, 'BOOK_KEEPING')
                self.PREFS_.putpref('RecentPath_0', fname, str, 'BOOK_KEEPING')
            ACTION.OPEN_PROGRAM(fname)
            STATUS.emit('update-machine-log', 'Loaded: ' + fname, 'TIME')
            # overlay hides it's self after loading
        else:
            STATUS.emit('focus-overlay-changed', False, None, None)
        return fname

    def save_dialog(self, extensions = None, preselect = None, directory = None):
        self.setFileMode(QFileDialog.AnyFile)
        self.setAcceptMode(QFileDialog.AcceptSave)
        if extensions:
            self.setNameFilter(extensions)
        else:
            self.setNameFilter(self.INI_exts)
        if preselect:
            self.selectFile(preselect)
        else:
            self.selectFile('')
        if directory:
            self.setDirectory(directory)
        self.setWindowTitle('Save')
        STATUS.emit('focus-overlay-changed', True, 'Save Gcode', self._color)
        if self.play_sound:
            STATUS.emit('play-sound', self.sound_type)
        self.set_geometry()
        fname = None
        if (self.exec_()):
            fname = self.selectedFiles()[0]
            path = self.directory().absolutePath()
            self.setDirectory(path)
        else:
            fname = None
        STATUS.emit('focus-overlay-changed', False, None, None)
        self.record_geometry()
        if fname: 
            if self.PREFS_:
                self.PREFS_.putpref('last_saved_directory', path, str, 'BOOK_KEEPING')
                self.PREFS_.putpref('RecentSavedPath_0', fname, str, 'BOOK_KEEPING')
        return fname

    #**********************
    # Designer properties
    #**********************

    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    state = pyqtProperty(bool, getState, setState, resetState)
    overlay_color = pyqtProperty(QColor, getColor, setColor)

    def getLoadIdName(self):
        return self._load_request_name
    def setLoadIdName(self, name):
        self._load_request_name = name
    def resetLoadIdName(self):
        self._load_request_name = 'LOAD'

    def getSaveIdName(self):
        return self._save_request_name
    def setSaveIdName(self, name):
        self._save_request_name = name
    def resetSaveIdName(self):
        self._save_request_name = 'SAVE'

    launch_load_id = pyqtProperty(str, getLoadIdName, setLoadIdName, resetLoadIdName)
    launch_save_id = pyqtProperty(str, getSaveIdName, setSaveIdName, resetSaveIdName)

################################################################################
# origin Offset Dialog
################################################################################
class OriginOffsetDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(OriginOffsetDialog, self).__init__(parent)
        self._color = QColor(0, 0, 0, 150)
        self._state = False
        self._request_name = 'ORIGINOFFSET'

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog |
                            Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)
        self.setMinimumSize(200, 200)
        buttonBox = QDialogButtonBox()
        buttonBox.setEnabled(False)
        STATUS.connect('not-all-homed', lambda w, axis: buttonBox.setEnabled(False))
        STATUS.connect('all-homed', lambda w: buttonBox.setEnabled(True))
        STATUS.connect('state-estop', lambda w: buttonBox.setEnabled(False))
        STATUS.connect('state-estop-reset', lambda w: buttonBox.setEnabled(STATUS.machine_is_on()
                                                    and STATUS.is_all_homed()))
        STATUS.connect('interp-idle', lambda w: buttonBox.setEnabled(STATUS.machine_is_on()
                                                    and STATUS.is_all_homed()))
        STATUS.connect('interp-run', lambda w: buttonBox.setEnabled(False))
        for i in('X', 'Y', 'Z'):
            b = 'button_%s' % i
            self[b] = QPushButton('Zero %s' % i)
            self[b].clicked.connect(self.zeroPress('%s' % i))
            buttonBox.addButton(self[b], 3)

        v = QVBoxLayout()
        h = QHBoxLayout()
        self._o = OFFVIEW_WIDGET()
        self._o.setObjectName('__dialogOffsetViewWidget')
        self.setLayout(v)
        v.addWidget(self._o)
        b = QPushButton('OK')
        b.clicked.connect(lambda: self.close())
        h.addWidget(b)
        h.addWidget(buttonBox)
        v.addLayout(h)
        self.setModal(True)

    def _hal_init(self):
        self._o.hal_init()
        self.set_default_geometry()
        STATUS.connect('dialog-request', self._external_request)

    def _external_request(self, w, message):
        if message['NAME'] == self._request_name:
            geo = message.get('GEONAME') or 'OriginOffsetDialog-geometry'
            self.read_preference_geometry(geo)
            self.load_dialog()

    # This weird code is just so we can get the axis
    # letter
    # using clicked.connect() apparently can't easily
    # add user data
    def zeroPress(self, data):
        def calluser():
            self.zeroAxis(data)
        return calluser

    def zeroAxis(self, index):
        ACTION.SET_AXIS_ORIGIN(index, 0)

    def load_dialog(self):
        STATUS.emit('focus-overlay-changed', True, 'Set Origin Offsets', self._color)
        self.set_geometry()
        self.show()
        self.exec_()
        STATUS.emit('focus-overlay-changed', False, None, None)
        self.record_geometry()

    def closing_cleanup__(self):
        self._o.closing_cleanup__()

    # usual boiler code
    # (used so we can use code such as self[SomeDataName]
    def __getitem__(self, item):
        return getattr(self, item)
    def __setitem__(self, item, value):
        return setattr(self, item, value)

    # **********************
    # Designer properties
    # **********************

    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'ORIGINOFFSET'

    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    state = pyqtProperty(bool, getState, setState, resetState)
    overlay_color = pyqtProperty(QColor, getColor, setColor)


################################################################################
# Tool Offset Dialog
################################################################################
class ToolOffsetDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(ToolOffsetDialog, self).__init__(parent)
        self._color = QColor(0, 0, 0, 150)
        self._state = False
        self._request_name = 'TOOLOFFSET'

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog |
                            Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)
        self.setMinimumSize(200, 200)

        self._o = TOOLVIEW_WIDGET()
        self._o.setObjectName('__dialogToolViewWidget')
        self._o._hal_init()

        buttonBox = QDialogButtonBox()
        buttonBox.setEnabled(False)
        STATUS.connect('not-all-homed', lambda w, axis: buttonBox.setEnabled(False))
        STATUS.connect('all-homed', lambda w: buttonBox.setEnabled(True))
        STATUS.connect('state-estop', lambda w: buttonBox.setEnabled(False))
        STATUS.connect('state-estop-reset', lambda w: buttonBox.setEnabled(STATUS.machine_is_on()
                                                    and STATUS.is_all_homed()))
        STATUS.connect('interp-idle', lambda w: buttonBox.setEnabled(STATUS.machine_is_on()
                                                    and STATUS.is_all_homed()))
        STATUS.connect('interp-run', lambda w: buttonBox.setEnabled(False))
        self.addtool = QPushButton('Add Tool')
        self.addtool.clicked.connect(lambda: self.addTool())
        buttonBox.addButton(self.addtool, 3)
        self.deletetool = QPushButton('Delete Tool')
        self.deletetool.clicked.connect(lambda: self.deleteTool())
        buttonBox.addButton(self.deletetool, 3)
        #for i in('X', 'Y', 'Z'):
        #    b = 'button_%s' % i
        #    self[b] = QPushButton('Zero %s' % i)
        #    self[b].clicked.connect(self.zeroPress('%s' % i))
        #    buttonBox.addButton(self[b], 3)

        v = QVBoxLayout()
        h = QHBoxLayout()
        self.setLayout(v)
        v.addWidget(self._o)
        b = QPushButton('OK')
        b.clicked.connect(lambda: self.close())
        h.addWidget(b)
        h.addWidget(buttonBox)
        v.addLayout(h)
        self.setModal(True)

    def _hal_init(self):
        self.set_default_geometry()
        STATUS.connect('dialog-request', self._external_request)

    def _external_request(self, w, message):
        if message['NAME'] == self._request_name:
            geo = message.get('GEONAME') or 'ToolOffsetDialog-geometry'
            self.read_preference_geometry(geo)
            self.load_dialog()

    def addTool(self):
        self._o.add_tool()

    def deleteTool(self):
        self._o.delete_tools()

    # This weird code is just so we can get the axis
    # letter
    # using clicked.connect() apparently can't easily
    # add user data
    def zeroPress(self, data):
        def calluser():
            self.zeroAxis(data)
        return calluser

    def zeroAxis(self, index):
        ACTION.SET_AXIS_ORIGIN(index, 0)

    def load_dialog(self):
        STATUS.emit('focus-overlay-changed', True, 'Set Tool Offsets', self._color)
        self.set_geometry()
        self.show()
        self.exec_()
        STATUS.emit('focus-overlay-changed', False, None, None)
        self.record_geometry()

    # usual boiler code
    # (used so we can use code such as self[SomeDataName]
    def __getitem__(self, item):
        return getattr(self, item)
    def __setitem__(self, item, value):
        return setattr(self, item, value)

    # **********************
    # Designer properties
    # **********************

    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'TOOLOFFSET'

    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    state = pyqtProperty(bool, getState, setState, resetState)
    overlay_color = pyqtProperty(QColor, getColor, setColor)


################################################################################
# CamView Dialog
################################################################################
class CamViewDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(CamViewDialog, self).__init__(parent)
        from qtvcp.widgets.camview_widget import CamView
        self._color = QColor(0, 0, 0, 150)
        self._state = False
        self._request_name = 'CAMVIEW'

        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog |
                            Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)
        self.setMinimumSize(200, 200)
        h = QHBoxLayout()
        h.addStretch(1)
        self.b = QPushButton('Close')
        self.b.clicked.connect(lambda: self.close())
        h.addWidget(self.b)
        l = QVBoxLayout()
        self.camV = CamView()
        self.setLayout(l)
        l.addWidget(self.camV)
        l.addLayout(h)

    def _hal_init(self):
        self.camV.hal_init(HAL_NAME='')
        self.set_default_geometry()
        STATUS.connect('dialog-request', self._external_request)

    def _external_request(self, w, message):
        if message['NAME'] == self._request_name:
            geo = message.get('GEONAME') or 'CamViewOffsetDialog-geometry'
            self.read_preference_geometry(geo)
            nblock = message.get('NONBLOCKING')
            if nblock:
                self.setWindowModality(Qt.NonModal)
                self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog | Qt.WindowStaysOnTopHint
                            | Qt.WindowSystemMenuHint)
                self.load_dialog_nonblocking()
            else:
                self.setWindowModality(Qt.ApplicationModal)
                self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.FramelessWindowHint | Qt.Dialog |
                            Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)
                self.load_dialog()

    def close(self):
        self.record_geometry()
        super(CamViewDialog, self).close()

    def load_dialog_nonblocking(self):
        self.set_geometry()
        self.show()

    def load_dialog(self):
        STATUS.emit('focus-overlay-changed', True, 'Cam View Dialog', self._color)
        self.set_geometry()
        self.show()
        self.exec_()
        STATUS.emit('focus-overlay-changed', False, None, None)

    # **********************
    # Designer properties
    # **********************

    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'CAMVIEW'

    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    state = pyqtProperty(bool, getState, setState, resetState)
    overlay_color = pyqtProperty(QColor, getColor, setColor)


################################################################################
# MacroTab Dialog
################################################################################
class MacroTabDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(MacroTabDialog, self).__init__(parent)
        self.setWindowTitle('Qtvcp Macro Menu')
        self._color = QColor(0, 0, 0, 150)
        self._state = False
        self._request_name = 'MACROTAB'
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog |
                            Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)
        self.setMinimumSize(00, 200)
        self.resize(600, 400)
        # patch class to call our button methods rather then the
        # original methods (Gotta do before instantiation)
        MacroTab.closeChecked = self._close
        MacroTab.runChecked = self._run
        MacroTab.setTitle = self._setTitle
        # ok now instantiate patched class
        self.tab = MacroTab()
        self.tab.setObjectName('macroTabInternal_')
        l = QVBoxLayout()
        self.setLayout(l)
        l.addWidget(self.tab)
        #we need the close button
        self.tab.closeButton.setVisible(True)

    def _hal_init(self):
        self.set_default_geometry()
        # gotta call this since we instantiated this out of qtvcp's knowledge
        self.tab._hal_init()

        STATUS.connect('dialog-request', self._external_request)

    def _external_request(self, w, message):
        if message['NAME'] == self._request_name:
            geo = message.get('GEONAME') or 'MacroTabDialog-geometry'
            self.read_preference_geometry(geo)
            self.load_dialog()

    # This method is called instead of MacroTab's closeChecked method
    # we do this so we can use it's buttons to hide our dialog
    # rather then close the MacroTab widget
    def _close(self):
        self.close()

    # This method is called instead of MacroTab's runChecked() method
    # we do this so we can use it's buttons to hide our dialog
    # rather then close the MacroTab widget
    def _run(self):
        self.tab.runMacro()
        self.close()

    def _setTitle(self, string):
        self.setWindowTitle(string)

    def load_dialog(self):
        STATUS.emit('focus-overlay-changed', True, 'Lathe Macro Dialog', self._color)
        self.tab.stack.setCurrentIndex(0)
        self.set_geometry()
        self.show()
        self.exec_()
        STATUS.emit('focus-overlay-changed', False, None, None)
        self.record_geometry()

    # **********************
    # Designer properties
    # **********************

    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'MACROTAB'

    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    state = pyqtProperty(bool, getState, setState, resetState)
    overlay_color = pyqtProperty(QColor, getColor, setColor)

################################################################################
# Versaprobe Dialog
################################################################################
class VersaProbeDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(VersaProbeDialog, self).__init__(parent)
        self._color = QColor(0, 0, 0, 150)
        self._state = False
        self._request_name  = 'VERSAPROBE'
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog |
                            Qt.WindowStaysOnTopHint | Qt.WindowSystemMenuHint)
        self.setMinimumSize(200, 200)
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        b = buttonBox.button(QDialogButtonBox.Ok)
        b.clicked.connect(lambda: self.close())
        l = QVBoxLayout()
        self._o = VersaProbe()
        self.setLayout(l)
        l.addWidget(self._o)
        l.addWidget(buttonBox)

    def _hal_init(self):
        self._o.hal_init()
        self.set_default_geometry()
        STATUS.connect('dialog-request', self._external_request)

    def closing_cleanup__(self):
        self._o.closing_cleanup__()

    def _external_request(self, w, message):
        if message['NAME'] == self._request_name:
            geo = message.get('GEONAME') or 'VersaProbeDialog-geometry'
            self.read_preference_geometry(geo)
            self.load_dialog()

    def showdialog(self):
        self.load_dialog()

    def load_dialog(self):
        STATUS.emit('focus-overlay-changed', True, 'VersaProbe Dialog', self._color)
        self.set_geometry()
        self.show()
        self.exec_()
        STATUS.emit('focus-overlay-changed', False, None, None)
        self.record_geometry()

    # **********************
    # Designer properties
    # **********************

    @pyqtSlot(bool)
    def setState(self, value):
        self._state = value
        if value:
            self.show()
        else:
            self.hide()
    def getState(self):
        return self._state
    def resetState(self):
        self._state = False

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'VERSAPROBE'

    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    state = pyqtProperty(bool, getState, setState, resetState)
    overlay_color = pyqtProperty(QColor, getColor, setColor)

############################################
# Entry Dialog
############################################
class EntryDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(EntryDialog, self).__init__(parent)
        self._color = QColor(0, 0, 0, 150)
        self.play_sound = False
        self._request_name = 'ENTRY'
        self._title = 'Numerical Entry'
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog | Qt.WindowStaysOnTopHint |
                            Qt.WindowSystemMenuHint)
        self._softKey = SoftInputWidget(self, 'numeric')

        self.Num = QLineEdit()
        self.Num.installEventFilter(self)
        self.Num.keyboard_type = 'numeric'
        # actiate touch input
        self.Num.keyboard_enable = True

        self.Num.returnPressed.connect(lambda: self.accept())


        gl = QVBoxLayout()
        gl.addWidget(self.Num)

        self.bBox = QDialogButtonBox()
        self.bBox.addButton('Apply', QDialogButtonBox.AcceptRole)
        self.bBox.addButton('Cancel', QDialogButtonBox.RejectRole)
        self.bBox.rejected.connect(self.reject)
        self.bBox.accepted.connect(self.accept)

        gl.addWidget(self.bBox)
        self.setLayout(gl)

    def _hal_init(self):
        self.set_default_geometry()
        if self.PREFS_:
            self.play_sound = self.PREFS_.getpref('EntryDialog_play_sound', True, bool, 'DIALOG_OPTIONS')
            self.sound_type = self.PREFS_.getpref('EntryDialog_sound_type', 'READY', str, 'DIALOG_OPTIONS')
        else:
            self.play_sound = False
        STATUS.connect('dialog-request', self._external_request)

    def eventFilter(self, widget, event):
        if self.Num.focusWidget() == widget and event.type() == QEvent.MouseButtonPress:
            if self.Num.keyboard_enable:
                self._softKey.show_input_panel(widget)
        return False

    # this processes STATUS called dialog requests
    # We check the cmd to see if it was for us
    # then we check for a id string
    # if all good show the dialog
    # and then send back the dialog response via a general message
    def _external_request(self, w, message):
        if message.get('NAME') == self._request_name:
            geo = message.get('GEONAME') or 'EntryDialog-geometry'
            self.read_preference_geometry(geo)
            t = message.get('TITLE')
            if t:
                self._title = t
            else:
                self._title = 'Numerical Entry'
            overlay = message.get('OVERLAY')
            if overlay is None :
                overlay = True
            preload = message.get('PRELOAD')
            num = self.showdialog(preload=preload, overlay=overlay)
            message['RETURN'] = num
            STATUS.emit('general', message)

    def showdialog(self, preload=None,overlay=True):
        conversion = {'x':0, 'y':1, "z":2, 'a':3, "b":4, "c":5, 'u':6, 'v':7, 'w':8}
        if overlay:
            STATUS.emit('focus-overlay-changed', True, '', self._color)
        self.setWindowTitle(self._title);
        if self.play_sound:
            STATUS.emit('play-sound', self.sound_type)
        self.set_geometry()
        if preload is not None:
            self.Num.setText(str(preload))
        flag = False
        while flag == False:
            self.Num.setFocus()
            retval = self.exec_()
            if retval:
                try:
                    answer = float(self.Num.text())
                    flag = True
                except Exception as e:
                    try:
                        p,relp,dtg = STATUS.get_position()
                        otext = text = self.Num.text().lower()
                        for let in INFO.AVAILABLE_AXES:
                            let = let.lower()
                            if let in text:
                                Pos = relp[conversion[let]]
                                text = text.replace('%s'%let,'%s'%Pos)
                        process = eval(text)
                        answer = float(process)
                        STATUS.emit('update-machine-log', 'Convert Entry from: {} to {}'.format(otext,text), 'TIME')
                        flag = True
                    except Exception as e:
                        self.setWindowTitle('%s'%e)
            else:
                flag = True
                answer = None
        if overlay:
            STATUS.emit('focus-overlay-changed', False, None, None)
        self.record_geometry()
        LOG.debug('Value of pressed button: {}'.format(retval))
        if answer is None:
            return None
        return answer

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'ENTRY'

    def set_soft_keyboard(self, data):
        self.Num.keyboard_enable = data
    def get_soft_keyboard(self):
        return self.Num.keyboard_enable
    def reset_soft_keyboard(self):
        self.Num.keyboard_enable = True

    # designer will show these properties in this order:
    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    overlay_color = pyqtProperty(QColor, getColor, setColor)
    soft_keyboard_option = pyqtProperty(bool, get_soft_keyboard, set_soft_keyboard, reset_soft_keyboard)

############################################
# Keyboard Dialog
############################################
class KeyboardDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(KeyboardDialog, self).__init__(parent)
        self._color = QColor(0, 0, 0, 150)
        self.play_sound = False
        self._request_name = 'KEYBOARD'
        self._title = 'Keyboard Entry'
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog | Qt.WindowStaysOnTopHint |
                            Qt.WindowSystemMenuHint)
        self.keybrd = VirtualKeyboard()
        self.edit = QLineEdit()

        gl = QVBoxLayout()
        gl.addWidget(self.edit)
        gl.addWidget(self.keybrd)

        self.bBox = QDialogButtonBox()
        self.bBox.addButton('Apply', QDialogButtonBox.AcceptRole)
        self.bBox.addButton('Cancel', QDialogButtonBox.RejectRole)
        self.bBox.rejected.connect(self.reject)
        self.bBox.accepted.connect(self.accept)

        gl.addWidget(self.bBox)
        self.setLayout(gl)

    def _hal_init(self):
        self.set_default_geometry()
        if self.PREFS_:
            self.play_sound = self.PREFS_.getpref('KeyboardDialog_play_sound', True, bool, 'DIALOG_OPTIONS')
            self.sound_type = self.PREFS_.getpref('KeyboardDialog_sound_type', 'READY', str, 'DIALOG_OPTIONS')
        else:
            self.play_sound = False
        STATUS.connect('dialog-request', self._external_request)

    # this processes STATUS called dialog requests
    # We check the cmd to see if it was for us
    # then we check for a id string
    # if all good show the dialog
    # and then send back the dialog response via a general message
    def _external_request(self, w, message):
        if message.get('NAME') == self._request_name:
            geo = message.get('GEONAME') or 'KeyboardDialog-geometry'
            self.read_preference_geometry(geo)
            t = message.get('TITLE')
            if t:
                self._title = t
            else:
                self._title = 'Keyboard Entry'
            preload = message.get('PRELOAD')
            overlay = message.get('OVERLAY')
            if overlay is None :
                overlay = True
            text = self.showdialog(preload)
            message['RETURN'] = text
            STATUS.emit('general', message)

    def showdialog(self, preload=None, overlay=True):
        if overlay:
            STATUS.emit('focus-overlay-changed', True, '', self._color)
        self.setWindowTitle(self._title);
        if self.play_sound:
            STATUS.emit('play-sound', self.sound_type)
        self.set_geometry()
        self.edit.setFocus()
        if preload is not None:
            self.edit.setFocus()
            self.edit.setText(str(preload))
            self.edit.deselect()
        retval = self.exec_()
        answer = self.edit.text()
        if retval:   
            STATUS.emit('update-machine-log', 'keyboard Entry {}'.format(answer), 'TIME')
        else:
            answer = None

        if overlay:
            STATUS.emit('focus-overlay-changed', False, None, None)
        self.record_geometry()
        LOG.debug('Value of pressed button: {}'.format(retval))
        if answer is None:
            return None
        return answer

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'ENTRY'

    def set_soft_keyboard(self, data):
        self.Num.keyboard_enable = data
    def get_soft_keyboard(self):
        return self.Num.keyboard_enable
    def reset_soft_keyboard(self):
        self.Num.keyboard_enable = True

    # designer will show these properties in this order:
    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    overlay_color = pyqtProperty(QColor, getColor, setColor)
    soft_keyboard_option = pyqtProperty(bool, get_soft_keyboard, set_soft_keyboard, reset_soft_keyboard)


############################################
# Calculator Dialog
############################################
class CalculatorDialog(Calculator, GeometryMixin):
    def __init__(self, parent=None):
        super(CalculatorDialog, self).__init__(parent)
        self._color = QColor(0, 0, 0, 150)
        self.play_sound = False
        self._request_name = 'CALCULATOR'
        self._title = 'Calculator Entry'
        self._nblock = False
        self._message = None
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog | Qt.WindowStaysOnTopHint |
                            Qt.WindowSystemMenuHint)

    def _hal_init(self):
        self.set_default_geometry()
        if self.PREFS_:
            self.play_sound = self.PREFS_.getpref('CalculatorDialog_play_sound', True, bool, 'DIALOG_OPTIONS')
            self.sound_type = self.PREFS_.getpref('CalculatorDialog_sound_type', 'READY', str, 'DIALOG_OPTIONS')
        else:
            self.play_sound = False
        STATUS.connect('dialog-request', self._external_request)

    # this processes STATUS called dialog requests
    # We check the cmd to see if it was for us
    # then we check for a id string
    # if all good show the dialog
    # and then send back the dialog response via a general message
    def _external_request(self, w, message):
        self._message = message
        if message.get('NAME') == self._request_name:
            geo = message.get('GEONAME') or 'CalculatorDialog-geometry'
            self.read_preference_geometry(geo)
            t = message.get('TITLE')
            if t:
                self._title = t
            else:
                self._title = 'Calculator Entry'
            preload = message.get('PRELOAD')
            axis = message.get('AXIS')
            if axis in ('X','Y','Z','A','B','C','U','V','W'):
                self.axisTriggered(axis)
            self._nblock = message.get('NONBLOCKING')
            overlay = message.get('OVERLAY')
            if overlay is None:
                overlay = True
            num = self.showdialog(preload=preload, overlay=overlay)
            message['RETURN'] = num
            STATUS.emit('general', message)

    def showdialog(self, preload=None, overlay=True):
        self.setWindowTitle(self._title);
        if self.play_sound:
            STATUS.emit('play-sound', self.sound_type)
        self.set_geometry()
        if preload is not None:
            self.display.setText(str(preload))
        if self._nblock:
            self.show()
        else:
            if overlay:
                STATUS.emit('focus-overlay-changed', True, '', self._color)
            retval = self.exec_()
            if overlay:
                STATUS.emit('focus-overlay-changed', False, None, None)

    def accept(self):
        self.record_geometry()
        super(CalculatorDialog, self).accept()
        try:
            num =  float(self.display.text())
            LOG.debug('Displayed value when accepted: {}'.format(num))
            if self._message is not None:
                self._message['RETURN'] = num
                STATUS.emit('general', self._message)
                self._message = None
        except Exception as e:
                print(e)

    def reject(self):
        self.record_geometry()
        super(CalculatorDialog, self).reject()

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'CALCULATOR'

    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    overlay_color = pyqtProperty(QColor, getColor, setColor)

############################################
# machine Log Dialog
############################################
class MachineLogDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(MachineLogDialog, self).__init__(parent)
        self._color = QColor(0, 0, 0, 150)
        self.play_sound = False
        self._request_name = 'MACHINELOG'
        self._title = 'Machine Log'
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog | Qt.WindowStaysOnTopHint |
                            Qt.WindowSystemMenuHint)


    def _hal_init(self):
        self.buildWidget()
        self.set_default_geometry()
        if self.PREFS_:
            self.play_sound = self.PREFS_.getpref('MachineLogDialog_play_sound', True, bool, 'DIALOG_OPTIONS')
            self.sound_type = self.PREFS_.getpref('MachineLogDialog_sound_type', 'READY', str, 'DIALOG_OPTIONS')
        else:
            self.play_sound = False
        STATUS.connect('dialog-request', self._external_request)

    def buildWidget(self):
        # add a vertical layout to dialog
        l = QVBoxLayout()
        self.setLayout(l)

        # build tab widget
        tabs = QTabWidget()
        # build tabs
        tab_mlog = MachineLog()
        tab_mlog._hal_init()
        tab_ilog = MachineLog()
        tab_ilog.set_integrator_log(True)
        tab_ilog._hal_init()
        # add tabs to tab widget
        tabs.addTab(tab_mlog,'Machine Log')
        tabs.addTab(tab_ilog,'Integrator Log')
        # add tab to layout
        l.addWidget(tabs)

        # build dialog buttons
        self.bBox = QDialogButtonBox()
        self.bBox.addButton('Ok', QDialogButtonBox.AcceptRole)
        self.bBox.accepted.connect(self.accept)
        # add buttons to layout
        l.addWidget(self.bBox)


    # this processes STATUS called dialog requests
    # We check the cmd to see if it was for us
    # then we check for a id string
    # if all good show the dialog
    # and then send back the dialog response via a general message
    def _external_request(self, w, message):
        if message.get('NAME') == self._request_name:
            geo = message.get('GEONAME') or 'MachineLogDialog-geometry'
            self.read_preference_geometry(geo)
            t = message.get('TITLE')
            if t:
                self._title = t
            else:
                self._title = 'Machine Log'
            nonblock = message.get('NONBLOCKING')
            num = self.showdialog(nonblock)
            message['RETURN'] = num
            STATUS.emit('general', message)

    def showdialog(self, nonblock=None):
        if nonblock is not None:
            STATUS.emit('focus-overlay-changed', True, 'Machine Log', self._color)
        self.setWindowTitle(self._title);
        if self.play_sound:
            STATUS.emit('play-sound', self.sound_type)
        self.set_geometry()
        if nonblock is not None:
            self.exec_()
            STATUS.emit('focus-overlay-changed', False, None, None)
            self.record_geometry()
            return False
        else:
            self.show()

    def getColor(self):
        return self._color
    def setColor(self, value):
        self._color = value
    def resetState(self):
        self._color = QColor(0, 0, 0, 150)

    def getIdName(self):
        return self._request_name
    def setIdName(self, name):
        self._request_name = name
    def resetIdName(self):
        self._request_name = 'MACHINELOG'

    # designer will show these properties in this order:
    launch_id = pyqtProperty(str, getIdName, setIdName, resetIdName)
    overlay_color = pyqtProperty(QColor, getColor, setColor)

############################################
# Run from line prestart Dialog
############################################

class RunFromLineDialog(QDialog, GeometryMixin):
    def __init__(self, parent=None):
        super(RunFromLineDialog, self).__init__(parent)
        # Load the widgets UI file:
        self.filename = os.path.join(INFO.LIB_PATH,'widgets_ui', 'runFromLine_dialog.ui')
        try:
            self.instance = uic.loadUi(self.filename, self)
        except AttributeError as e:
            LOG.critical(e)
        self.start_line = None
        self._color = QColor(0, 0, 0, 150)
        self.play_sound = False
        self._request_name = 'RUNFROMLINE'
        self._title = 'Run from line preset Dialog'
        self.setWindowFlags(self.windowFlags() | Qt.Tool |
                            Qt.Dialog | Qt.WindowStaysOnTopHint |
                            Qt.WindowSystemMenuHint)
        self.buttonBox.clicked.connect(self.Clicked)

    def _hal_init(self):
        self.set_default_geometry()
        if self.PREFS_:
            self.play_sound = self.PREFS_.getpref('RunFromLineDialog_play_sound', True, bool, 'DIALOG_OPTIONS')
            self.sound_type = self.PREFS_.getpref('RunFromLineDialog_sound_type', 'READY', str, 'DIALOG_OPTIONS')
        else:
            self.play_sound = False
        STATUS.connect('dialog-request', self._external_request)

        def homed_on_test():
            return (STATUS.machine_is_on() 
                    and (STATUS.is_all_homed() or INFO.NO_HOME_REQUIRED))

        STATUS.connect('state-off', lambda w: self.setEnabled(False))
        STATUS.connect('state-estop', lambda w: self.setEnabled(False))
        STATUS.connect('interp-idle', lambda w: self.setEnabled(homed_on_test()))
        STATUS.connect('all-homed', lambda w: self.setEnabled(homed_on_test()))

    # this processes STATUS called dialog requests
    # We check the cmd to see if it was for us
    # then we check for a id string
    # if all good show the dialog
    # and then send back the dialog response via a general message
    def _external_request(self, w, message):
        if message.get('NAME') == self._request_name:
            geo = message.get('GEONAME') or 'RunFromLineDialog-geometry'
            self.read_preference_geometry(geo)
            l = message.get('LINE')
            t = message.get('TITLE')
            if t:
                self._title = t
            else:
                self._title = 'Run From Line: {}'.format(l)
            nblock = message.get('NONBLOCKING')
            mess = message.get('MESSAGE')
            num = self.showdialog(line = l, message=mess, nonblock = nblock)
            message['RETURN'] = num
            STATUS.emit('general', message)

    def showdialog(self, line = 1, message=None, nonblock=None):
        self.start_line = int(line)
        if message is not None:
            self.label_line.setText(message)
        if not nonblock:
            STATUS.emit('focus-overlay-changed', True, 'Machine Log', self._color)
        self.setWindowTitle(self._title);
        if self.play_sound:
            STATUS.emit('play-sound', self.sound_type)
        self.set_geometry()
        if not nonblock:
            self.exec_()
            STATUS.emit('focus-overlay-changed', False, None, None)
            self.record_geometry()
            return False
        else:
            self.show()

    # accept button applies presets and if line number given starts linuxcnc
    def accept(self):
        self.preset()
        if self.start_line:
            ACTION.RUN(self.start_line)
        super(RunFromLineDialog, self).accept()

    #apply button only applies presets
    def Clicked(self, button):
        if self.buttonBox.buttonRole(button) == QDialogButtonBox.ApplyRole:
            self.preset()

    # preset spindle before running
    def preset(self):
        if self.radioButton_cw.isChecked():
            direction = 'M3'
        else:
            direction = 'M4'
        speed  = self.spinBox_rpm.value()
        ACTION.CALL_MDI('s{} {}'.format(speed,direction))

################################
# for testing without editor:
################################
def main():
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    widget = KeyboardDialog()
    #widget = CalculatorDialog()
    #widget = RunFromLineDialog()
    #widget = MachineLogDialog()
    #widget = EntryDialog()
    #widget = CamViewDialog()
    #widget = VersaProbeDialog()
    #widget = MacroTabDialog()
    #widget = CamViewDialog()
    #widget = ToolOffsetDialog()
    #widget = OriginOffsetDialog()
    #widget = FileDialog()
    #widget = ToolDialog()

    widget.HAL_NAME_ = 'test'
    widget.PREFS_ = None
    widget._hal_init()
    t = widget.showdialog()
    print (t)
    sys.exit()
if __name__ == '__main__':
    main()
