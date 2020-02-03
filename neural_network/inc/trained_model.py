# coding: utf-8

import os, sys, numpy as np
import tensorflow as tf

################################################################################################
# 
################################################################################################

from inc.model    import ModelCells, ModelSpots, ModelType, ProblemFormulation, ModelSettings
from inc.utils    import Utils
from inc.verbose  import Verbose
from inc.dataset  import GfsData

################################################################################################
# ModelContent
################################################################################################


class ModelContent:

	def __init__(self):
		self.cellsAndSpots = {}
		self.super_resolution = 1

	def __str__(self):
		return str(self.cellsAndSpots)

	def __repr__(self):
		return self.__str__()


	def set_super_resolution(self, super_resolution):
		self.super_resolution = super_resolution

	def add(self, cell, spots):

		if not type(spots) == list:
			spots = [spots]

		if not cell in self.cellsAndSpots:
			self.cellsAndSpots[cell] = []

		self.cellsAndSpots[cell] += spots


	def cells(self):
		return sorted(self.cellsAndSpots.keys())

	def nbCells(self):
		return len(self.cellsAndSpots)


	def spots(self, cell): # access from cell
		return self.cellsAndSpots[cell]

	def spots_at(self, kCell): # access from cell idx
		return self.cellsAndSpots[self.cells()[kCell]]

	def nbSpots(self, cell): # access from cell
		return len(self.cellsAndSpots[cell])

	def nbSpots_at(self, kCell): # access from cell idx
		return len(self.cellsAndSpots[self.cells()[kCell]])

	def total_nb_spots(self):
		return sum([self.nbSpots(cell) for cell in self.cells()])


	def sameStructure(self, otherModelContent):
		if self.nbCells() != otherModelContent.nbCells():
			return False
		for kc in range(self.nbCells()):
			if self.nbSpots_at(kc) != otherModelContent.nbSpots_at(kc):
				return False
		return True

################################################################################################
# TrainedModel
################################################################################################


class TrainedModel:

	def __init__(self, models_directory, problem_formulation):

		self.models_directory = models_directory
		self.problem_formulation = problem_formulation
		self.modelClass      = None
		self.model           = None
		self.modelContent    = None
		self.nbWindAltitudes = None

		self.other_spots_weights_loaded = False

	def dirLayerWeights(self):
		return os.path.join(self.models_directory, "weights")

	def filesLayerWeights(self, layerName):

		if type(layerName) == list:
			last = layerName[-1]
		else:
			last = layerName

		if type(last) is tuple:
			name = last[0]
		else:
			name = last

		file = os.path.join(self.dirLayerWeights(), name)

		return file


	@staticmethod
	def meteoParams():
		meteoParamsPrecipitation = [[(h,) + p for p in GfsData().parameters_humidity] for h in [6, 12, 18]]
		meteoParamsOther         = [[(h,) + p for p in GfsData().parameters_other]    for h in [6, 12, 18]]
		meteoParamsWind          = [[(h,) + p for p in GfsData().parameters_wind]     for h in [6, 12, 18]]
		return meteoParamsOther, meteoParamsWind, meteoParamsPrecipitation


	#==============================================================================
	# Compile
	#==============================================================================

	def compile(self, metrics=[]):
		Verbose.print_arguments()

		if self.problem_formulation == ProblemFormulation.CLASSIFICATION:
			self.model.compile(optimizer = tf.keras.optimizers.Adam(lr=0.01),
							   loss      = 'binary_crossentropy',
							   metrics   = ["accuracy"])
		else: # REGRESSION
			self.model.compile(optimizer = tf.keras.optimizers.Adam(lr=0.01),
							   loss      = 'mean_absolute_error',
							   metrics   = [])

	#==============================================================================
	# IO complete model
	#==============================================================================


	def new(self, model_content, wind_dim, other_dim, humidity_dim, nb_altitudes, model_type):
		Verbose.print_arguments()

		if model_type == ModelType.CELLS:
			self.modelClass = ModelCells
			initialization = None
		else:
			self.modelClass = ModelSpots
			initialization = {}
			initialization['date_factor'] = np.load(self.filesLayerWeights("population_date")+".npy")
			if ModelSettings.optimize_dow:
				initialization['dow_factor'] = np.load(self.filesLayerWeights("population_dow")+".npy")

		self.model = self.modelClass.createNewModel(self.problem_formulation, model_content, wind_dim, other_dim, humidity_dim, nb_altitudes, initialization)
		self.modelContent = model_content
		self.nbWindAltitudes = nb_altitudes

	#==============================================================================
	#
	#==============================================================================

	def freeze_all_but_crossability(self):
		for layer in self.model.layers:
			if not layer.name == "crossability_block" and not layer.__class__.__name__ == "InputLayer":
				layer.trainable = False
				Verbose.print_text(1, "[INFO] "+ layer.name.ljust(26) +" set to non-trainable")

	def unfreeze_all(self):
		for layer in self.model.layers:
			if not layer.__class__.__name__ == "InputLayer":
				layer.trainable = True
				#Verbose.print_text(1, "[INFO] "+ layer.name.ljust(26) +" set to trainable")

	#==============================================================================
	#
	#==============================================================================


	def set_population_value(self, popuValue):
		Verbose.print_arguments()

		for layer in self.model.layers:
			if layer.name.startswith("population"):
				Verbose.print_text(1, "[INFO] Setting population value %f in layer '%s'" % (popuValue, layer.name))
				populationWeights = layer.get_weights()
				populationWeights[-1][:, :] = popuValue
				layer.set_weights(populationWeights)


	#==============================================================================
	# IO Both shared and specific shortcuts
	#==============================================================================


	def save_all_weights(self):
		Verbose.print_arguments()

		if self.modelClass == ModelCells:

			os.makedirs(self.dirLayerWeights(), exist_ok=True)

			# shared
			for layer in ["flyability_block", "crossability_block", "wind_block_cells", "wind_flyability_block", "humidity_flyability_block"]:
				arrs = self.model.get_layer(layer).get_weights()
				for kArr,arr in enumerate(arrs):
					np.save(self.filesLayerWeights(layer+"_%d"%kArr), arr)

			# population
			populationWeights = self.model.get_layer("population_block").get_weights()

			np.save(self.filesLayerWeights("population_date"), populationWeights[0]) # date factor
			if ModelSettings.optimize_dow:
				assert(len(populationWeights) == 3)
				np.save(self.filesLayerWeights("population_dow"),  populationWeights[1]) # DOW factor
			else:
				assert(len(populationWeights) == 2)

			# specific
			for c,cell in enumerate(self.modelContent.cells()):
				for sr in range(self.modelContent.super_resolution*self.modelContent.super_resolution):
					c_sr    = c   * self.modelContent.super_resolution*self.modelContent.super_resolution + sr
					cell_sr = cell* self.modelContent.super_resolution*self.modelContent.super_resolution + sr
					np.save(self.filesLayerWeights("population_alt_cell_%d"%cell_sr), populationWeights[-1][c_sr,:]) # population at each altitude
		else:

			for c, cell in enumerate(self.modelContent.cells()):
				if self.modelContent.nbSpots(cell) > 0:
					np.save(self.filesLayerWeights("population_0_spots__cell_%d"%cell), self.model.get_layer("population__cell_%d"%cell).get_weights()[0])

					windWeights = self.model.get_layer("wind_block_spots__cell_%d" % cell).get_weights()
					np.save(self.filesLayerWeights("wind_block_spots_0__cell_%d" % cell), windWeights[0])
					np.save(self.filesLayerWeights("wind_block_spots_1__cell_%d" % cell), windWeights[1])


	def load_all_weights(self, modelContentToLoad=None, wind_bias=-1.0):
		Verbose.print_arguments()

		# self.modelContent est le contenu du network, il définit le nom des layers
		# modelContentToLoad définit le nom des fichiers de weights à utiliser
		if modelContentToLoad is None:
			modelContentToLoad = self.modelContent
		else:
			assert(self.modelContent.sameStructure(modelContentToLoad))


		if self.modelClass == ModelCells:
			layers = ["flyability_block", "crossability_block", "wind_block_cells", "wind_flyability_block", "humidity_flyability_block"]
		else:
			layers = ["flyability_block"]

		#===============================================================================================================
		# shared
		#===============================================================================================================

		# Flyability, Fufu, Wind, WindFlyability, RainFlyability
		for layer in layers:
			try:
				arrs = self.model.get_layer(layer).get_weights()
				for kArr,arr in enumerate(arrs):
					arr = np.load(self.filesLayerWeights(layer+"_%d"%kArr) +".npy")
					if wind_bias > 0.0 and layer == "wind_block_cells":
						arr = wind_bias * arr
					arrs[kArr] = arr
				self.model.get_layer(layer).set_weights(arrs)
			except:
				pass

		if self.modelClass == ModelCells:
			populationWeights = self.model.get_layer("population_block").get_weights() #[(1,), (7,), (5,)]

			try:
				populationWeights[0] = np.load(self.filesLayerWeights("population_date") +".npy") # date factor (1,)
				if ModelSettings.optimize_dow:
					assert(len(populationWeights) == 3)
					populationWeights[1] = np.load(self.filesLayerWeights("population_dow") +".npy")  # DOW factor  (7,)
				else:
					assert(len(populationWeights) == 2)
			except:
				Verbose.print_text(1, "[ERROR] Could not load weights population_date population_dow")
				raise

		# ===============================================================================================================
		# specific
		# ===============================================================================================================

		if self.modelClass == ModelCells:
			for c,cell in enumerate(self.modelContent.cells()): # TODO super_resolution
				for sr in range(self.modelContent.super_resolution*self.modelContent.super_resolution):
					c_sr    = c   * self.modelContent.super_resolution*self.modelContent.super_resolution + sr
					cell_sr = cell* self.modelContent.super_resolution*self.modelContent.super_resolution + sr
					try:
						populationWeights[-1][c_sr,:] = np.load(self.filesLayerWeights("population_alt_cell_%d"%cell_sr) +".npy") # population at each altitude
					except:
						Verbose.print_text(1, "[ERROR] Could not load weights for population cell %d"% cell_sr)
						raise

			self.model.get_layer("population_block").set_weights(populationWeights)

		else:
			Verbose.print_text(1, "modelContent      :"+ str(self.modelContent))
			Verbose.print_text(1, "modelContentToLoad:"+ str(modelContentToLoad))

			for c, cell in enumerate(self.modelContent.cells()):
				cellToLoad  = modelContentToLoad.cells()[c]
				spotsToLoad = modelContentToLoad.spots(cellToLoad)

				try:
					self.model.get_layer("population__cell_%d"%cell).set_weights([np.load(self.filesLayerWeights("population_0_spots__cell_%d"%cellToLoad) +".npy")])
				except:
					Verbose.print_text(1, "[WARNING] Could not load weights for "+ ("population__cell_%d"%cell))

				try:
					# load weights for all spots
					WindSpots_cell_0 = np.load(self.filesLayerWeights("wind_block_spots_0__cell_%d"%cellToLoad) +".npy") # shape (nbSpots, nbWindDim)
					WindSpots_cell_1 = np.load(self.filesLayerWeights("wind_block_spots_1__cell_%d"%cellToLoad) +".npy") # shape (      1, nbWindDim)

					# keep only spots of modelContent
					WindSpots_cell_0 = WindSpots_cell_0[spotsToLoad,:]
					WindSpots_cell_1 = WindSpots_cell_1[spotsToLoad,:]

					self.model.get_layer("wind_block_spots__cell_%d"%cell).set_weights([WindSpots_cell_0, WindSpots_cell_1])
				except:
					Verbose.print_text(1, "[WARNING] Could not load weights for " + ("wind_block_spots__cell_%d"% cell))
