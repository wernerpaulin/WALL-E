#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python /home/pi/Yaha/yaha_main.py


class chartLin():
    #init
    def __init__(self):
        self.points = []

    def addPointPair(self, x, y):
        self.points.append([])
        self.points[len(self.points)-1].append(x)
        self.points[len(self.points)-1].append(y)

        #resort list so that all x values are ascending
        self.points.sort()


    def calcYfromX(self, x):
        #check whether x is outside of chart boundary
        if (x <= self.points[0][0]):
            minBoundaryIndex = 0
            maxBoundaryIndex = minBoundaryIndex + 1
        elif (x >= self.points[len(self.points)-1][0]):
            maxBoundaryIndex = len(self.points)-1
            minBoundaryIndex = maxBoundaryIndex - 1
        else:
            #find segment in which x is within. Assume ascending value order
            for pairIndex in range(len(self.points)):
                if (self.points[pairIndex][0] >= x):
                    minBoundaryIndex = pairIndex - 1
                    maxBoundaryIndex = pairIndex
                    break        

        #interpolation
        xyInterpol = xyLin()
        xyInterpol.x1 = self.points[minBoundaryIndex][0]
        xyInterpol.x2 = self.points[maxBoundaryIndex][0]
        xyInterpol.y1 = self.points[minBoundaryIndex][1]
        xyInterpol.y2 = self.points[maxBoundaryIndex][1]

        xyInterpol.calcK()
        xyInterpol.calcD()
        
        
        return xyInterpol.calcYfromX(x)
        

class xyLin():
    #init
    def __init__(self):
        self.x1 = 0         #x axis
        self.x2 = 0
        self.y1 = 0         #y axis
        self.y2 = 0
        self.k = 0
        self.d = 0
        self.xMin = 0
        self.xMax = 0
        self.yMin = 0
        self.yMax = 0
    
    def calcK(self):
        try:
            self.k = (float(self.y2) - float(self.y1)) / (float(self.x2) - float(self.x1)) 
        except:
            self.k = 0

    def calcD(self):
        try:
            self.d = ( (float(self.y1) * float(self.x2)) - (float(self.y2) * float(self.x1)) ) / (float(self.x2) - float(self.x1))
        except:
            self.d = 0
        
    def calcYfromX(self, x):
        try:
            return self.k * float(x) + self.d #y = kx + d
        except:
            return 0

    def limitY(self, y):
        return max(min(y, self.yMax), self.yMin)

    
    def calcXfromY(self, y):
        try:
            return (y - self.d) / self.k     #x = (y - d) / k
        except:
            return 0

    def limitX(self, x):
        return max(min(x, self.xMax), self.xMin)


if __name__ == "__main__":
    print("!!! DEBUGGING !!!")
    tempChart = chartLin()
    tempChart.addPointPair(642, -10)
    tempChart.addPointPair(633, -5)
    tempChart.addPointPair(623, 0)
    tempChart.addPointPair(612, 5)
    tempChart.addPointPair(600, 10)
    tempChart.addPointPair(588, 15)
    tempChart.addPointPair(575, 20)
    tempChart.addPointPair(563, 25)
    
    #for pointPair in tempChart.points:
    #    print(pointPair)
    
    print(tempChart.calcYfromX(650))
