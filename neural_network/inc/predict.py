# coding: utf-8

import sys, os
import numpy as np

################################################################################################
#
################################################################################################

from inc.bin_obj        import BinObj
from inc.utils          import Utils
from inc.model          import ModelType, ModelSettings
from inc.trained_model  import TrainedModel, ModelContent
from inc.verbose        import Verbose

# for ForecastAndAnl
from inc.grid_latlon  import GridLatLon
from inc.dataset      import GfsData

################################################################################################
# Predict
################################################################################################


class Predict:

	def __init__(self, models_directory, model_type, problem_formulation):

		self.models_directory = models_directory
		self.model_type       = model_type

		self.wind_dim  = 8 # TODO share parameters
		self.other_dim = 45
		self.humidity_dim = 2
		self.nb_altitudes = 5

		self.trainedModel = TrainedModel(models_directory, problem_formulation)

		self.X_rain  = None
		self.X_other = None
		self.X_wind  = None


	def set_meteo_data(self, meteo_matrix, parameters_vector_all):
		Verbose.print_arguments()

		# Parameters prefixed by hour
		parameters_vector_all_with_hours = [(h,) + p for h in [6, 12, 18] for p in parameters_vector_all]
		meteoParamsOther, meteoParamsWind, meteoParamsPrecipitation = TrainedModel.meteoParams()

		# Params for other and wind
		rainIdx  = [[parameters_vector_all_with_hours.index(pX) for pX in meteoParamsPrecipitation[h]] for h in range(3)]
		otherIdx = [[parameters_vector_all_with_hours.index(pX) for pX in meteoParamsOther[h]]         for h in range(3)]
		windIdx  = [[parameters_vector_all_with_hours.index(pX) for pX in meteoParamsWind[h]]          for h in range(3)]

		self.X_rain  = [                          meteo_matrix[:, rainIdx[h] ]                 for h in range(3)]
		self.X_other = [                          meteo_matrix[:, otherIdx[h]]                 for h in range(3)]
		self.X_wind  = [Utils.convert_wind_matrix(meteo_matrix[:, windIdx[h] ], self.wind_dim) for h in range(3)]

		# Load and apply normalization
		normalization_mean_other, normalization_std_other, normalization_mean_rain, normalization_std_rain = BinObj.load("normalization_%s"%str(self.model_type).split(".")[-1], self.models_directory)

		for h in range(3):
			Utils.apply_normalization(self.X_other[h], normalization_mean_other, normalization_std_other)
			Utils.apply_normalization(self.X_rain[h],  normalization_mean_rain,  normalization_std_rain)


	# @const
	def get_X(self, lines):
		nb_cells        = len(lines)
		prediction_dow  = [0., 0., 0., 0., 0., 0., 1.] # sunday
		prediction_date = 0.5
		mountainess     = 1.0
		other_dim       = self.X_other[0].shape[1]
		humidity_dim    = self.X_rain[0].shape[1]
		nb_altitudes    = self.X_wind[0].shape[1]//self.wind_dim

		assert(other_dim    == self.other_dim)
		assert(humidity_dim == self.humidity_dim)
		assert(nb_altitudes == self.nb_altitudes)

		all_X = []

		# On suppose nb_days=bcp et nbCells=1

		# 0) date (nbCells, )
		all_X += [np.ones((nb_cells,), dtype=np.float)]

		# 1) DOW hot vectors (nbCells, 7)
		all_X += [np.repeat([np.array(prediction_dow, dtype=np.float)], nb_cells, 0)]

		# 2) mountainess (nbCells, 1, nbAltitudes)
		all_X += [mountainess * np.ones((nb_cells, 1, nb_altitudes), dtype=np.float)]

		# 3) other (1, nbCells, nbHours, dimOther)
		other = np.empty((nb_cells, 1, 3, other_dim), dtype=np.float)
		for h in range(3):
			other[:, 0, h, :] = self.X_other[h][lines, :]
		all_X += [other]

		# 4) precipitations (nbCells, 1, nbHours, dimRain)
		rain = np.empty((nb_cells, 1, 3, humidity_dim), dtype=np.float)
		for h in range(3):
			rain[:, 0, h, :] = self.X_rain[h][lines, :]
		all_X += [rain]

		# 5) wind (nbCells, 1, nbAltitudes, nbHours, dimWind)
		wind = np.empty((nb_cells, 1, nb_altitudes, 3, self.wind_dim), dtype=np.float)
		for h in range(3):
			for alt in range(nb_altitudes):
				wind[:, 0, alt, h, :] = self.X_wind[h][lines, alt*self.wind_dim:(alt+1)*self.wind_dim]
		all_X += [wind]

		return all_X


	def __set_trained(self, dictContent):
		Verbose.print_arguments()

		modelContent = ModelContent()
		for kd,d in dictContent.items():
			modelContent.add(kd, d)

		self.trainedModel.new(modelContent, self.wind_dim, self.other_dim, self.humidity_dim, self.nb_altitudes, self.model_type)


	def __get_prediction_population(self):
		# In CLASSIFICATION mode, there is an underdetermination between population values and the flyability definition learned.
		# Also, the DOW coefficient have one dimension of redundancy with the population, for better convergence.
		# Thus, we have to normalize.

		# dow

		if ModelSettings.optimize_dow:
			assert(len(populationWeights) == 3)
			mean_dow = np.mean(np.load(self.models_directory+"/weights/population_dow.npy"))
		else:
			mean_dow = 1. # mean of constant DOW is set to 1 in model.py

		# cells population
		popus = []
		for c in range(20):
			popus += [np.mean(np.load(self.models_directory+"/weights/population_alt_cell_%d.npy"%c))]
		
		return  0.25 #0.6/mean_dow/np.mean(popus) # TODO


	def set_prediction_population(self):
		Verbose.print_arguments()
		prediction_popu = self.__get_prediction_population()
		self.trainedModel.set_population_value(prediction_popu)


	def set_trained_spots(self):
		Verbose.print_arguments()
		self.__set_trained({0: [0]})


	def set_trained_cells(self):
		Verbose.print_arguments()
		self.__set_trained({0: [-1]})


################################################################################################
# ForecastAndAnl
################################################################################################

# common stuff between forecasting and anl
class ForecastAndAnl:

	@staticmethod
	def __jsonBool(val):
		if val:
			return "true"
		else:
			return "false"

	@classmethod
	def generate_tiler_argument_file(	cls, outputFilename, predictionFilename, tilesDir, tilerCacheDir, bordersFilename, minZoom,
										maxZoom, backgroundTilesDir="", drawPngTiles=True, decos="", skippedTiles="",
										generateTranspaVersion=True):
			content = """{
				"predictionFilename":   \"""" + predictionFilename + """\",
				"tilesDir":             \"""" + tilesDir + """/256",
				"drawPngTiles":         """ + cls.__jsonBool(drawPngTiles) + """,
				"minZoom":              """ + str(minZoom) + """,
				"maxZoom":              """ + str(maxZoom) + """,
				"cacheDir":             \"""" + tilerCacheDir + """\",

				"progressFilename":     \"""" + tilesDir + """/progress.txt",
				"bordersFilename":      \"""" + bordersFilename + """\",
				"minBordersZoom":       6,
				"maxBordersZoom":       8,
				"takesOffFilename":     \"""" + decos + """\",
				"backgroundTiles":      \"""" + backgroundTilesDir + """\",

				"skippedTiles":         \"""" + skippedTiles + """\",

				"legendImg1":           "/tmp/legend1.png",
				"legendImg2":           "/tmp/legend2.png",
				"legendImg3":           "/tmp/legend3.png",

				"generateTranspaVersion": """ + cls.__jsonBool(generateTranspaVersion) + """
			}"""
			with open(outputFilename, "w") as file:
				file.write(content)


	################################################################################################
	#
	################################################################################################

	@staticmethod
	def compute_prediction_file_cells(	cells_forecasts,
										prediction_filename_for_tiler,
										distinct_latitudes,
										distinct_longitudes,
										meteo_matrix,
										crops,
										meteo_params,
										grid_desc_predictions,
										export_for_tiler=True):
		Verbose.print_arguments()

		# ======================================================================================
		# Retrieve geopotential height at 12h indices in meteoParams
		#
		# inputs:
		#    - meteoParams
		#    - parameters_geopotential_height
		# outputs:
		#    - geopotential_height_indices
		# ======================================================================================

		geopotential_height_indices = []
		for geopotential_height_param in GfsData().parameters_geopotential_height:
			for kParam, param in enumerate(meteo_params):
				if param == (12,) + geopotential_height_param:
					geopotential_height_indices += [kParam]
					break

		assert (len(geopotential_height_indices) == len(GfsData().parameters_geopotential_height))

		# ======================================================================================
		# Retrieve wind at 12h
		#
		# inputs:
		#    - meteoParams
		#    - parameters_wind
		# outputs:
		#    - wind_indices
		# ======================================================================================

		wind_indices = []
		for wind_param in GfsData().parameters_wind:
			for kParam, param in enumerate(meteo_params):
				if param == (12,) + wind_param:
					wind_indices += [kParam]
					break

		assert (len(wind_indices) == len(GfsData().parameters_wind))

		# ========================================================================
		# Create and fill prediction grid
		#
		# params:
		#    - grid_desc_predictions
		# inputs:
		#    - distinct_latitudes
		#    - distinct_longitudes
		#    - meteo_matrix
		#    - geopotential_height_indices
		#    - predictions
		# outputs:
		#    - prediction_grid
		# ========================================================================

		prediction_grid = GridLatLon(grid_desc_predictions[0], grid_desc_predictions[1], grid_desc_predictions[2], grid_desc_predictions[3])

		p = 0
		for crop in crops:  # number of data rectangles to read in the GRIB grid

			lat_range = (crop[0], crop[1])
			lon_range = (crop[2], crop[3])
			Verbose.print_text(1, "lats: " + str(distinct_latitudes[lat_range[0]]) +" , "+ str(distinct_latitudes[lat_range[1]-1]))
			Verbose.print_text(1, "lons: " + str(distinct_longitudes[lon_range[0]]) +" , "+ str(distinct_longitudes[lon_range[1]-1]))

			for ilat in range(lat_range[0], lat_range[1]):
				for ilon in range(lon_range[0], lon_range[1]):

					predictions_data_sample = ()

					# Add geopential heights (not predicted, simply meteo variables)
					predictions_data_sample += (meteo_matrix[p, geopotential_height_indices[0]],    #  0
												meteo_matrix[p, geopotential_height_indices[1]],    #  1
												meteo_matrix[p, geopotential_height_indices[2]],    #  2
												meteo_matrix[p, geopotential_height_indices[3]],    #  3
												meteo_matrix[p, geopotential_height_indices[4]])    #  4
					predictions_data_sample += (cells_forecasts[0][p,0,0], # flyability at 1000     #  5
												cells_forecasts[0][p,0,1], # flyability at  900     #  6
												cells_forecasts[0][p,0,2], # flyability at  800     #  7
												cells_forecasts[0][p,0,3], # flyability at  700     #  8
												cells_forecasts[0][p,0,4], # flyability at  600     #  9
												np.mean(cells_forecasts[1][p,0,0:5]),# crossability # 10
												cells_forecasts[2][p,0,0], # wind at 1000           # 11
												cells_forecasts[2][p,0,1], # wind at  900           # 12
												cells_forecasts[2][p,0,2], # wind at  800           # 13
												cells_forecasts[2][p,0,3], # wind at  700           # 14
												cells_forecasts[2][p,0,4], # wind at  600           # 15
												np.mean(cells_forecasts[3][p,0,0:5]), # humidity    # 16
												0.0)                       # Attractiveness         # 17
					predictions_data_sample += (meteo_matrix[p, wind_indices[0 + 0]], # U 1000 12h  # 18
												meteo_matrix[p, wind_indices[2 + 0]], # U  900 12h  # 19
												meteo_matrix[p, wind_indices[4 + 0]], # U  800 12h  # 20
												meteo_matrix[p, wind_indices[6 + 0]], # U  700 12h  # 21
												meteo_matrix[p, wind_indices[8 + 0]], # U  600 12h  # 22
												meteo_matrix[p, wind_indices[0 + 1]], # V 1000 12h  # 23
												meteo_matrix[p, wind_indices[2 + 1]], # V  900 12h  # 24
												meteo_matrix[p, wind_indices[4 + 1]], # V  800 12h  # 25
												meteo_matrix[p, wind_indices[6 + 1]], # V  700 12h  # 26
												meteo_matrix[p, wind_indices[8 + 1]]) # V  600 12h  # 27

					# Push the sample
					prediction_grid.add(distinct_latitudes[ilat], distinct_longitudes[ilon], predictions_data_sample)
					p += 1

		# ========================================================================
		# Export predictions for tiler
		#
		# params:
		#    - predictionFilenameForTiler
		# inputs:
		#    - prediction_grid
		# ========================================================================

		accessors = [lambda x, ix=ixVal: sum([xx[ix] for xx in x]) / len(x) for ixVal in range(len(predictions_data_sample))]

		if export_for_tiler:
			prediction_grid.export_data_for_tiler(prediction_filename_for_tiler, accessors)
		else:
			prediction_grid.export_json(prediction_filename_for_tiler, accessors)


	################################################################################################
	#
	################################################################################################

	@staticmethod
	def compute_cells_forecasts(models_directory, problem_formulation, meteo_matrix):
		Verbose.print_arguments()
		predict = Predict(models_directory, ModelType.CELLS, problem_formulation)
		predict.set_meteo_data(meteo_matrix, GfsData().parameters_vector_all)
		predict.set_trained_cells()
		predict.trainedModel.load_all_weights()
		predict.set_prediction_population()
		NN_X = predict.get_X(range(meteo_matrix.shape[0]))
		return predict.trainedModel.model.predict(NN_X)
