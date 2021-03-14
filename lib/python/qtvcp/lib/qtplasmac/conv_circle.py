'''
conv_circle.py

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

import math
from PyQt5.QtCore import Qt 
from PyQt5.QtWidgets import QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QMessageBox
from PyQt5.QtGui import QPixmap 

def preview(P, W):
    if P.dialogError: return
    if W.dEntry.text():
        radius = float(W.dEntry.text()) / 2
    else:
        radius = 0
    if radius > 0:
        angle = math.radians(45)
        ijOffset = radius * math.sin(angle)
        ijDiff = 0
        if W.kOffset.isChecked():
            if W.cExt.isChecked():
                ijDiff = float(W.kerf_width.text()) / 2 * math.sin(angle)
            else:
                ijDiff = float(W.kerf_width.text()) / 2 * -math.sin(angle)

        if W.liEntry.text():
            leadInOffset = math.sin(angle) * float(W.liEntry.text())
        else:
            leadInOffset = 0
        if W.loEntry.text():
            leadOutOffset = math.sin(math.radians(45)) * float(W.loEntry.text())
        else:
            leadOutOffset = 0
        kOffset = float(W.kerf_width.text()) * W.kOffset.isChecked() / 2
        if not W.xsEntry.text():
            W.xsEntry.setText('{:0.3f}'.format(P.xOrigin))
        if W.center.isChecked():
            xC = float(W.xsEntry.text())
        else:
            if W.cExt.isChecked():
                xC = float(W.xsEntry.text()) + radius + kOffset
            else:
                xC = float(W.xsEntry.text()) + radius - kOffset
        if not W.ysEntry.text():
            W.ysEntry.setText('{:0.3f}'.format(P.yOrigin))
        if W.center.isChecked():
            yC = float(W.ysEntry.text())
        else:
            if W.cExt.isChecked():
                yC = float(W.ysEntry.text()) + radius + kOffset
            else:
                yC = float(W.ysEntry.text()) + radius - kOffset
        xS = xC - ijOffset - ijDiff
        yS = yC - ijOffset - ijDiff
        right = math.radians(0)
        up = math.radians(90)
        left = math.radians(180)
        down = math.radians(270)
        if W.cExt.isChecked():
            dir = [left, down]
        else:
            dir = [right, up]
        if radius <= P.holeDiameter / 2:
            sHole = True
            if leadInOffset > radius:
                leadInOffset = radius
        else:
            sHole = False
        outTmp = open(P.fTmp, 'w')
        outNgc = open(P.fNgc, 'w')
        inWiz = open(P.fNgcBkp, 'r')
        for line in inWiz:
            if '(new conversational file)' in line:
                outNgc.write('\n{} (preamble)\n'.format(P.preAmble))
                break
            elif '(postamble)' in line:
                break
            elif 'm2' in line.lower() or 'm30' in line.lower():
                break
            outNgc.write(line)
        outTmp.write('\n(conversational circle)\n')
        outTmp.write('M190 P{}\n'.format(int(W.conv_material.currentText().split(':')[0])))
        outTmp.write('M66 P3 L3 Q1\n')
        outTmp.write('f#<_hal[plasmac.cut-feed-rate]>\n')
        if leadInOffset > 0:
            if sHole and not W.cExt.isChecked():
                xlStart = xS + leadInOffset * math.cos(angle)
                ylStart = yS + leadInOffset * math.sin(angle)
            else:
                xlcenter = xS + (leadInOffset * math.cos(angle + dir[0]))
                ylcenter = yS + (leadInOffset * math.sin(angle + dir[0]))
                xlStart = xlcenter + (leadInOffset * math.cos(angle + dir[1]))
                ylStart = ylcenter + (leadInOffset * math.sin(angle + dir[1]))
            outTmp.write('g0 x{:.6f} y{:.6f}\n'.format(xlStart, ylStart))
            outTmp.write('m3 $0 s1\n')
            if sHole:
                outTmp.write('M67 E3 Q{} (reduce feed rate to 60%)\n'.format(P.holeSpeed))
            if sHole and not W.cExt.isChecked():
                outTmp.write('g1 x{:.6f} y{:.6f}\n'.format(xS, yS))
            else:
                outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xS, yS, xlcenter - xlStart, ylcenter - ylStart))
        else:
            outTmp.write('g0 x{:.6f} y{:.6f}\n'.format(xS, yS))
            outTmp.write('m3 $0 s1\n')
            if sHole:
                outTmp.write('M67 E3 Q{} (reduce feed rate to 60%)\n'.format(P.holeSpeed))
        if W.cExt.isChecked():
            outTmp.write('g2 x{0:.6f} y{1:.6f} i{2:.6f} j{2:.6f}\n'.format(xS, yS, ijOffset + ijDiff))
        else:
            outTmp.write('g3 x{0:.6f} y{1:.6f} i{2:.6f} j{2:.6f}\n'.format(xS, yS, ijOffset + ijDiff))
        if leadOutOffset and not W.overcut.isChecked() and not (not W.cExt.isChecked() and sHole):
                if W.cExt.isChecked():
                    dir = [left, up]
                else:
                    dir = [right, down]
                xlcenter = xS + (leadOutOffset * math.cos(angle + dir[0]))
                ylcenter = yS + (leadOutOffset * math.sin(angle + dir[0]))
                xlEnd = xlcenter + (leadOutOffset * math.cos(angle + dir[1]))
                ylEnd = ylcenter + (leadOutOffset * math.sin(angle + dir[1]))
                outTmp.write('g3 x{:.6f} y{:.6f} i{:.6f} j{:.6f}\n'.format(xlEnd, ylEnd, xlcenter - xS, ylcenter - yS))
        torch = True
        if W.overcut.isChecked() and sHole and not W.cExt.isChecked():
            Torch = False
            outTmp.write('m62 p3 (disable torch)\n')
            over_cut(P, W, xS, yS, ijOffset + ijDiff, radius, outTmp)
        outTmp.write('m5 $0\n')
        if sHole:
            outTmp.write('M68 E3 Q0 (reset feed rate to 100%)\n')
        if not torch:
            torch = True
            outTmp.write('m65 p3 (enable torch)\n')
        outTmp.close()
        outTmp = open(P.fTmp, 'r')
        for line in outTmp:
            outNgc.write(line)
        outTmp.close()
        outNgc.write('\n{} (postamble)\n'.format(P.postAmble))
        outNgc.write('m2\n')
        outNgc.close()
        W.conv_preview.load(P.fNgc)
        W.conv_preview.set_current_view()
        W.add.setEnabled(True)
        W.undo.setEnabled(True)
    else:
        P.dialogError = True
        P.dialog_error(QMessageBox.Warning, 'CIRCLE', 'Diameter is required')

def over_cut(P, W, lastX, lastY, IJ, radius, outTmp):
    try:
        oclength = float(W.ocEntry.text())
    except:
        oclength = 0
    centerX = lastX + IJ
    centerY = lastY + IJ
    cosA = math.cos(oclength / radius)
    sinA = math.sin(oclength / radius)
    cosB = ((lastX - centerX) / radius)
    sinB = ((lastY - centerY) / radius)
    #clockwise arc
    if W.cExt.isChecked():
        endX = centerX + radius * ((cosB * cosA) + (sinB * sinA))
        endY = centerY + radius * ((sinB * cosA) - (cosB * sinA))
        dir = '2'
    #counterclockwise arc
    else:
        endX = centerX + radius * ((cosB * cosA) - (sinB * sinA))
        endY = centerY + radius * ((sinB * cosA) + (cosB * sinA))
        dir = '3'
    outTmp.write('g{0} x{1:.6f} y{2:.6f} i{3:.6f} j{3:.6f}\n'.format(dir, endX, endY, IJ))

def cut_type_toggled(P, W):
    if W.cExt.isChecked():
        W.overcut.setChecked(False)
        W.overcut.setEnabled(False)
        W.ocEntry.setEnabled(False)
    else:
        try:
            dia = float(W.dEntry.text())
        except:
            dia = 0
        if dia <= P.holeDiameter:
            W.overcut.setEnabled(True)
            W.ocEntry.setEnabled(True)
    auto_preview(P, W)

def overcut_toggled(P, W):
    if W.overcut.isChecked():
        try:
            lolen = float(W.loEntry.text())
        except:
            lolen = 0
        try:
            dia = float(W.dEntry.text())
        except:
            dia = 0
        if (W.cExt.isChecked() and lolen) or not dia or dia > P.holeDiameter:
            W.overcut.setChecked(False)
    auto_preview(P, W)    

def entry_changed(P, W, widget):
    P.conv_entry_changed(widget)
    try:
        dia = float(W.dEntry.text())
    except:
        dia = 0
    if dia >= P.holeDiameter:
        W.overcut.setChecked(False)
        W.overcut.setEnabled(False)
        W.ocEntry.setEnabled(False)
    else:
        if not W.cExt.isChecked():
            W.overcut.setEnabled(True)
            W.ocEntry.setEnabled(True)

def auto_preview(P, W):
    if W.main_tab_widget.currentIndex() == 1 and \
       W.dEntry.text() and float(W.dEntry.text()) > 0:
        preview(P, W) 

def add_shape_to_file(P, W):
    P.conv_add_shape_to_file()

def undo_pressed(P, W):
    P.conv_undo_shape()

def widgets(P, W):
    #widgets
    W.ctLabel = QLabel('CUT TYPE')
    W.ctGroup = QButtonGroup(W)
    W.cExt = QRadioButton('EXTERNAL')
    W.cExt.setChecked(True)
    W.ctGroup.addButton(W.cExt)
    W.cInt = QRadioButton('INTERNAL')
    W.ctGroup.addButton(W.cInt)
    W.koLabel = QLabel('Offset')
    W.kOffset = QPushButton('KERF WIDTH')
    W.kOffset.setCheckable(True)
    W.spLabel = QLabel('START')
    W.spGroup = QButtonGroup(W)
    W.center = QRadioButton(' CENTER')
    W.spGroup.addButton(W.center)
    W.bLeft = QRadioButton('BTM LEFT')
    W.spGroup.addButton(W.bLeft)
    W.xsLabel = QLabel('X ORIGIN')
    W.xsEntry = QLineEdit(objectName = 'xsEntry')
    W.ysLabel = QLabel('Y ORIGIN')
    W.ysEntry = QLineEdit(objectName = 'ysEntry')
    W.liLabel = QLabel('LEAD IN')
    W.liEntry = QLineEdit(objectName = 'liEntry')
    W.loLabel = QLabel('LEAD OUT')
    W.loEntry = QLineEdit(objectName = 'loEntry')
    W.dLabel = QLabel('DIAMETER')
    W.dEntry = QLineEdit(objectName = '')
    W.overcut = QPushButton('OVER CUT')
    W.overcut.setEnabled(False)
    W.overcut.setCheckable(True)
    W.ocLabel = QLabel('OC LENGTH')
    W.ocEntry = QLineEdit(objectName = 'ocEntry')
    W.ocEntry.setEnabled(False)
    W.ocEntry.setText('{}'.format(4 * P.unitsPerMm))
    W.preview = QPushButton('PREVIEW')
    W.add = QPushButton('ADD')
    W.undo = QPushButton('UNDO')
    W.lDesc = QLabel('CREATING CIRCLE')
    W.iLabel = QLabel()
    pixmap = QPixmap('{}conv_circle_l.png'.format(P.IMAGES)).scaledToWidth(196)
    W.iLabel.setPixmap(pixmap)
    #alignment and size
    rightAlign = ['ctLabel', 'koLabel', 'spLabel', 'xsLabel', 'xsEntry', 'ysLabel', \
                  'ysEntry', 'liLabel', 'liEntry', 'loLabel', 'loEntry', 'dLabel', \
                  'dEntry', 'ocLabel', 'ocEntry']
    centerAlign = ['lDesc']
    rButton = ['cExt', 'cInt', 'center', 'bLeft']
    pButton = ['preview', 'add', 'undo', 'kOffset', 'overcut']
    for widget in rightAlign:
        W[widget].setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        W[widget].setFixedWidth(80)
        W[widget].setFixedHeight(24)
    for widget in centerAlign:
        W[widget].setAlignment(Qt.AlignCenter | Qt.AlignBottom)
        W[widget].setFixedWidth(240)
        W[widget].setFixedHeight(24)
    for widget in rButton:
        W[widget].setFixedWidth(80)
        W[widget].setFixedHeight(24)
    for widget in pButton:
        W[widget].setFixedWidth(80)
        W[widget].setFixedHeight(24)
    #starting parameters
    W.add.setEnabled(False)
    W.undo.setEnabled(False)
    if P.oSaved:
        W.center.setChecked(True)
    else:
        W.bLeft.setChecked(True)
    W.liEntry.setText('{}'.format(P.leadIn))
    W.loEntry.setText('{}'.format(P.leadOut))
    W.xsEntry.setText('{}'.format(P.xSaved))
    W.ysEntry.setText('{}'.format(P.ySaved))
    P.conv_undo_shape()
    #connections
    W.conv_material.currentTextChanged.connect(lambda:auto_preview(P, W))
    W.cExt.toggled.connect(lambda:cut_type_toggled(P, W))
    W.kOffset.toggled.connect(lambda:auto_preview(P, W))
    W.center.toggled.connect(lambda:auto_preview(P, W))
    W.overcut.toggled.connect(lambda:overcut_toggled(P, W))
    W.preview.pressed.connect(lambda:preview(P, W))
    W.add.pressed.connect(lambda:add_shape_to_file(P, W))
    W.undo.pressed.connect(lambda:undo_pressed(P, W))
    entries = ['xsEntry', 'ysEntry', 'liEntry', 'loEntry', 'dEntry', 'ocEntry']
    for entry in entries:
        W[entry].textChanged.connect(lambda:entry_changed(P, W, W.sender()))
        W[entry].editingFinished.connect(lambda:auto_preview(P, W))
    #add to layout
    if P.landscape:
        W.entries.addWidget(W.ctLabel, 0, 0)
        W.entries.addWidget(W.cExt, 0, 1)
        W.entries.addWidget(W.cInt, 0, 2)
        W.entries.addWidget(W.koLabel, 0, 3)
        W.entries.addWidget(W.kOffset, 0, 4)
        W.entries.addWidget(W.spLabel, 1, 0)
        W.entries.addWidget(W.center, 1, 1)
        W.entries.addWidget(W.bLeft, 1, 2)
        W.entries.addWidget(W.xsLabel, 2, 0)
        W.entries.addWidget(W.xsEntry, 2, 1)
        W.entries.addWidget(W.ysLabel, 3, 0)
        W.entries.addWidget(W.ysEntry, 3, 1)
        W.entries.addWidget(W.liLabel, 4, 0)
        W.entries.addWidget(W.liEntry, 4, 1)
        W.entries.addWidget(W.loLabel, 5, 0)
        W.entries.addWidget(W.loEntry, 5, 1)
        W.entries.addWidget(W.dLabel, 6, 0)
        W.entries.addWidget(W.dEntry, 6, 1)
        W.entries.addWidget(W.overcut, 7, 1)
        W.entries.addWidget(W.ocLabel, 8, 0)
        W.entries.addWidget(W.ocEntry, 8, 1)
        for r in range(9, 12):
            W['s{}'.format(r)] = QLabel('')
            W['s{}'.format(r)].setFixedHeight(24)
            W.entries.addWidget(W['s{}'.format(r)], r, 0)
        W.entries.addWidget(W.preview, 12, 0)
        W.entries.addWidget(W.add, 12, 2)
        W.entries.addWidget(W.undo, 12, 4)
        W.entries.addWidget(W.lDesc, 13 , 1, 1, 3)
        W.entries.addWidget(W.iLabel, 2 , 2, 7, 3)
    else:
        W.entries.addWidget(W.conv_material, 0, 0, 1, 5)
        W.entries.addWidget(W.ctLabel, 1, 0)
        W.entries.addWidget(W.cExt, 1, 1)
        W.entries.addWidget(W.cInt, 1, 2)
        W.entries.addWidget(W.koLabel, 1, 3)
        W.entries.addWidget(W.kOffset, 1, 4)
        W.entries.addWidget(W.spLabel, 2, 0)
        W.entries.addWidget(W.center, 2, 1)
        W.entries.addWidget(W.bLeft, 2, 2)
        W.entries.addWidget(W.xsLabel, 3, 0)
        W.entries.addWidget(W.xsEntry, 3, 1)
        W.entries.addWidget(W.ysLabel, 3, 2)
        W.entries.addWidget(W.ysEntry, 3, 3)
        W.entries.addWidget(W.liLabel, 4, 0)
        W.entries.addWidget(W.liEntry, 4, 1)
        W.entries.addWidget(W.loLabel, 4, 2)
        W.entries.addWidget(W.loEntry, 4, 3)
        W.entries.addWidget(W.dLabel, 5, 0)
        W.entries.addWidget(W.dEntry, 5, 1)
        W.entries.addWidget(W.overcut, 6, 1)
        W.entries.addWidget(W.ocLabel, 6, 2)
        W.entries.addWidget(W.ocEntry, 6, 3)
        for r in range(6, 9):
            W['s{}'.format(r)] = QLabel('')
            W['s{}'.format(r)].setFixedHeight(24)
            W.entries.addWidget(W['s{}'.format(r)], r, 0)
        W.entries.addWidget(W.preview, 9, 0)
        W.entries.addWidget(W.add, 9, 2)
        W.entries.addWidget(W.undo, 9, 4)
        W.entries.addWidget(W.lDesc, 10 , 1, 1, 3)
        W.entries.addWidget(W.iLabel, 0 , 5, 7, 3)
    W.dEntry.setFocus()
