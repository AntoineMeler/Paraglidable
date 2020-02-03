import pygrib, tqdm
import numpy as np

# read some cells and params of grid file of known structure
class GribReader:

    gribFile = None
    grbindx  = None

    def __init__(self, gribFile):
        self.gribFile = gribFile
        self.grbIndx  = pygrib.index(gribFile, 'name', 'typeOfLevel', 'level')

    def getInfos(self):
        for grb in pygrib.open(self.gribFile):
            return grb.validDate, grb.distinctLatitudes, grb.distinctLongitudes

    def getGridStructure(self):
        for grb in pygrib.open(self.gribFile):
            #print grb.distinctLatitudes
            #print grb.distinctLongitudes
            #print grb.keys()
            resolutionLat = abs(grb.distinctLatitudes[1]  - grb.distinctLatitudes[0])
            resolutionLon = abs(grb.distinctLongitudes[1] - grb.distinctLongitudes[0])
            originLat = grb.distinctLatitudes[-1] - 0.5*resolutionLat
            originLon = grb.distinctLongitudes[0] - 0.5*resolutionLon
            return originLat, originLon, resolutionLat, resolutionLon

    @staticmethod
    def findClosest(val, vect, latOrLon):
        idx = (np.abs(vect - val)).argmin()
        return idx

    def getValues(self, params, cellsLatLon):
        cells = None
        values = []

        for param in params:
            name, level = param
            for l in level:
                try:
                    selected_grbs = self.grbIndx.select(name=name, typeOfLevel=l[0], level=l[1])
                    assert len(selected_grbs) == 1 # several matching parameters found

                    for grb in selected_grbs:
                        # Assume the grid is the same for each param
                        if not cells and cellsLatLon:

                            #========
                            # TODO: quand j'utiliserai plus de lon dans le training: check lon negatives
                            #
                            #for latLon in cellsLatLon:
                            #    print "lat", latLon[0], grb.distinctLatitudes[self.findClosest(latLon[0], grb.distinctLatitudes, 0)]
                            #    print "lon", latLon[1], grb.distinctLongitudes[self.findClosest(latLon[1], grb.distinctLongitudes, 1)]
                            #========

                            cells = [(self.findClosest(latLon[0], grb.distinctLatitudes, 0), self.findClosest(latLon[1], grb.distinctLongitudes, 1)) for latLon in cellsLatLon]

                        for cell in cells:
                            values += [grb.values[cell[0],cell[1]]]
                except ValueError:
                    pass

        if len(values) != len(params)*len(cellsLatLon):
            print("len(values)", len(values))
            print("len(params)", len(params))
            print("len(cellsLatLon)", len(cellsLatLon))
            return None
        else:
            return values

    def get_values_array(self, params, crops):
        stacks = []

        for param in params:
            name, level = param
            for l in level:
                try:
                    selected_grbs = self.grbIndx.select(name=name, typeOfLevel=l[0], level=l[1])
                    assert len(selected_grbs) == 1 # several matching parameters found

                    for grb in selected_grbs:
                        stack = np.empty(0)
                        for crop in crops:
                            stack = np.concatenate((stack, grb.values[crop[0]:crop[1],crop[2]:crop[3]].flatten()))
                        stacks += [stack]

                except ValueError:
                    pass

        if len(stacks) != len(params):
            print("len(stacks)", len(stacks))
            print("len(params)", len(params))
            return None
        else:
            return np.stack(stacks)

