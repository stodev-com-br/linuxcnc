'''
conv_settings.py

Copyright (C) 2020  Phillip A Carter

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import * 
from PyQt5.QtWidgets import * 
from PyQt5.QtGui import * 

def save(P, W):
    P.preAmble = W.preEntry.text()
    P.postAmble = W.pstEntry.text()
    P.origin = W.center.isChecked()
    P.leadIn = float(W.liEntry.text())
    P.leadOut = float(W.loEntry.text())
    P.holeDiameter = float(W.hdEntry.text())
    P.holeSpeed = int(W.hsEntry.text())
    P.gridSize = float(W.gsEntry.text())
    W.PREFS_.putpref('Preamble', P.preAmble, str, 'CONVERSATIONAL')
    W.PREFS_.putpref('Postamble', P.postAmble, str, 'CONVERSATIONAL')
    W.PREFS_.putpref('Origin', int(P.origin), int, 'CONVERSATIONAL')
    W.PREFS_.putpref('Leadin', P.leadIn, float, 'CONVERSATIONAL')
    W.PREFS_.putpref('Leadout', P.leadOut, float, 'CONVERSATIONAL')
    W.PREFS_.putpref('Hole diameter', P.holeDiameter, float, 'CONVERSATIONAL')
    W.PREFS_.putpref('Hole speed', P.holeSpeed, int, 'CONVERSATIONAL')
    W.PREFS_.putpref('Grid Size', P.gridSize, float, 'CONVERSATIONAL')
    show(P, W)
    W[P.oldConvButton].click()

#def reload(parent, ambles, unitCode):
def reload(P, W):
    load(P, W)
    show(P, W)
    W[P.oldConvButton].click()

def load(P, W):
    P.preAmble = W.PREFS_.getpref('Preamble', P.ambles, str, 'CONVERSATIONAL')
    P.postAmble = W.PREFS_.getpref('Postamble', P.ambles, str, 'CONVERSATIONAL')
    P.origin = bool(W.PREFS_.getpref('Origin', False, int, 'CONVERSATIONAL'))
    P.leadIn = W.PREFS_.getpref('Leadin', 0, float, 'CONVERSATIONAL')
    P.leadOut = W.PREFS_.getpref('Leadout', 0, float, 'CONVERSATIONAL')
    P.holeDiameter = W.PREFS_.getpref('Hole diameter', P.unitCode[2], float, 'CONVERSATIONAL')
    P.holeSpeed = W.PREFS_.getpref('Hole speed', 60, int, 'CONVERSATIONAL')
    P.gridSize = W.PREFS_.getpref('Grid Size', 0, float, 'CONVERSATIONAL')

def show(P, W):
    W.preEntry.setText(P.preAmble)
    W.pstEntry.setText(P.postAmble)
    W.liEntry.setText('{}'.format(P.leadIn))
    W.loEntry.setText('{}'.format(P.leadOut))
    W.hdEntry.setText('{}'.format(P.holeDiameter))
    W.hsEntry.setText('{}'.format(P.holeSpeed))
    W.gsEntry.setText('{}'.format(P.gridSize))
    if P.origin:
        W.center.setChecked(True)
    else:
        W.btLeft.setChecked(True)
    P.oSaved = P.origin
    if P.gridSize:
        # grid size is in inches
        W.conv_preview.grid_size = P.gridSize / P.unitsPerMm / 25.4
        W.conv_preview.set_current_view()

def widgets(P, W):
    W.preLabel = QLabel('Preamble')
    W.preLabel.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    W.entries.addWidget(W.preLabel, 0, 0)
    W.preEntry = QLineEdit()
    W.entries.addWidget(W.preEntry, 0, 1, 1, 4)
    W.pstLabel = QLabel('Postamble')
    W.entries.addWidget(W.pstLabel, 1, 0)
    W.pstEntry = QLineEdit()
    W.entries.addWidget(W.pstEntry, 1, 1, 1, 4)
    W.oLabel = QLabel('ORIGIN')
    W.entries.addWidget(W.oLabel, 2, 1, 1, 3)
    W.center = QRadioButton('     Centre')
    W.entries.addWidget(W.center, 3, 1)
    W.btLeft = QRadioButton('Bottom Left')
    W.entries.addWidget(W.btLeft, 3, 3)
    W.llLabel = QLabel('LEAD LENGTHS')
    W.entries.addWidget(W.llLabel, 4, 1, 1, 3)
    W.liLabel = QLabel('Lead In')
    W.entries.addWidget(W.liLabel, 5, 0)
    W.liEntry = QLineEdit()
    W.liEntry.textChanged.connect(lambda:P.conv_entry_changed(W.sender()))
    W.entries.addWidget(W.liEntry, 5, 1)
    W.loEntry = QLineEdit()
    W.loEntry.textChanged.connect(lambda:P.conv_entry_changed(W.sender()))
    W.entries.addWidget(W.loEntry, 5, 3)
    W.loLabel = QLabel('Lead Out')
    W.entries.addWidget(W.loLabel, 5, 4)
    W.shLabel = QLabel('SMALL HOLES')
    W.entries.addWidget(W.shLabel, 6, 1, 1, 3)
    W.hdLabel = QLabel('Diameter')
    W.entries.addWidget(W.hdLabel, 7, 0)
    W.hdEntry = QLineEdit()
    W.hdEntry.textChanged.connect(lambda:P.conv_entry_changed(W.sender()))
    W.entries.addWidget(W.hdEntry, 7, 1)
    W.hsEntry = QLineEdit()
    W.hsEntry.textChanged.connect(lambda:P.conv_entry_changed(W.sender()))
    W.entries.addWidget(W.hsEntry, 7, 3)
    W.hsLabel = QLabel('Speed %')
    W.entries.addWidget(W.hsLabel, 7, 4)
    W.pvLabel = QLabel('PREVIEW')
    W.entries.addWidget(W.pvLabel, 8, 1, 1, 3)
    W.gsLabel = QLabel('Grid Size')
    W.entries.addWidget(W.gsLabel, 9, 0)
    W.gsEntry = QLineEdit()
    W.gsEntry.textChanged.connect(lambda:P.conv_entry_changed(W.sender()))
    W.entries.addWidget(W.gsEntry, 9, 1)
    W.save = QPushButton('SAVE')
    W.save.pressed.connect(lambda:save(P, W))
    W.entries.addWidget(W.save, 12, 1)
    W.reload = QPushButton('RELOAD')
    W.reload.pressed.connect(lambda:reload(P, W))
    W.entries.addWidget(W.reload, 12, 3)
    for blank in range(2):
        W['{}'.format(blank)] = QLabel('')
        W.entries.addWidget(W['{}'.format(blank)], 10 + blank, 0)
    ra = ['preLabel', 'pstLabel', 'liLabel', 'liEntry', 'loEntry', \
          'hdLabel', 'hdEntry', 'hsEntry', 'gsLabel', 'gsEntry']
    la = ['loLabel', 'hsLabel']
    ca = ['oLabel', 'llLabel', 'shLabel', 'pvLabel']
    rb = ['center', 'btLeft']
    bt = ['save', 'reload']
    for w in ra:
        W[w].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        W[w].setFixedWidth(80)
        W[w].setFixedHeight(24)
    for w in la:
        W[w].setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        W[w].setFixedWidth(80)
        W[w].setFixedHeight(24)
    for w in ca:
        W[w].setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        W[w].setFixedWidth(240)
        W[w].setFixedHeight(24)
    for w in rb:
        W[w].setFixedWidth(80)
        W[w].setFixedHeight(24)
    for w in bt:
        W[w].setFixedWidth(80)
        W[w].setFixedHeight(24)
    W.preEntry.setFocus()
