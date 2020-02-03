# coding: utf-8

################################################################################################
#
################################################################################################

import pygrib, sys, numpy as np

################################################################################################
#
################################################################################################

class Grib:

	def __init__(self, gribFile):
		for grb in pygrib.open(gribFile):
			self.distinctLatitudes  =                        grb.distinctLatitudes
			self.distinctLongitudes = Grib.convert_longitudes(grb.distinctLongitudes)


	def getCoordinates(self):
		return self.distinctLatitudes, self.distinctLongitudes


	@staticmethod
	def convert_longitudes(lon):
		return lon - 360.0*(lon > 180.0).astype(float)


	def getCell(self, lat, lon):
		iLat = np.abs(self.distinctLatitudes  - lat).argmin()
		iLon = np.abs(self.distinctLongitudes - lon).argmin()
		return (iLat, iLon)
