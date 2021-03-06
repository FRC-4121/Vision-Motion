# -*- coding: utf-8 -*-
#!/usr/bin/env python3

####################################################################
#                                                                  #
#                       FRC Vision Library                         #
#                                                                  #
#  This class provides numerous methods and utilities for vision   #
#  processing during an FRC game.  The provided methods cover      #
#  finding standard game elements (balls, cubes, etc.) as well as  #
#  retroreflective vision targets in video frames.                 #
#                                                                  #
#  @Version: 1.0                                                   #
#  @Created: 2020-1-8                                              #
#  @Author: Team 4121                                              #
#                                                                  #
####################################################################

'''FRC Vision Library - Provides vision processing for game elements'''

# System imports
import os

# Module Imports
import cv2 as cv
import numpy as np 
import math

# Define the vision library class
class VisionLibrary:

    # Define class fields
    visionFile = ""
    ball_values = {}
    goal_values = {}
    tape_values = {}


    # Define class initialization
    def __init__(self, visionfile):
        
        #Read in vision settings file
        VisionLibrary.visionFile = visionfile
        self.read_vision_file(VisionLibrary.visionFile)


    # Read vision settings file
    def read_vision_file(self, file):

        # Declare local variables
        value_section = ''
        new_section = False

        # Open the file and read contents
        try:
            
            # Open the file for reading
            in_file = open(file, 'r')
            
            # Read in all lines
            value_list = in_file.readlines()
            
            # Process list of lines
            for line in value_list:
                
                # Remove trailing newlines and whitespace
                clean_line = line.strip()

                # Split the line into parts
                split_line = clean_line.split(',')

                # Determine section of the file we are in
                if split_line[0].upper() == 'BALL:':
                    value_section = 'BALL'
                    new_section = True
                elif split_line[0].upper() == 'GOALTARGET:':
                    value_section = 'GOALTARGET'
                    new_section = True
                elif split_line[0].upper() == 'VISIONTAPE:':
                    value_section = 'VISIONTAPE'
                    new_section = True
                elif split_line[0] == '':
                    value_section = ''
                    new_section = True
                else:
                    new_section = False

                # Take action based on section
                if new_section == False:
                    if value_section == 'BALL':
                        VisionLibrary.ball_values[split_line[0].upper()] = split_line[1]
                    elif value_section == 'GOALTARGET':
                        VisionLibrary.goal_values[split_line[0].upper()] = split_line[1]
                    elif value_section == 'VISIONTAPE':
                        VisionLibrary.tape_values[split_line[0].upper()] = split_line[1]
                    else:
                        new_section = True
        
        except FileNotFoundError:
            return False
        
        return True


    # Define basic image processing method for contours
    def process_image_contours(self, imgRaw, hsvMin, hsvMax):
    
        # Blur image to remove noise
        blur = cv.GaussianBlur(imgRaw.copy(),(13,13),0)
        
        # Convert from BGR to HSV colorspace
        hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)

        # Set pixels to white if in target HSV range, else set to black
        mask = cv.inRange(hsv, hsvMin, hsvMax)

        # Find contours in mask
        _, contours, _ = cv.findContours(mask,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)
    
        return contours


    # Define basic image processing method for edge detection
    def process_image_edges(self, imgRaw):

        # Blur image to remove noise
        blur = cv.GaussianBlur(imgRaw.copy(),(13,13),0)
        
        # Convert from BGR to HSV colorspace
        hsv = cv.cvtColor(blur, cv.COLOR_BGR2HSV)

        # Detect edges
        edges = cv.Canny(hsv, 35, 125)

        # Find contours using edges
        _, contours, _ = cv.findContours(edges.copy(),cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)

        return contours


    # Find ball game pieces
    def detect_game_balls(self, imgRaw, cameraWidth, cameraHeight, cameraFOV):

        # Read HSV values from dictionary and make tuples
        hMin = int(VisionLibrary.ball_values['HMIN'])
        hMax = int(VisionLibrary.ball_values['HMAX'])
        sMin = int(VisionLibrary.ball_values['SMIN'])
        sMax = int(VisionLibrary.ball_values['SMAX'])
        vMin = int(VisionLibrary.ball_values['VMIN'])
        vMax = int(VisionLibrary.ball_values['VMAX'])
        ballHSVMin = (hMin, sMin, vMin)
        ballHSVMax = (hMax, sMax, vMax)
        
        # Initialize variables
        distanceToBall = 0 #inches
        angleToBall = 0 #degrees
        ballOffset = 0
        screenPercent = 0
        ballsFound = 0
        ballData = []

        # Find contours in the mask and clean up the return style from OpenCV
        ballContours = self.process_image_contours(imgRaw, ballHSVMin, ballHSVMax)

        # Only proceed if at least one contour was found
        if len(ballContours) > 0:

            #Sort contours by area (reverse order so largest is first)
            sortedContours = sorted(ballContours, key=cv.contourArea, reverse=True)

            #Process each contour
            for contour in sortedContours:

                #Find enclosing circle
                ((x, y), radius) = cv.minEnclosingCircle(contour)

                #Proceed if circle meets minimum radius requirement
                if radius > int(VisionLibrary.ball_values['MINRADIUS']):
            
                    #Calculate ball metrics
                    inches_per_pixel = float(VisionLibrary.ball_values['RADIUS'])/radius #set up a general conversion factor
                    distanceToBall = inches_per_pixel * (cameraWidth / (2 * math.tan(math.radians(cameraFOV))))
                    offsetInInches = inches_per_pixel * (x - cameraWidth / 2)
                    angleToBall = math.degrees(math.atan((offsetInInches / distanceToBall)))
                    screenPercent = math.pi * radius * radius / (cameraWidth * cameraHeight)
                    ballOffset = -offsetInInches

                    #Save values to dictionary
                    ballDataDict = {}
                    ballDataDict['x'] = x
                    ballDataDict['y'] = y
                    ballDataDict['radius'] = radius
                    ballDataDict['distance'] = distanceToBall
                    ballDataDict['angle'] = angleToBall
                    ballDataDict['offset'] = ballOffset
                    ballDataDict['percent'] = screenPercent

                    #Add dictionary to return list
                    ballData.append(ballDataDict)

                    #Increment ball count
                    ballsFound = ballsFound + 1
        
                else:

                    #No more contours meet criteria so break loop
                    break

        return ballsFound, ballData


    # Define general tape detection method (rectangle good for generic vision tape targets)
    def detect_tape_rectangle(self, imgRaw, imageWidth, imageHeight, cameraFOV, cameraFocalLength, cameraMountAngle, cameraMountHeight):

        # Read HSV values from dictionary and make tupples
        hMin = int(VisionLibrary.tape_values['HMIN'])
        hMax = int(VisionLibrary.tape_values['HMAX'])
        sMin = int(VisionLibrary.tape_values['SMIN'])
        sMax = int(VisionLibrary.tape_values['SMAX'])
        vMin = int(VisionLibrary.tape_values['VMIN'])
        vMax = int(VisionLibrary.tape_values['VMAX'])
        tapeHSVMin = (hMin, sMin, vMin)
        tapeHSVMax = (hMax, sMax, vMax)

        # Initialize processing values
        targetX = 1000
        targetY = 1000
        targetW = 1000
        targetH = 1000
        aspectRatio = 0
        centerOffset = 0
        cameraAngle = 0
        actualVertAngle = 0
        botAngle = 0
        apparentTapeWidth = 0
        distanceArg = 0
        straightLineDistance = 1000
        distanceToTape = 1000
        distanceToWall = 1000
        horizAngleToTape = 0
        vertAngleToTape = 0
        inchesPerPixel = 0
        horizOffsetPixels = 0
        horizOffsetInInches = 0
        vertOffsetPixels = 0
        vertOffsetInInches = 0
        rect = None
        box = None

        # Initialize flags
        foundTape = False
        targetLock = False

        goalHeight = 90.0

        # Return dictionary
        tapeCameraValues = {}
        tapeRealWorldValues = {}
        
        # Find alignment tape in image
        tapeContours = self.process_image_contours(imgRaw, tapeHSVMin, tapeHSVMax)
  
        # Continue with processing if alignment tape found
        if len(tapeContours) > 0:

            # Find the largest contour and check it against the mininum tape area
            largestContour = max(tapeContours, key=cv.contourArea)
                        
            if cv.contourArea(largestContour) > int(VisionLibrary.tape_values['MINAREA']):
                
                # Find horizontal rectangle
                targetX, targetY, targetW, targetH = cv.boundingRect(largestContour)

                # Calculate aspect ratio
                aspectRatio = targetW / targetH

                # Find angled rectangle
                rect = cv.minAreaRect(largestContour)#((x, y), (h, w), angle)
                box = cv.boxPoints(rect)
                box = np.int0(box)

                # Find angle of bot to target
                angle = rect[2]
                if abs(angle) < 45:
                    cameraAngle = abs(angle)
                else:
                    cameraAngle = 90 - abs(angle)
                botAngle = 2 * cameraAngle

                # Set flag
                foundTape = True
                
            # Calculate real world values of found tape
            if foundTape:
                
                # Adjust tape size for robot angle
                apparentTapeWidth = float(VisionLibrary.tape_values['TAPEWIDTH']) * math.cos(math.radians(botAngle))
                
                # Calculate inches per pixel conversion factor
                inchesPerPixel = apparentTapeWidth / targetW

                # Find tape offsets
                horizOffsetPixels = (targetX + targetW/2) - imageWidth / 2
                horizOffsetInInches = inchesPerPixel * horizOffsetPixels
                vertOffsetPixels = (imageHeight / 2) - (targetY - targetH/2)
                vertOffsetInInches = inchesPerPixel * vertOffsetPixels
                centerOffset = -horizOffsetInInches
                
                # Calculate distance to tape
                straightLineDistance = apparentTapeWidth * cameraFocalLength / targetW
                distanceArg = math.pow(straightLineDistance, 2) - math.pow((float(VisionLibrary.tape_values['GOALHEIGHT']) - cameraMountHeight),2)
                if (distanceArg > 0):
                    distanceToTape = math.sqrt(distanceArg)
                distanceToWall = distanceToTape / math.cos(math.radians(botAngle))                

                # Find tape offsets
                horizAngleToTape = math.degrees(math.atan((horizOffsetInInches / distanceToTape)))
                vertAngleToTape = math.degrees(math.atan((vertOffsetInInches / distanceToTape)))

                # Determine if we have target lock
                if abs(horizOffsetInInches) <= float(VisionLibrary.tape_values['LOCKTOLERANCE']):
                    targetLock = True

        # Fill return dictionary
        tapeCameraValues['TargetX'] = targetX
        tapeCameraValues['TargetY'] = targetY
        tapeCameraValues['TargetW'] = targetW
        tapeCameraValues['TargetH'] = targetH
        tapeCameraValues['IPP'] = inchesPerPixel
        tapeCameraValues['Offset'] = horizOffsetPixels
        tapeRealWorldValues['AspectRatio'] = aspectRatio
        tapeRealWorldValues['CenterOffset'] = centerOffset
        tapeRealWorldValues['StraightDistance'] = straightLineDistance
        tapeRealWorldValues['TapeDistance'] = distanceToTape
        tapeRealWorldValues['WallDistance'] = distanceToWall
        tapeRealWorldValues['HAngle'] = horizAngleToTape
        tapeRealWorldValues['VAngle'] = vertAngleToTape
        tapeRealWorldValues['TargetRotation'] = cameraAngle
        tapeRealWorldValues['BotAngle'] = botAngle
        tapeRealWorldValues['ApparentWidth'] = apparentTapeWidth
        tapeRealWorldValues['VertOffset'] = vertOffsetInInches

        return tapeCameraValues, tapeRealWorldValues, foundTape, targetLock, rect, box

