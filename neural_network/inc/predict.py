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
		
		return 0.6/mean_dow/np.mean(popus) # TODO


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

