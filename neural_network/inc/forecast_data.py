# coding: utf-8

import sys, numpy as np

################################################################################################
#
################################################################################################

from inc.dataset     import GfsData
from inc.utils       import Utils
from inc.grib_reader import GribReader

################################################################################################
# ForecastData
################################################################################################

# Grid info will be read from the first GRIB
g_distinct_latitudes  = np.array([])
g_distinct_longitudes = np.array([])


class ForecastData:


	@staticmethod
	def get_meteo_array_of_day(meteoFiles_6_12_18, parametersVector, crops):

		stacksHours = []

		for h, meteo_file in enumerate(meteoFiles_6_12_18):
			try:
				gr = GribReader(meteo_file)
				stacksHours += [gr.get_values_array(parametersVector, crops)]

			except RuntimeError:
				print("RuntimeError", meteo_file)
				break

		return np.concatenate(stacksHours)


	@staticmethod
	def readWeatherData(meteoFiles, crops):

		global g_distinct_latitudes
		global g_distinct_longitudes

		# ======================================================================================
		# Retrieve grid info
		#
		# inputs:
		#    - meteoFiles[0]
		# outputs:
		#    - g_distinct_latitudes
		#    - g_distinct_longitudes
		# ======================================================================================

		if g_distinct_latitudes.size == 0 or g_distinct_longitudes.size == 0:
			validDate, g_distinct_latitudes, g_distinct_longitudes = GribReader(meteoFiles[0]).getInfos()

			# Convert longitudes
			for i in range(g_distinct_longitudes.shape[0]):
				g_distinct_longitudes[i] = Utils.convert_longitude(g_distinct_longitudes[i])

		# ======================================================================================
		# Read grib files into a single matrix
		#
		# params:
		#    - crops
		# inputs:
		#    - meteoFiles
		#    - parameters_vector_all
		# outputs:
		#    - meteo_matrix
		# ======================================================================================

		meteo_matrix = ForecastData.get_meteo_array_of_day(meteoFiles, GfsData().parameters_vector_all, crops).transpose()

		return g_distinct_latitudes, g_distinct_longitudes, meteo_matrix
