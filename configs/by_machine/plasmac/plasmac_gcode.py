#!/usr/bin/env python2

'''
plasmac_gcode.py

Copyright (C) 2019, 2020  Phillip A Carter

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import os
import sys
import linuxcnc
import math
import gtk
import shutil
import time
import hal
from subprocess import Popen, PIPE

ini = linuxcnc.ini(os.environ['INI_FILE_NAME'])
cmd = linuxcnc.command()
inCode = sys.argv[1]
materialFile = ini.find('EMC', 'MACHINE').lower() + '_material.cfg'
tmpMmaterialFile = ini.find('EMC', 'MACHINE').lower() + '_material.tmp'
runFile = materialFile.replace('material','run')
cutType = int(Popen('halcmd getp plasmac_run.cut-type', stdout = PIPE, shell = True).communicate()[0])
currentMat = int(Popen('halcmd getp plasmac_run.material-change-number', stdout = PIPE, shell = True).communicate()[0])
metric = ['mm', 4]
imperial = ['in', 6]
units, precision = imperial if ini.find('TRAJ', 'LINEAR_UNITS').lower() == 'inch' else metric
if units == 'mm':
    minDiameter = 32
    ocLength = 4
else:
    minDiameter = 1.26
    ocLength = 0.157
newMaterial = []
line = ''
rapidLine = ''
lastX = 0
lastY = 0
lineNum = 0
holeVelocity = 60
material = [0, False]
codeError = False
codeWarn = False
overCut = False
holeActive = False
holeEnable = False
arcEnable = False
customDia = False
customLen = False
torchEnable = True
pierceOnly = False
scribing = False
spotting = False
offsetG41 = False
feedWarning = False

# error dialog
def dialog_error(mode, title, error):
    md = gtk.MessageDialog(None,
                           gtk.DIALOG_DESTROY_WITH_PARENT,
                           mode,
                           gtk.BUTTONS_CLOSE,
                           error)
    md.set_position(gtk.WIN_POS_CENTER_ALWAYS)
    md.set_keep_above(True)
    md.set_title(title)
    md.run()
    md.destroy()

# set hole type
def set_hole_type():
    global holeType, holeEnable, overCut, arcEnable, lineNum
    holeType = line.split('=')[1][0]
    if holeType == '1':
        holeEnable = True
        overCut = False
        arcEnable = False
        print('(velocity reduction for small holes)')
    elif holeType == '2':
        holeEnable = overCut = True
        arcEnable = False
        print('(velocity reduction for small holes)')
        lineNum += 1
        print('(overcut for small holes)')
    elif holeType == '3':
        holeEnable = arcEnable = True
        overCut = False
        print('(velocity reduction for small holes and arcs)')
    elif holeType == '4':
        holeEnable = arcEnable = overCut = True
        print('(velocity reduction for small holes and arcs)')
        lineNum += 1
        print('(overcut for small holes)')
    else:
        holeEnable = arcEnable = overCut = False
        print('(disable small hole sensing)')

# check if arc is a hole
def check_if_hole():
    global lastX, lastY, minDiameter, lineNum
    endX = get_position('x') if 'x' in line else lastX
    endY = get_position('y') if 'y' in line else lastY
    I = J = isHole = 0
    if 'i' in line: I = get_position('i')
    if 'j' in line: J = get_position('j')
    if lastX == endX and lastY == endY:
        isHole = True
    radius = get_hole_radius(I, J, isHole)
    print(line)
    if isHole and overCut and radius <= (minDiameter / 2):
        overburn(I, J, radius)
        return
    else:
        lastX = endX
        lastY = endY

# get hole radius and set velocity percentage
def get_hole_radius(I, J, isHole):
    global holeActive, lineNum
    if offsetG41:
        radius = math.sqrt((I ** 2) + (J ** 2))
    else:
        #radius = math.sqrt((I ** 2) + (J ** 2)) + (materialDict[material[0]][1] / 2)
        radius = math.sqrt((I ** 2) + (J ** 2))
    # velocity reduction required
    if radius <= (minDiameter / 2) and (isHole or arcEnable):
        if offsetG41:
            lineNum += 1
            codeWarn = True
            print(';m67 e3 q0 (inactive due to g41)')
            wng  = '\nCannot reduce velocity\n'
            wng += 'with cutter compensation active.\n'
            wng += '\nWarning for line #{}\n'.format(lineNum)
            dialog_error(gtk.MESSAGE_WARNING,'WARNING', wng)
        elif not holeActive:
            lineNum += 1
            print('m67 e3 q{0} (diameter:{1:0.3f}, velocity:{0}%)'.format(holeVelocity, radius * 2))
            holeActive = True
        if line.startswith('g2') and isHole:
            codeWarn = True
            wng = '\nThis cut appears to be a hole.\n'
            wng += 'Did you mean to cut clockwise?\n'
            wng += '\nWarning for line {}\n'.format(lineNum)
            dialog_error(gtk.MESSAGE_WARNING,'WARNING', wng)
    # no velocity reduction required
    else:
        if holeActive:
            lineNum += 1
            print('m67 e3 q0 (arc complete, velocity 100%)')
            holeActive = False
    return radius

# turn torch off and move 4mm (0.157) past hole end
def overburn(I, J, radius):
    global lastX, lastY, torchEnable, ocLength, lineNum
    centerX = lastX + I
    centerY = lastY + J
    cosA = math.cos(ocLength / radius)
    sinA = math.sin(ocLength / radius)
    cosB = ((lastX - centerX) / radius)
    sinB = ((lastY - centerY) / radius)
    lineNum += 1
    if offsetG41:
        codeWarn = True
        print(';m62 p3 (inactive due to g41)')
        wng  = '\nCannot enable/disable torch\n'
        wng += 'with cutter compensation active.\n'
        wng += '\nWarning for line #{}\n'.format(lineNum)
        dialog_error(gtk.MESSAGE_WARNING,'WARNING', wng)
    else:
        print('m62 p3 (disable torch)')
        torchEnable = False
    #clockwise arc
    if line.startswith('g2'):
        endX = centerX + radius * ((cosB * cosA) + (sinB * sinA))
        endY = centerY + radius * ((sinB * cosA) - (cosB * sinA))
        dir = '2'
    #counterclockwise arc
    else:
        endX = centerX + radius * ((cosB * cosA) - (sinB * sinA))
        endY = centerY + radius * ((sinB * cosA) + (cosB * sinA))
        dir = '3'
    lineNum += 1
    print('g{0} x{1:0.{5}f} y{2:0.{5}f} i{3:0.{5}f} j{4:0.{5}f}'.format(dir, endX, endY, I, J, precision))
    lastX = endX
    lastY = endY

# get axis position
def get_position(axis):
    tmp1 = line.split(axis)[1].replace(' ','')
    if not tmp1[0].isdigit() and not tmp1[0] == '.' and not tmp1[0] == '-':
        return None
    n = 0
    tmp2 = ''
    while 1:
        if tmp1[n].isdigit() or tmp1[n] == '.' or tmp1[n] == '-':
            tmp2 += tmp1[n]
            n += 1
        else:
            break
        if n >= len(tmp1):
            break
    return float(tmp2)

# set the last X and Y positions
def set_last_position(Xpos, Ypos):
    if line[0] in ['g','x','y']:
        if 'x' in line:
            if get_position('x') is not None:
                Xpos = get_position('x')
        if 'y' in line:
            if get_position('y') is not None:
                Ypos = get_position('y')
    return Xpos, Ypos

# comment out all Z commands
def comment_out_z_commands():
    global holeActive
    newline = ''
    newz = ''
    removing = 0
    comment = 0
    for bit in line:
        if comment:
            if bit == ')':
                comment = 0
            newline += bit
        elif removing:
            if bit in '0123456789.- ':
                newz += bit
            else:
                removing = 0
                if newz:
                    newz = newz.rstrip()
                newline += bit
        elif bit == '(':
            comment = 1
            newline += bit
        elif bit == 'z':
            removing = 1
            newz += '(' + bit
        else:
            newline += bit
    if holeActive:
        lineNum += 1
        print('m67 e3 q0 (arc complete, velocity 100%)')
        holeActive = False
    return '{} {})'.format(newline, newz)

# check if math used or explicit values
def check_math(axis):
    global codeError
    tmp1 = line.split(axis)[1]
    if tmp1.startswith('[') or tmp1.startswith('#'):
        codeError = True
        wng  = '\nPlasmaC GCode parser\n'
        wng += 'requires explicit values.\n'
        wng += '\nError near line #{}\n'.format(lineNum)
        wng += '\nDisable hole sensing\n'
        wng += 'or edit GCode file to suit.\n'
        dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)

# do material change
def do_material_change():
    if '(' in line:
        c = line.split('(', 1)[0]
    elif ';' in line:
        c = line.split(';', 1)[0]
    else:
        c = line
    a, b = c.split('p', 1)
    m = ''
    # get the material number
    for mNum in b.strip():
        if mNum in '0123456789':
            m += mNum
    material[0] = int(m)
    material[1] = True
    if material[0] not in materialDict:
        codeError = True
        wng  = '\nMaterial {} is missing from:\n'.format(material[0])
        wng += '{}\n'.format(materialFile)
        wng += '\nError near line #{}\n'.format(lineNum)
        wng += '\nAdd a new material\n'
        wng += 'or edit GCode file to suit.'
        dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)
        print(line)
        quit()
    Popen('halcmd setp plasmac_run.material-change-number {}'.format(material[0]), stdout = PIPE, shell = True)
    print(line)

# check if matarial edit required
def check_material_edit():
    newMaterial = []
    th = 0
    kw = jh = jd = ca = cv = pe = gp = cm = 0.0
    # try:
    if 'ph=' in line and 'pd=' in line and 'ch=' in line and 'fr=' in line:
        if '(o=0' in line:
            nu = 0
            na = 'Temporary'
            newMaterial.append(0)
        elif '(o=1' in line and 'nu=' in line and 'na=' in line:
            newMaterial.append(1)
        elif '(o=2' in line and 'nu=' in line and 'na=' in line:
            newMaterial.append(2)
        if newMaterial[0] in [0, 1, 2]:
            for item in line.split('(')[1].split(')')[0].split(','):
                # mandatory items
                if 'nu=' in item:
                    nu = int(item.split('=')[1])
                elif 'na=' in item:
                    na = item.split('=')[1].strip()
                elif 'ph=' in item:
                    ph = float(item.split('=')[1])
                elif 'pd=' in item:
                    pd = float(item.split('=')[1])
                elif 'ch=' in item:
                    ch = float(item.split('=')[1])
                elif 'fr=' in item:
                    fr = float(item.split('=')[1])
                # optional items
                elif 'kw=' in item:
                    kw = float(item.split('=')[1])
                elif 'th=' in item:
                    th = int(item.split('=')[1])
                elif 'jh=' in item:
                    jh = float(item.split('=')[1])
                elif 'jd=' in item:
                    jd = float(item.split('=')[1])
                elif 'ca=' in item:
                    ca = float(item.split('=')[1])
                elif 'cv=' in item:
                    cv = float(item.split('=')[1])
                elif 'pe=' in item:
                    pe = float(item.split('=')[1])
                elif 'gp=' in item:
                    gp = float(item.split('=')[1])
                elif 'cm=' in item:
                    cm = float(item.split('=')[1])
            for i in [nu,na,kw,th,ph,pd,jh,jd,ch,fr,ca,cv,pe,gp,cm]:
                newMaterial.append(i)
            if newMaterial[0] == 0:
                write_temp_default_material(newMaterial)
            elif nu in materialDict and newMaterial[0] == 1:
                wng  = '\nCannot add new Material #{}\n'.format(nu)
                wng += '\nMaterial number is in use\n'
                dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)
            else:
                rewrite_material_file(newMaterial)
        else:
            codeError = True
            wng  = '\nCannot add or edit material from G-Code file.\n'
            wng += '\nInvalid parameter or value in:'
            wng += '{}\n'.format(line)
            wng += 'This material will not be processed'
            dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)
    # except:
    #     codeError = True
    #     wng  = '\nCannot add or edit material from G-Code file.\n'
    #     wng += '\nInvalid/missing parameter or value in:\n\n'
    #     wng += '{}\n'.format(line)
    #     wng += 'This material will not be processed'
    #     dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)

# write temporary materials file
def write_temp_default_material(data):
    with open(tmpMmaterialFile, 'w') as fWrite:
        fWrite.write('#plasmac temp default material file, format is:\n')
        fWrite.write('#name = value\n\n')
        fWrite.write('kerf-width={}\n'.format(data[3]))
        fWrite.write('thc-enable={}\n'.format(data[4]))
        fWrite.write('pierce-height={}\n'.format(data[5]))
        fWrite.write('pierce-delay={}\n'.format(data[6]))
        fWrite.write('puddle-jump-height={}\n'.format(data[7]))
        fWrite.write('puddle-jump-delay={}\n'.format(data[8]))
        fWrite.write('cut-height={}\n'.format(data[9]))
        fWrite.write('cut-feed-rate={}\n'.format(data[10]))
        fWrite.write('cut-amps={}\n'.format(data[11]))
        fWrite.write('cut-volts={}\n'.format(data[12]))
        fWrite.write('pause-at-end={}\n'.format(data[13]))
        fWrite.write('gas-pressure={}\n'.format(data[14]))
        fWrite.write('cut-mode={}\n'.format(data[15]))
        fWrite.write('\n')
    Popen('halcmd setp plasmac_run.temp-material 1', stdout = PIPE, shell = True)
    matDelay = time.time()
    while 1:
        if time.time() > matDelay + 3:
            codeWarn = True
            wng  = '\nTemporary materials was not loaded in a timely manner:\n'
            wng += '\nTry to reload the G-Code file.\n'
            dialog_error(gtk.MESSAGE_WARNING, 'WARNING', wng)
            break
        if Popen('halcmd getp plasmac_run.temp-material', stdout = PIPE, shell = True).communicate()[0] == 'FALSE\n':
            break

# rewrite the material file
def rewrite_material_file(newMaterial):
    copyFile = '{}.bkp'.format(materialFile)
    shutil.copy(materialFile, copyFile)
    inFile = open(copyFile, 'r')
    outFile = open(materialFile, 'w')
    while 1:
        line = inFile.readline()
        if not line:
            break
        if not line.strip().startswith('[MATERIAL_NUMBER_'):
            outFile.write(line)
        else:
            break
    while 1:
        if line.strip().startswith('[MATERIAL_NUMBER_'):
            mNum = int(line.split('NUMBER_')[1].replace(']',''))
            if mNum == newMaterial[1]:
                add_edit_material(newMaterial, outFile)
        if mNum != newMaterial[1]:
            outFile.write(line)
        line = inFile.readline()
        if not line:
            break
    if newMaterial[1] not in materialDict:
        add_edit_material(newMaterial, outFile)
    inFile.close()
    outFile.close()
    Popen('halcmd setp plasmac_run.material-reload 1', stdout = PIPE, shell = True)
    get_materials()
    matDelay = time.time()
    while 1:
        if time.time() > matDelay + 3:
            codeWarn = True
            wng  = '\nMaterials were not reloaded in a timely manner:\n'
            wng += '\nTry a manual Reload or reload the G-Code file.\n'
            dialog_error(gtk.MESSAGE_WARNING, 'WARNING', wng)
            break
        if Popen('halcmd getp plasmac_run.material-reload', stdout = PIPE, shell = True).communicate()[0] == 'FALSE\n':
            break

# add a new material or or edit an existing material
def add_edit_material(material, outFile):
    outFile.write('[MATERIAL_NUMBER_{}]\n'.format(material[1]))
    outFile.write('NAME               = {}\n'.format(material[2]))
    outFile.write('KERF_WIDTH         = {}\n'.format(material[3]))
    outFile.write('THC                = {}\n'.format(material[4]))
    outFile.write('PIERCE_HEIGHT      = {}\n'.format(material[5]))
    outFile.write('PIERCE_DELAY       = {}\n'.format(material[6]))
    outFile.write('PUDDLE_JUMP_HEIGHT = {}\n'.format(material[7]))
    outFile.write('PUDDLE_JUMP_DELAY  = {}\n'.format(material[8]))
    outFile.write('CUT_HEIGHT         = {}\n'.format(material[9]))
    outFile.write('CUT_SPEED          = {}\n'.format(material[10]))
    outFile.write('CUT_AMPS           = {}\n'.format(material[11]))
    outFile.write('CUT_VOLTS          = {}\n'.format(material[12]))
    outFile.write('PAUSE_AT_END       = {}\n'.format(material[13]))
    outFile.write('GAS_PRESSURE       = {}\n'.format(material[14]))
    outFile.write('CUT_MODE           = {}\n'.format(material[15]))
    outFile.write('\n')


# create a dict of material numbers and kerf widths
def get_materials():
    global materialDict
    with open(runFile, 'r') as rFile:
        fRate = kWidth = 0.0
        for line in rFile:
            if line.startswith('cut-feed-rate'):
                fRate = float(line.split('=')[1])
            if line.startswith('kerf-width'):
                kWidth = float(line.split('=')[1])
    mNumber = 0
    with open(materialFile, 'r') as mFile:
        materialDict = {mNumber: [fRate, kWidth]}
        while 1:
            line = mFile.readline()
            if not line:
                break
            elif line.startswith('[MATERIAL_NUMBER_') and line.strip().endswith(']'):
                mNumber = int(line.rsplit('_', 1)[1].strip().strip(']'))
                break
        while 1:
            line = mFile.readline()
            if not line:
                materialDict[mNumber] = [fRate, kWidth]
                break
            elif line.startswith('[MATERIAL_NUMBER_') and line.strip().endswith(']'):
                materialDict[mNumber] = [fRate, kWidth]
                mNumber = int(line.rsplit('_', 1)[1].strip().strip(']'))
            elif line.startswith('CUT_SPEED'):
                fRate = float(line.split('=')[1].strip())
            elif line.startswith('KERF_WIDTH'):
                kWidth = float(line.split('=')[1].strip())

def check_f_word(inFeed):
    if not material[1]:
        material[0] = currentMat
    global feedWarning
    rawFeed = ''
    codeFeed = 0.0
    while len(inFeed) and (inFeed[0].isdigit() or inFeed[0] == '.'):
        rawFeed = rawFeed + inFeed[0]
        inFeed = inFeed[1:].lstrip()
    if rawFeed:
        codeFeed = float(rawFeed)
        if codeFeed != float(materialDict[material[0]][0]):
            cutFeed = materialDict[material[0]][0]
            dec = 0 if units == 'mm' else 1
            if not feedWarning:
                if cutFeed and cutFeed != codeFeed:
                    wng   = '\nGcode feed rate is F{:0.{}f}\n'.format(codeFeed, dec)
                    wng  += '\nMaterial #{} feed rate is F{:0.{}f}\n'.format(material[0], cutFeed, dec)
                    wng  += '\nTHC calculations will be based on the\n'
                    wng  += 'material #{} feed rate which may cause issues.\n'.format(material[0])
                else:
                    wng   = '\nGcode feed rate is F{:0.{}f}\n'.format(codeFeed, dec)
                    wng  += '\nMaterial #{} feed rate is F{:0.{}f}\n'.format(material[0], cutFeed, dec)
                    wng  += '\nThis will cause the THC calculations\n'
                    wng  += 'to use the motion.requested-vel HAL pin\n'
                    wng  += 'which is not recommended.\n'
                wng  += '\nThe recommended settings are to use\n'
                wng  += 'F#<_hal[plasmac.cut-feed-rate]>\n'
                wng  += 'in the G-Code file and a valid cut feed rate\n'
                wng  += 'in the material cut parameters.\n'
                wng  += '\nFirst warning near line #{}\n'.format(lineNum)
                wng  += '\nPlease check all feed rates.\n'.format(material[0])
                dialog_error(gtk.MESSAGE_WARNING, 'WARNING', wng)
                feedWarning = True

# start processing the gcode file
get_materials()
with open(inCode, 'r') as fRead:
    for line in fRead:
        lineNum += 1
        # remove whitespace
        line = line.strip()
        # remove line numbers
        if line.lower().startswith('n'):
            line = line[1:]
            while line[0].isdigit() or line[0] == '.':
                line = line[1:].lstrip()
                if not line:
                    break
        # check for a material edit
        if line.startswith('(o='):
            check_material_edit()
            continue
        # if line is a comment then print it and get next line
        if line.startswith(';') or line.startswith('('):
            print(line)
            continue
        # if a ; comment at end of line, convert line to lower case and remove spaces, preserve comment as is
        elif ';' in line:
            a,b = line.split(';', 1)
            line = '{} ({})'.format(a.strip().lower().replace(' ',''),b)
        # if a () comment at end of line, convert line to lower case and remove spaces, preserve comment as is
        elif '(' in line:
            a,b = line.split('(', 1)
            line = '{} ({}'.format(a.strip().lower().replace(' ',''),b)
        # if any other line, convert line to lower case and remove spaces
        else:
            line = line.lower().replace(' ','')
        # remove leading 0's from G & M codes
        if (line.lower().startswith('g') or \
           line.lower().startswith('m')) and \
           len(line) > 2:
            while line[1] == '0' and len(line) > 2:
                if line[2].isdigit():
                    line = line[:1] + line[2:]
                else:
                    break
        # set default units
        if 'g21' in line and units == 'in':
            if not customDia:
                minDiameter = 32
            if not customLen:
                ocLength = 4
        elif 'g20' in line and units == 'mm':
            if not customDia:
                minDiameter = 1.26
            if not customLen:
                ocLength = 0.157
        # check for g41 offset set
        if 'g41' in line:
            offsetG41 = True
        # check for g41 offset cleared
        elif 'g40' in line:
            offsetG41 = False
        # are we scribing
        if line.startswith('m3$1s'):
            if pierceOnly:
                codeWarn = True
                wng  = '\nScribe is invalid for pierce only mode.\n'
                wng += '\nError near line #{}\n'.format(lineNum)
                wng += '\nEdit GCode file to suit.'
                dialog_error(gtk.MESSAGE_WARNING, 'WARNING', wng)
                scribing = False
            else:
                scribing = True
                print(line)
                continue
        # if pierce only mode
        if pierceOnly:
            # Don't pierce spotting operations
            if line.startswith('m3$2'):
                spotting = True
                print('(Ignoring spotting operation as pierce-only is active)')
                continue
            # Ignore spotting blocks when pierceOnly
            if spotting:
                if line.startswith('m5$2'):
                    spotting = False
                continue
            if line.startswith('g0'):
                rapidLine = line
                continue
            if line.startswith('m3') and not line.startswith('m3$1'):
                pierces += 1
                print('\n(Pierce #{})'.format(pierces))
                print(rapidLine)
                print('M3 $0 S1')
                print('G91')
                print('G1 X.000001')
                print('G90\nM5 $0')
                rapidLine = ''
                continue
            if not pierces or line.startswith('o') or line.startswith('#'):
                print(line)
            continue
        # test for pierce only mode
        if (line.startswith('#<pierce-only>') and line.split('=')[1][0] == '1') or (not pierceOnly and cutType == 1):
            if scribing:
                codeWarn = True
                wng  = '\nPierce only mode is invalid while scribing.\n'
                wng += '\nError near line #{}\n'.format(lineNum)
                wng += '\nEdit GCode file to suit.'
                dialog_error(gtk.MESSAGE_WARNING, 'WARNING', wng)
            else:
                pierceOnly = True
                pierces = 0
                rapidLine = ''
                print('(pierce only mode)')
            if not cutType == 1:
                continue
        if line.startswith('#<oclength>'):
            ocLength = float(line.split('=')[1])
            customLen = True
            print('(overcut length = {})'.format(ocLength))
            continue
        # if hole sensing code
        if line.startswith('#<holes>'):
            set_hole_type()
            continue
        # if hole diameter command
        if line.startswith('#<h_diameter>') or line.startswith('#<m_diameter>') or line.startswith('#<i_diameter>'):
            if (';') in line:
                minDiameter = float(line.split('=')[1].split(';')[0])
                customDia = True
            elif ('(') in line:
                minDiameter = float(line.split('=')[1].split('(')[0])
                customDia = True
            else:
                minDiameter = float(line.split('=')[1])
                customDia = True
            print('(small hole diameter = {})'.format(minDiameter))
            if '#<m_d' in line:
                wng = '\n#<m_diameter> is deprecated in favour of #<h_diameter>\n'
            if '#<i_d' in line:
                wng = '\n#<i_diameter> is deprecated in favour of #<h_diameter>\n'
            if '#<m_d' in line or '#<i_d' in line:
                codeWarn = True
                wng += '\nThe diameter {} in line {} will read as being in\n'.format(minDiameter, lineNum)
                wng += 'the current units of the GCode file.\n'
                dialog_error(gtk.MESSAGE_WARNING, 'WARNING', wng)
            continue
        # if hole velocity command
        if line.startswith('#<h_velocity>'):
            holeVelocity = float(line.split('=')[1].split(';')[0])
            print('(small hole velocity = {})'.format(holeVelocity))
            continue
        # if material change
        if line.startswith('m190'):
            do_material_change()
            if not 'm66' in line:
                continue
        # wait for material change
        if 'm66' in line:
            if offsetG41:
                codeError = True
                wng  = '\nCannot validate a material change\n'
                wng += 'with cutter compensation active\n'
                wng += '\nError near line #{}\n'.format(lineNum)
                dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)
            print(line)
            continue
        # check if unsupported distance mode
        if holeEnable and 'g91' in line and not 'g91.1' in line:
            codeError = True
            wng  = '\nPlasmaC GCode parser only\n'
            wng += 'supports Distance Mode G90\n'
            wng += '\nError near line #{}\n'.format(lineNum)
            wng += '\nEdit GCode file to suit.'
            dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)
        # check if unsupported arc distance mode
        elif holeEnable and 'g90.1' in line:
                codeError = True
                wng  = '\nPlasmaC GCode parser only\n'
                wng += 'supports Arc Distance Mode G91.1\n'
                wng += '\nError near line #{}\n'.format(lineNum)
                wng += '\nEdit GCode file to suit.'
                dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)
        # check if we can read the values correctly
        if holeEnable and 'x' in line: check_math('x')
        if holeEnable and 'y' in line: check_math('y')
        if holeEnable and 'i' in line: check_math('i')
        if holeEnable and 'j' in line: check_math('j')
        # if z axis in line but no other axes comment it
        if 'z' in line and 1 not in [c in line for c in 'xyabcuvw'] and line.split('z')[1][0].isdigit():
            print('({})'.format(line))
            continue
        # if z axis and other axes in line, comment out the Z axis
        if 'z' in line and not '(z' in line and line.split('z')[1][0] in '0123456789.- ':
            if holeEnable:
                lastX, lastY = set_last_position(lastX, lastY)
            result = comment_out_z_commands()
            print(result)
            continue
        # if an arc command
        if (line.startswith('g2') or line.startswith('g3')) and line[2].isalpha():
            if holeEnable:
                check_if_hole()
            else:
                print(line)
            continue
        # if torch off, flag it then print it
        if line.startswith('m62p3') or line.startswith('m64p3'):
            torchEnable = False
            print(line)
            continue
        # if torch on, flag it then print it
        if line.startswith('m63p3') or line.startswith('m65p3'):
            torchEnable = True
            print(line)
            continue
        # if spindle off
        if line.startswith('m5'):
            if len(line) == 2 or (len(line) > 2 and not line[2].isdigit()):
                print(line)
                # restore velocity if required
                if holeActive:
                    lineNum += 1
                    print('m68 e3 q0 (arc complete, velocity 100%)')
                    holeActive = False
                # if torch off, allow torch on 
                if not torchEnable:
                    lineNum += 1
                    print('m65 p3 (enable torch)')
                    torchEnable = True
            else:
                print(line)
            continue
        # if program end
        if line.startswith('m2') or line.startswith('m30') or line.startswith('%'):
            # restore velocity if required
            if holeActive:
                lineNum += 1
                print('m68 e3 q0 (arc complete, velocity 100%)')
                holeActive = False
            # if torch off, allow torch on 
            if not torchEnable:
                lineNum += 1
                print('m65 p3 (enable torch)')
                torchEnable = True
            # restore hole sensing to default
            if holeEnable:
                lineNum += 1
                print('(disable hole sensing)')
                holeEnable = False
            print(line)
            if codeError:
                wng  = '\nThis GCode file has one or more errors\n'
                wng += 'that will affect the quality of the process.\n'
                wng += '\nIt is recommended that all errors are fixed\n'
                wng += 'before running this file.'
                dialog_error(gtk.MESSAGE_ERROR, 'ERROR', wng)
            continue
        # check feed rate
        if 'f' in line:
            inFeed = line.split('f')[1]
            if not inFeed.startswith('#<_hal[plasmac.cut-feed-rate]>'):
                check_f_word(inFeed)
        # restore velocity if required
        if holeActive:
            lineNum += 1
            print('m67 e3 q0 (arc complete, velocity 100%)')
            holeActive = False
        # set last X/Y position
        if holeEnable and len(line):
            lastX, lastY = set_last_position(lastX, lastY)
        print(line)
if pierceOnly:
    print('')
    if rapidLine:
        print('{}'.format(rapidLine))
    print('M2 (END)')
