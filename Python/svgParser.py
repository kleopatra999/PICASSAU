#-------------------------------------------------------------------------------
# Name:        svgParser
# Purpose:
#
# Author:      Kayla Frost
#
# Created:     30/08/2013
# Copyright:   (c) Kayla 2013
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import os
import sys
import re
import serial
from xml.dom import minidom


class svgParser:
    def __init__(self):

        #instantiate some arrays we'll use
        self.commands = []
        self.xCoords = []
        self.yCoords = []

        #use these variables to scale the instructions for the Arduino
        #these need to be floats, so include a decmial point
        self.canvasX = 22.0 #the dimension of the canvas in the x direction (in)
        self.canvasY = 28.0 #the dimension of the canvas in the y direction (in)
        self.ardDist = (100/11.125) #how much the motor moves in one step

        self.fileWidth = 1 #default file width - found in svg file
        self.fileHeight = 1 #default file height - found in svg file


#        self.ser = serial.Serial('COM5') #9600 Baud, 8 data bits, No parity, 1 stop bit


    def readInFile(self, file):
        '''
        Given a file path, this function opens it, reads it,
        and returns its contents as a string.

        '''
        if os.path.isfile(file):
            tempFile = open(file, 'r')
            output = tempFile.read()
            tempFile.close()
            return output
        else:
            return

    def parsePaths(self, svgStr):
        '''
        Given a string, presumably the text from the SVG file,
        it will strip out the paths and put them into an array.

        '''
        doc = minidom.parseString(svgStr)
        pathStrings = [path.getAttribute('d') for path in
                       doc.getElementsByTagName('path')]
        self.fileWidth = [path.getAttribute('width') for path in
                          doc.getElementsByTagName('svg')]
        self.fileHeight = [path.getAttribute('height') for path in
                       doc.getElementsByTagName('svg')]
        self.scaleX = (self.canvasX/float(self.fileWidth[0]))*self.ardDist
        self.scaleY = (self.canvasY/float(self.fileHeight[0]))*self.ardDist
        doc.unlink()
        return pathStrings

    def evalCurveEqtn(self, t, PArray):
        '''
        This function does some crazy math to evaluate the curve equation.
        It requires the t value (ranges from 0 to 1) and an array of P values
        that includes 4 entries.

        '''

        Pt = pow((1-t),3)*PArray[0] + 3*pow(1-t,2)*t*PArray[1] + 3*(1-t)*pow(t,2)*PArray[2] + pow(t,3)*PArray[3]
        return Pt

    def splitStrXY(self, str):
        '''
        This function is used to split coordinates.  It deliniates the given
        string using a comma, sending the first part followed by the second part
        (usually x,y).

        '''
        x = int(0.5+(float(str.split(',')[0])))
        y = int(0.5+(float(str.split(',')[1])))
        return x,y

    def capFirstLetOnly(self, str):
        '''
        Given a string, this function will capitalize the first letter only,
        leaving the rest of the string as it was.

        '''
        if str[0].islower:
            str = str[0].upper() + str[1:]
            upperFlag = False
        return str, upperFlag

    def matchAny(self, lookingfor, element):
        '''
        Given the string of what you're looking for, this function will return
        a boolean True if any character in the "lookingfor" is in "element".

        '''
        lookingfor = '[' + lookingfor + ']'
        return re.match(lookingfor, element)

    def addToList(self, addition, listName):
        '''
        Given the addition, this function will add it to the appropriate list,
        given as a string (all lowercase).
        'command' = the command array
        'x' = the x array
        'y' = the y array

        '''
        if listName is 'command': #if the addition is a command...
            self.commands.append(addition)
        elif listName is 'x': #else if the addition is an x coordinate...
            self.xCoords.append(int((addition*self.scaleX)+0.5))
        else: #hopefully the addtion is a y coordinate...
            self.yCoords.append(int((addition*self.scaleY)+0.5))

    def sendToArduino(self, i):
        serOut = str(self.commands[i]) + ' ' + str(self.xCoords[i]) + ',' + str(self.yCoords[i]) + '\n'
        self.ser.write(serOut)
        return serOut

    def readFromArduino(self):
        self.ser.flush()
        ardCheck = self.ser.readline()
        return ardCheck

def main():

    mySVG = svgParser()
    #load in file - here I'm doing it manually
    file = "C:\Users\Kayla\Documents\School\Fall 2013\Senior Design\svgParser\demoCircle.svg"

    #N sets how many sections curves are divided into
    N = 10
    Ccount = 0
    PXArray = []
    PYArray = []

    #instantiate some flags

    #remember the last element and last command given
    lastElemLet = None
    lastComm = None

    #remember the last case used: upper = True, lower = False
    lastCaseUp = None

    #remember the value of the last x and y coordinates
    lastXCoord = 0
    lastYCoord = 0

    #remember the first coordinate of each path
    pathFirstCoordFlag = None
    pathFirstXCoord = 0
    pathFirstYCoord = 0

    #read in the file and parse out the paths into an array of strings
    svgStr = mySVG.readInFile(file)
    pathStrings = mySVG.parsePaths(svgStr)

    #iteratively run through the paths, correct letters, and reorganize
    #into the different arrays
    for path in pathStrings:
        path, lastCaseUp = mySVG.capFirstLetOnly(path)
        #we want to make sure the first letter is capitalized and set the flag

        elements = path.split(' ') #split the elements based on spaces
        pathFirstCoordFlag = True #raise the falg to say it's the first coord of the path

        #iterate through each element of the path i.e. each letter or number set
        for element in elements:
            #check to see if the element is an acceptable letter
            if mySVG.matchAny('mlzcMLZC', element):
                if mySVG.matchAny('zZ', element):
                   #if the letter is Z, then we need to close the loop by drawing
                   #back to the first coordinate of the path.  To do this, add a
                   #"L" to the command array, and put the initial x and y coords
                   #into the x and y arrays.
                   mySVG.addToList('L', 'command')
                   mySVG.addToList(pathFirstXCoord, 'x')
                   mySVG.addToList(pathFirstYCoord, 'y')
                   lastElemLet = True
                   lastComm = 'zZ'

                elif mySVG.matchAny("cC", element):
                    #if the letter is C, then just set the right flags, and we'll
                    #take care of it when we get to the actual numbers (see below)
                    if mySVG.matchAny("c", element):
                        lastComm = 'c'
                    else:
                        lastComm = 'C'
                    Ccount = 0
                    lastElemLet = True

                else: #letter is m/M/l/L
                    #if the letter is lowercase, change the lastCaseUp flag and add
                    #the uppercase version to the command array
                    if element.islower():
                        element = str(element)
                        element = element.upper()
                        lastCaseUp = False
                        mySVG.addToList(element, 'command')
                    #if the letter isn't lowercase, change the flag and add the
                    #element to the commands
                    elif not pathFirstCoordFlag:
                        lastCaseUp = True
                        mySVG.addToList(element, 'command')
                    else:
                        mySVG.addToList(element, 'command')
                    lastElemLet = True
                    lastComm = 'mMlL'

            #if the element isn't a letter...(it's a number)
            else:
                #this section will go through calculating a curve
                if lastComm is ('c' or 'C'):
                    if Ccount  is 0: #this is a counter to gather the curve coords
                        #the first point used to calucalte the curve is the previous
                        #point, so add the x and y to the corresponding P arrays
                        PXArray.append(lastXCoord)
                        PYArray.append(lastYCoord)
                    Ccount += 1 #increment count because we've got 1 point down

                    #add the current coordinates to the PX and PY arrays
                    tempx = mySVG.splitStrXY(element)[0]
                    tempy = mySVG.splitStrXY(element)[1]
                    if lastComm is 'c':
                        #if c is lowercase, it's relative to the 1st point
                        tempx += PXArray[0]
                        tempy += PYArray[0]
                    PXArray.append(tempx)
                    PYArray.append(tempy)
                    if Ccount is 3: #when you've got 4 points...

                        #Actual Points = P(i/N), so iteratively solve for these
                        for i in range(N):
                            mySVG.addToList('L', 'command') #each move requires drawing a line
                            mySVG.addToList(int(mySVG.evalCurveEqtn((float(i)/N), PXArray)), 'x')
                            mySVG.addToList(int(mySVG.evalCurveEqtn((float(i)/N), PYArray)), 'y')

                        #the last point on the curve is the last point given from the file
                        mySVG.addToList('L', 'command')
                        tempx = PXArray[3]
                        tempy = PYArray[3]
                        mySVG.addToList(tempx, 'x')
                        mySVG.addToList(tempy, 'y')
                        Ccount = 0 #reset the count in case you have another curve
                        PXArray = []
                        PYArray = []


                else:
                    if not lastElemLet:
                        #if the last command was an M or L, any non-explicit instru-
                        #ctions will be "L's" so we add that to the commands
                        mySVG.addToList('L', 'command')

                    #split the element: before the comma is the x element, after is the y
                    tempx, tempy = mySVG.splitStrXY(element)

                    #if the last case was lower, we need to translate relative coords
                    #to absolute by adding them to the previous absolute coordinates
                    if not lastCaseUp:
                        if not pathFirstCoordFlag:
                            tempx += lastXCoord
                            tempy += lastYCoord

                    #add the coordinates to the corresponding arrays
                    mySVG.addToList(tempx, 'x')
                    mySVG.addToList(tempy, 'y')

                #save the current x and y coordinates
                lastXCoord = tempx
                lastYCoord = tempy

                #check to see if it's the first coordinate of the path
                if pathFirstCoordFlag:
                    pathFirstXCoord = lastXCoord
                    pathFirstYCoord = lastYCoord
                    pathFirstCoordFlag = False

                lastElemLet = False

    print mySVG.commands
    print mySVG.xCoords
    print mySVG.yCoords

'''
    #start talking to Arduino
    index = 0 #this index refers to the number command we're on as we iterate
              #through the arrays (command, xcoords, ycoords)
    for eachComm in mySVG.commands: #for each command...
        #reset the output and check variables
        serOut = None
        ardCheck = None

        readyByte = mySVG.ser.read() #read 1 byte from Arduino
        while readyByte is not 'R':() #wait for the ready signal from the Arduino
        print "got ready signal"
        serOut = mySVG.sendToArduino(index) #write the 3 arrays to the Arduino
        ardCheck = mySVG.readFromArduino() #read the check from the Arduino
        if '\n' in ardCheck: #sometimes the check is just a new line character
                             #if this is the case, read it again
            ardCheck = mySVG.readFromArduino()
        while(serOut not in ardCheck): #we're looking for our output to match the check
                                       #so keep sending/reading until they match
            serOut = mySVG.sendToArduino(index)
            ardCheck = mySVG.readFromArduino()
        mySVG.ser.write('G\n') #when you get the instructions to match, send out a
                               #go signal and wait for the Arduino to be ready again
        print 'g'
        index += 1
        readyByte = None
        print ardCheck
    mySVG.ser.write('D\n')
    ardCheck = mySVG.readFromArduino()
    while 'D' not in ardCheck:
        ardCheck = mySVG.readFromArduion()
    mySVG.ser.write('G\n')
    mySVG.ser.close() #when you're done with everything, close the serial connection
    print "done"
'''

if __name__ == '__main__':
    main()