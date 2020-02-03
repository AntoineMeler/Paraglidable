import math, sys
import dateutil.parser
import pandas as pd


#================================================================================
# valToColorLst
#================================================================================


paraglidableColors = ([0.0,0.5,1.0], ["A00000", "A07000", "00A000"])


def valToColorLst(val, vals, colors):
    if val < vals[0]:
        val = vals[0]
    if val > vals[-1]:
        val = vals[-1]

    for v in range(len(vals)-1):
        if val <= vals[v+1]:
            colorR = int(colors[v][0:2], 16), int(colors[v+1][0:2], 16)
            colorG = int(colors[v][2:4], 16), int(colors[v+1][2:4], 16)
            colorB = int(colors[v][4:6], 16), int(colors[v+1][4:6], 16)

            interp = (val - vals[v])/(vals[v+1] - vals[v])
            colorRint = interp*(colorR[1]-colorR[0]) + colorR[0]
            colorGint = interp*(colorG[1]-colorG[0]) + colorG[0]
            colorBint = interp*(colorB[1]-colorB[0]) + colorB[0]

            return (int(0.5+colorRint), int(0.5+colorGint), int(0.5+colorBint))

    return (0,0,0)


def valToColor(val, vals, colors):
    color = valToColorLst(val, vals, colors)
    return "%02x%02x%02x" % color


#================================================================================
# Utils
#================================================================================



def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))


#================================================================================
# BBoxes
#================================================================================


class BBoxLatLon:
    # ATTENTION MEMBRES STATICS ???
    minLat = 0
    maxLat = 0
    minLon = 0
    maxLon = 0

    def __init__(self, minLat, maxLat, minLon, maxLon):
        self.minLat = minLat
        self.maxLat = maxLat
        self.minLon = minLon
        self.maxLon = maxLon

    def inbb(self, lat, lon):
        epsilon = 1e-10
        return self.minLat-epsilon <= lat <= self.maxLat+epsilon and self.minLon-epsilon <= lon <= self.maxLon+epsilon
    
    def overlaps(self, otherBBox):
        return (otherBBox.minLat < self.maxLat and otherBBox.maxLat > self.minLat) and (otherBBox.minLon < self.maxLon and otherBBox.maxLon > self.minLon)


class BBoxTime:
    # ATTENTION MEMBRES STATICS ???
    minTime = ""
    maxTime = ""

    def __init__(self, minTime, maxTime):
        self.minTime = minTime
        self.maxTime = maxTime

    def inbb(self, time):
        return self.minTime <= time <= self.maxTime

    def start(self):
        return dateutil.parser.parse(self.minTime)

    def end(self):
        return dateutil.parser.parse(self.maxTime)

    def date_range(self):
        return pd.date_range(self.start(), self.end())


#================================================================================
# GridLatLon
#================================================================================


class GridLatLon:

    # ATTENTION MEMBRES STATICS ???
    
    data = []
    resolutionLat = 1.0 # degrees
    resolutionLon = 1.0 # degrees
    originLat     = 0.0
    originLon     = 0.0

    def __init__(self, resolutionLat, resolutionLon, originLat=0.0, originLon=0.0):
        self.data = [[[] for lon in range(int(math.ceil((360.0-originLon)/resolutionLon)))] for lat in range(int(math.ceil((180.0-originLat)/resolutionLat)))]
        self.resolutionLat = resolutionLat
        self.resolutionLon = resolutionLon
        self.originLat = originLat
        self.originLon = originLon

    def getStructure(self):
        return GridLatLon(self.resolutionLat, self.resolutionLon, self.originLat, self.originLon)

    def getCellCenterLatLon(self, iCellLatLon):
        return ((iCellLatLon[0]+0.5)*self.resolutionLat + self.originLat -  90.0,
                (iCellLatLon[1]+0.5)*self.resolutionLon + self.originLon - 180.0)

    def getCellForLatLon(self, lat, lon):
        iCellLat = clamp(int((lat-self.originLat +  90.0) / self.resolutionLat), 0, len(self.data)   -1)
        iCellLon = clamp(int((lon-self.originLon + 180.0) / self.resolutionLon), 0, len(self.data[0])-1)
        return iCellLat, iCellLon

    def addi(self, iCellLatLon, obj):
        self.data[iCellLatLon[0]][iCellLatLon[1]] += [obj]

    def add(self, lat, lon, obj):
        iCellLat, iCellLon = self.getCellForLatLon(lat, lon)
        GridLatLon.addi(self, (iCellLat, iCellLon), obj)

    def getNonEmptyCells(self):
        res = []
        for iCellLat in range(len(self.data)):
            for iCellLon in range(len(self.data[iCellLat])):
                if len(self.data[iCellLat][iCellLon]) > 0:
                    res += [(iCellLat, iCellLon)]
        return res

    def sortCellContent(self, iCellLatLon, sortingFunction):
        self.getCellContent(iCellLatLon).sort(key=sortingFunction)

    def getCellContent(self, iCellLatLon):
        return self.data[iCellLatLon[0]][iCellLatLon[1]]

    def nbCells(self):
        return len(self.data) * len(self.data[0])

    def printStats(self):
        print("nb cells: "+ str(self.nbCells()))
        print("nb non-empty cells: "+ str(len(self.getNonEmptyCells())))

    def exportCsv(self, filename, cellValFnt, bBoxLatLon = None, *args):
        csv = "lat lon val"
        for iCellLat in range(len(self.data)):
            for iCellLon in range(len(self.data[iCellLat])):
                lat, lon = self.getCellCenterLatLon((iCellLat, iCellLon))
                if bBoxLatLon != None and not bBoxLatLon.inbb(lat, lon):
                    continue
                val = cellValFnt(self.data[iCellLat][iCellLon], *args)
                csv += "%f %f %f\n" % (lat, lon, val)

        with open(filename, "w") as text_file:
            text_file.write(csv)

        return csv


    def export_json(self, filename, cellValFnt, bBoxLatLon = None, *args):
        jsonHead = "{ \"analysis\": [ "

        jsonBody = ""
        cells = self.getNonEmptyCells()
        for cell in cells:

            lat, lon = self.getCellCenterLatLon(cell)
            if bBoxLatLon and not bBoxLatLon.inbb(lat, lon):
                continue

            strValsList = []
            if type(cellValFnt) in [list,tuple]:
                for v,vfnt in enumerate(cellValFnt):
                    val = vfnt(self.data[cell[0]][cell[1]], *args)
                    strValsList += [str(val)]

            else:
                assert(False)

            if jsonBody != "":
                jsonBody += ","

            jsonBody += "{"
            jsonBody += "\"coords\": {\"lat\":%f, \"lon\":%f}," % (lat,lon)
            jsonBody += "\"predictions\": ["+ ",".join(strValsList) +"]"
            jsonBody += "}"


        jsonBody += "]}"


        with open(filename, "w") as text_file:
            text_file.write(jsonHead + jsonBody)


    def exportGeoJson(self, filename, cellValFnt, bBoxLatLon = None, *args):
        geojsonHead = "{\"type\": \"FeatureCollection\",\"features\": ["

        geojsonBody = ""
        cells = self.getNonEmptyCells()
        for cell in cells:
            lat, lon = self.getCellCenterLatLon(cell)
            if bBoxLatLon and not bBoxLatLon.inbb(lat, lon):
                continue

            if type(cellValFnt) in [list,tuple]:
                strProperties = ""
                for v,vfnt in enumerate(cellValFnt):
                    val = vfnt(self.data[cell[0]][cell[1]], *args)
                    if v>0:
                        strProperties += ","
                    strProperties += ("\"val%d\": "%v)+ str(val)

            else:
                val = cellValFnt(self.data[cell[0]][cell[1]], *args)
                strProperties = "\"val\": "+ str(val)

            if geojsonBody != "":
                geojsonBody += ","
            geojsonBody += "{\"type\": \"Feature\", \"properties\": {"+ strProperties +"},\"geometry\": {\"type\": \"Polygon\",\
                             \"coordinates\": [[[%f, %f], [%f, %f], [%f, %f], [%f, %f], [%f, %f]]]}}\n" % ( lon-self.resolutionLon/2., lat-self.resolutionLat/2.,
                                                                                               lon+self.resolutionLon/2., lat-self.resolutionLat/2.,
                                                                                               lon+self.resolutionLon/2., lat+self.resolutionLat/2.,
                                                                                               lon-self.resolutionLon/2., lat+self.resolutionLat/2.,
                                                                                               lon-self.resolutionLon/2., lat-self.resolutionLat/2.)
        geojsonFoot = "]}"

        with open(filename, "w") as text_file:
            text_file.write(geojsonHead + geojsonBody + geojsonFoot)


    def exportAscii(self, filename, cellValFnt, bBoxLatLon = None, *args):

        assert(self.resolutionLat == self.resolutionLon)
        assert bBoxLatLon

        NODATA_value = -9999

        if bBoxLatLon:
            ncols = int((bBoxLatLon.maxLon - bBoxLatLon.minLon)/self.resolutionLon)
            nrows = int((bBoxLatLon.maxLat - bBoxLatLon.minLat)/self.resolutionLat)

        cellTopLeft = self.getCellForLatLon(bBoxLatLon.minLat, bBoxLatLon.minLon)

        yllcorner =  -90 + self.originLat + cellTopLeft[0]*self.resolutionLat
        xllcorner = -180 + self.originLon + cellTopLeft[1]*self.resolutionLon

        head  = ""
        head += "ncols        %d\n" % ncols
        head += "nrows        %d\n" % nrows
        head += "xllcorner    %f\n" % xllcorner
        head += "yllcorner    %f\n" % yllcorner
        head += "cellsize     %f\n" % self.resolutionLat
        head += "NODATA_value %f\n" % NODATA_value

        body = ""
        for row in range(cellTopLeft[0], cellTopLeft[0]+nrows):
            for col in range(cellTopLeft[1], cellTopLeft[1]+ncols):
                print(row, col)
                print(self.getCellCenterLatLon((row, col)))
                print(self.data[row][col])
                val = cellValFnt(self.data[row][col], *args)
                body += "%f " % val
            body += "\n"

        with open(filename, "w") as text_file:
            text_file.write(head + body)

    # val doit etre un entier dans [minVal, maxVal]
    def encodeValue(self, vals, minVal, maxVal, nbChiffres):
        charSet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,?.;:/=+%*^-_!@"

        # len(vals) chiffres en base (maxVal-minVal) -> base 10
        encodedNb = 0
        for v,val in enumerate(vals):
            if v>0:
                val *= (maxVal-minVal+1)
            encodedNb += val-minVal

        # base 10 -> 3 chiffres en base len(charSet)
        res = ""
        for c in range(nbChiffres):
            res       += charSet[encodedNb %  len(charSet)]
            encodedNb  = encodedNb // len(charSet)

        # TODO, encoder les couples de valeur avec 3 chiffres dans cette base
        return res

    def exportEncodedJson(self, filename, cellValFnt, bBoxLatLon = None, *args):
        assert(self.resolutionLat == self.resolutionLon)
        assert bBoxLatLon

        if bBoxLatLon:
            ncols = int((bBoxLatLon.maxLon - bBoxLatLon.minLon)/self.resolutionLon)
            nrows = int((bBoxLatLon.maxLat - bBoxLatLon.minLat)/self.resolutionLat)

        cellTopLeft = self.getCellForLatLon(bBoxLatLon.minLat, bBoxLatLon.minLon)

        yllcorner =  -90 + self.originLat + cellTopLeft[0]*self.resolutionLat
        xllcorner = -180 + self.originLon + cellTopLeft[1]*self.resolutionLon

        minVal = 0
        maxVal = 100

        js  = "{"
        js += "\"ncols\": %d,\n" % ncols
        js += "\"nrows\": %d,\n" % nrows
        js += "\"xllcorner\": %f,\n" % xllcorner
        js += "\"yllcorner\": %f,\n" % yllcorner
        js += "\"cellsize\": %f,\n" % self.resolutionLat
        js += "\"minVal\": %d,\n" % minVal
        js += "\"maxVal\": %d,\n" % maxVal

        if type(cellValFnt) in [list,tuple]:
            nbChiffres = 3
            nbVals     = len(cellValFnt)
        else:
            nbChiffres = 2
            nbVals     = 1

        js += "\"nbChiffres\": %d,\n" % nbChiffres
        js += "\"nbVals\": %d,\n"     % nbVals

        js += "\"data\": \""

        for row in range(cellTopLeft[0], cellTopLeft[0]+nrows):
            for col in range(cellTopLeft[1], cellTopLeft[1]+ncols):
                if type(cellValFnt) in [list,tuple]:
                    vals = []
                    for oneCellValFnt in cellValFnt:
                        vals += [int(round(oneCellValFnt(self.data[row][col], *args)*100.0))]
                    js += self.encodeValue(vals, minVal, maxVal, nbChiffres)
                else:
                    val = int(round(cellValFnt(self.data[row][col], *args)*100.0))
                    js += self.encodeValue([val], minVal, maxVal, nbChiffres)
                    
        js += "\"\n"
        js += "}"

        with open(filename, "w") as text_file:
            text_file.write(js)

    def latEquiToMercator(self, lat):
        return 180.0/math.pi*math.log(math.tan(math.pi/4.0 + (lat/180.0*math.pi)/2.0))

    def export_data_for_tiler(self, filename, cellValFnt, bBoxLatLon = None, *args):
        data = ""

        cells = self.getNonEmptyCells()

        # compute bounding box
        if not bBoxLatLon:
            effectiveBBoxLatLon = BBoxLatLon(1000, -1000, 1000, -1000)
            for cell in cells:
                lat, lon = self.getCellCenterLatLon(cell)
                effectiveBBoxLatLon.minLat = min(effectiveBBoxLatLon.minLat, lat - 0.5*self.resolutionLat)
                effectiveBBoxLatLon.maxLat = max(effectiveBBoxLatLon.maxLat, lat + 0.5*self.resolutionLat)
                effectiveBBoxLatLon.minLon = min(effectiveBBoxLatLon.minLon, lon - 0.5*self.resolutionLon)
                effectiveBBoxLatLon.maxLon = max(effectiveBBoxLatLon.maxLon, lon + 0.5*self.resolutionLon)
        else:
            effectiveBBoxLatLon = bBoxLatLon

        effectiveBBoxLatLonMercator = BBoxLatLon(self.latEquiToMercator(effectiveBBoxLatLon.minLat), self.latEquiToMercator(effectiveBBoxLatLon.maxLat), effectiveBBoxLatLon.minLon, effectiveBBoxLatLon.maxLon)

        for cell in cells:
            lat, lon = self.getCellCenterLatLon(cell)
            if bBoxLatLon and not bBoxLatLon.inbb(lat, lon):
                continue

            data += "%f %f" % (lat, lon)

            if type(cellValFnt) in [list,tuple]:
                strProperties = ""
                for v,vfnt in enumerate(cellValFnt):
                    val = vfnt(self.data[cell[0]][cell[1]], *args)
                    data += " %f" % val
            else:
                val = cellValFnt(self.data[cell[0]][cell[1]], *args)
                data += " %f" % val

            data += "\n"

        with open(filename, "w") as text_file:
            text_file.write(data)

    def exportSVG(self, filename, cellValFnt, bBoxLatLon = None, *args):
        cells = self.getNonEmptyCells()

        # compute bounding box
        if not bBoxLatLon:
            effectiveBBoxLatLon = BBoxLatLon(1000, -1000, 1000, -1000)
            for cell in cells:
                lat, lon = self.getCellCenterLatLon(cell)
                effectiveBBoxLatLon.minLat = min(effectiveBBoxLatLon.minLat, lat - 0.5*self.resolutionLat)
                effectiveBBoxLatLon.maxLat = max(effectiveBBoxLatLon.maxLat, lat + 0.5*self.resolutionLat)
                effectiveBBoxLatLon.minLon = min(effectiveBBoxLatLon.minLon, lon - 0.5*self.resolutionLon)
                effectiveBBoxLatLon.maxLon = max(effectiveBBoxLatLon.maxLon, lon + 0.5*self.resolutionLon)
        else:
            effectiveBBoxLatLon = bBoxLatLon

        effectiveBBoxLatLonMercator = BBoxLatLon(self.latEquiToMercator(effectiveBBoxLatLon.minLat), self.latEquiToMercator(effectiveBBoxLatLon.maxLat), effectiveBBoxLatLon.minLon, effectiveBBoxLatLon.maxLon)

        # bounding box
        print("[[%f,%f],[%f,%f]]" % (effectiveBBoxLatLon.minLat, effectiveBBoxLatLon.minLon, effectiveBBoxLatLon.maxLat, effectiveBBoxLatLon.maxLon))

        height = (effectiveBBoxLatLon.maxLat-effectiveBBoxLatLon.minLat)
        geojsonHead  = "<svg width=\"%f\" height=\"%f\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\">\n" % (effectiveBBoxLatLon.maxLon-effectiveBBoxLatLon.minLon, height)
        
        geojsonHead += "<defs><g id=\"fufupattern\">"
        for icx in range(4):
            for icy in range(4):
                circleX = icx*0.25*self.resolutionLon
                circleY = icy*0.25*self.resolutionLat
                circleRx = 0.1*self.resolutionLon
                circleRy = 0.7*circleRx
                circleStyle = "fill:#FFFFFF;fill-opacity:0.5;stroke-width:0"
                geojsonHead += "<ellipse cx=\""+ str(circleX) +"\" cy=\""+ str(circleY) +"\" rx=\""+ str(circleRx) +"\" ry=\""+ str(circleRy) +"\" style=\""+ circleStyle +"\" />\n"
        geojsonHead += "</g></defs>"


        geojsonBody = ""

        for cell in cells:
            lat, lon = self.getCellCenterLatLon(cell)
            if bBoxLatLon and not bBoxLatLon.inbb(lat, lon):
                continue

            if type(cellValFnt) in [list,tuple]:
                strProperties = ""
                for v,vfnt in enumerate(cellValFnt):
                    val = vfnt(self.data[cell[0]][cell[1]], *args)
                    break # TODO
            else:
                val = cellValFnt(self.data[cell[0]][cell[1]], *args)

            latMercator0Normalized = (self.latEquiToMercator(lat-0.5*self.resolutionLat) - effectiveBBoxLatLonMercator.minLat) / (effectiveBBoxLatLonMercator.maxLat - effectiveBBoxLatLonMercator.minLat)
            latMercator1Normalized = (self.latEquiToMercator(lat+0.5*self.resolutionLat) - effectiveBBoxLatLonMercator.minLat) / (effectiveBBoxLatLonMercator.maxLat - effectiveBBoxLatLonMercator.minLat)
            latMercator0 = effectiveBBoxLatLon.minLat + latMercator0Normalized * (effectiveBBoxLatLon.maxLat - effectiveBBoxLatLon.minLat)
            latMercator1 = effectiveBBoxLatLon.minLat + latMercator1Normalized * (effectiveBBoxLatLon.maxLat - effectiveBBoxLatLon.minLat)
            heightLat = latMercator1 - latMercator0

            rectX = lon-0.5*self.resolutionLon-effectiveBBoxLatLon.minLon
            rectY = height - (latMercator0-effectiveBBoxLatLon.minLat) - heightLat
            rectWidth  = self.resolutionLon
            rectHeight = heightLat
            rectStyle  = "fill:#"+ valToColor.valToColor(val, valToColor.paraglidableColors[0], valToColor.paraglidableColors[1]) +";stroke-width:0;fill-opacity:0.5"

            geojsonBody += "<rect mask=\"url(#fufupattern)\" shape-rendering=\"crispEdges\" x=\""+ str(rectX) +"\" y=\""+ str(rectY) +"\" width=\""+ str(rectWidth) +"\" height=\""+ str(rectHeight) +"\" style=\""+ rectStyle +"\" />\n"

            geojsonBody += "<use xlink:href=\"#fufupattern\" x=\""+ str(rectX) +"\" y=\""+ str(rectY) +"\" />"
            """
            for icx in range(4):
                for icy in range(4):
                    circleX = icx*0.25*self.resolutionLon + lon-0.5*self.resolutionLon-effectiveBBoxLatLon.minLon
                    circleY = icy*0.25*self.resolutionLat + height - (-0.5*heightLat+latMercator0-effectiveBBoxLatLon.minLat) - heightLat
                    circleRx = 0.05*self.resolutionLon
                    circleRy = 0.7*circleRx
                    circleStyle = "fill:#FFFFFF;fill-opacity:0.5;stroke-width:0"
                    #circleStyle = "fill:url(#image);fill-opacity:1.0;stroke-width:1"
                    
                    geojsonBody += "<ellipse cx=\""+ str(circleX) +"\" cy=\""+ str(circleY) +"\" rx=\""+ str(circleRx) +"\" ry=\""+ str(circleRy) +"\" style=\""+ circleStyle +"\" />\n"
            """
        geojsonFoot = "</svg>"

        with open(filename, "w") as text_file:
            text_file.write(geojsonHead + geojsonBody + geojsonFoot)


    def __str__(self):
        return self.__class__.__name__ +"["+ str(len(self.data)) +"]["+ str(len(self.data[0])) +"]"


#================================================================================
# GridLatLonTime
#================================================================================

# todo: cell Content: dict  day: [data1, data2,...]

class GridLatLonTime(GridLatLon):

    def __init__(self, resolutionLat, resolutionLon, originLat=0.0, originLon=0.0):
        GridLatLon.__init__(self, resolutionLat, resolutionLon, originLat, originLon)

    def getStructure(self):
        return GridLatLonTime(self.resolutionLat, self.resolutionLon, self.originLat, self.originLon)

    def addi(self, iCellLatLon, time, obj):
        GridLatLon.addi(self, iCellLatLon, (time,obj))

    def add(self, lat, lon, time, obj):
        GridLatLon.add(self, lat, lon, (time,obj))

    def getCellDayContentLatLon(self, lat, lon, day):
        iCellLat, iCellLon = self.getCellForLatLon(lat, lon)
        return self.getCellDayContent((iCellLat, iCellLon), day)

    # /!\ The cell content must be sorted by date
    def getCellDayContentLatLonDichotomy(self, lat, lon, day):
        iCellLat, iCellLon = self.getCellForLatLon(lat, lon)
        return self.getCellDayContentDichotomy((iCellLat, iCellLon), day)

    def getCellDayContent(self, iCellLatLon, day):
        cellContent = self.getCellContent(iCellLatLon)
        filteredContent = []
        for d in cellContent:
            if dateutil.parser.parse(d[0]).date() == day:
                filteredContent += [d]
        return filteredContent

    # /!\ The cell content must be sorted by date
    def getCellDayContentDichotomy(self, iCellLatLon, day):
        day = str(day)[0:10]
        cellContent = self.getCellContent(iCellLatLon)
        filteredContent = []
        nb = len(cellContent)

        if nb==0:
            return []

        intervalMin = 0
        intervalMax = nb-1

        while True:
            cur    = int((intervalMax+intervalMin)/2)
            curDay = str(cellContent[cur][0])[0:10]

            if curDay == day:
                break
            elif curDay < day:
                intervalMin = cur+1
            elif curDay > day:
                intervalMax = cur-1

            if intervalMax <= intervalMin or (not 0 <= intervalMin < nb)  or (not 0 <= intervalMax < nb):
                break

        if curDay != day:
            return []


        #ici: curDay == day

        delta = 0
        while cur+delta >= 0 and str(cellContent[cur+delta][0])[0:10] == day:
            delta -= 1

        #ici: cur+delta < 0 || cellContent[cur+delta][0:10] != day

        filteredContent = []
        while cur+delta+1<nb and str(cellContent[cur+delta+1][0])[0:10] == day:
            filteredContent += [cellContent[cur+delta+1]]
            delta += 1

        return filteredContent

    def filterTime(self, vals, bBoxTimeCellValFnt):
        filteredVals = []
        for val in vals:
            if not bBoxTimeCellValFnt[0] or bBoxTimeCellValFnt[0].inbb(val[0]):
                filteredVals += [val[1]]
        return bBoxTimeCellValFnt[1](filteredVals)

    def exportCsv(self, filename, cellValFnt, bBoxLatLon = None, bBoxTime = None, *args):
        return GridLatLon.exportCsv(self, filename, self.filterTime, bBoxLatLon, (bBoxTime, cellValFnt))

    def export_json(self, filename, cellValFnt, bBoxLatLon = None, bBoxTime = None, *args):
        return GridLatLon.export_json(self, filename, self.filterTime, bBoxLatLon, (bBoxTime, cellValFnt))

