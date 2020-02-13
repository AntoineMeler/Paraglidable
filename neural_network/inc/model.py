# coding: utf-8

import random, tqdm, numpy as np, math, sys, enum
import tensorflow as tf

################################################################################################
# 
################################################################################################

from inc.utils   import Utils
from inc.verbose import Verbose

################################################################################################
# ModelType, ProblemFormulation, ModelSettings
################################################################################################

class ModelType(enum.Enum):
	CELLS = 0
	SPOTS = 1

class ProblemFormulation(enum.Enum):
	CLASSIFICATION = 0
	REGRESSION     = 1

class ModelSettings:
	optimize_dow = False
	dow_init = [[111383., 107993., 117721., 131987., 154665., 266616., 238255.]] / np.mean([[111383., 107993., 117721., 131987., 154665., 266616., 238255.]])

################################################################################################
# 
################################################################################################

def get_humidity_flyability_block(nb_altitudes, model_content, humidity_dim, name):
	dropout_rate = 0.05

	layers  = [tf.keras.layers.Input((model_content.nbCells(), 3, humidity_dim),  name = "in_rainflyability_rain")]
	layers += [tf.keras.layers.Lambda(lambda x: tf.keras.backend.reshape(x, (-1, 3 * humidity_dim)))]
	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(4, activation='tanh',    name="RainFlyability_1")]
	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(1, activation='sigmoid', name="RainFlyability_2")]
	layers += [tf.keras.layers.Lambda(lambda x: tf.keras.backend.tile(tf.keras.backend.reshape(x,
													 # reshape
													 (-1, model_content.nbCells(), 1)),
													 # tile
													 (1, 1, nb_altitudes)))]

	for l,layer in enumerate(layers):
		result = layer if l==0 else layer(result)
	return tf.keras.models.Model(layers[0], result, name=name)


def get_wind_flyability_block(nb_altitudes, model_content, name):
	dropout_rate = 0.05

	layers  = [tf.keras.layers.Input((model_content.nbCells(), nb_altitudes, 3), name="in_windflyability_wind")]
	layers += [tf.keras.layers.Lambda(lambda x: tf.keras.backend.reshape(x, (-1, 3)))]
	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(8, activation='tanh',    name="WindFlyability_1")]
	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(1, activation='sigmoid', name="WindFlyability_2")]
	layers += [tf.keras.layers.Lambda(lambda x: tf.keras.backend.reshape(x, (-1, model_content.nbCells(), nb_altitudes)))]

	for l,layer in enumerate(layers):
		result = layer if l==0 else layer(result)
	return tf.keras.models.Model(layers[0], result, name=name)


def get_flyability_block(other_dim, humidity_dim, name, disable_dropout=False):
	batch_normalization = True
	dropout_rate = 0.0 if not disable_dropout else 0.

	layers  = [[tf.keras.layers.Input((3,),                name = "in_flyability_wind"),
	            tf.keras.layers.Input((3 * other_dim,),    name = "in_flyability_other"),
	            tf.keras.layers.Input((3 * humidity_dim,), name = "in_flyability_rain")]]
	layers += [tf.keras.layers.Concatenate(name="concatenate_flyability")]

	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(32//2, use_bias=not batch_normalization, name="Flyability_1A")]
	if batch_normalization:
		layers += [tf.keras.layers.BatchNormalization()]
	layers += [tf.keras.layers.Activation("tanh")]

	
	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(16//2, use_bias=not batch_normalization, name="Flyability_1B")]
	if batch_normalization:
		layers += [tf.keras.layers.BatchNormalization()]
	layers += [tf.keras.layers.Activation("tanh")]
	

	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(1, activation='sigmoid', name="Flyability_2")]

	for l,layer in enumerate(layers):
		result = layer if l==0 else layer(result)
	return tf.keras.models.Model(layers[0], result, name=name)


def get_crossability_block(other_dim, humidity_dim, nb_altitudes, wind_dim, model_content, name):
	batch_normalization = True
	dropout_rate = 0.0
	nbH = 3

	layers  = [[tf.keras.layers.Input((model_content.nbCells(), nb_altitudes),                    name = "in_flyability"),
			    tf.keras.layers.Input((model_content.nbCells(), nb_altitudes, nbH),               name = "in_fufu_wind"),
	            tf.keras.layers.Input((model_content.nbCells(),               nbH, other_dim),    name = "in_fufu_other"),
	            tf.keras.layers.Input((model_content.nbCells(),               nbH, humidity_dim), name = "in_fufu_rain")]]
	layers += [tf.keras.layers.Lambda(lambda x: [ # flyability (, nbCells, nbAlt) -> (, nbCells, nbAlt)
												  tf.keras.backend.reshape(x[0], (-1, nb_altitudes)),
												  # wind (, nbCells, nbAlt, nbH) -> (, nbCells, nbAlt*nbH)
												  tf.keras.backend.reshape(x[1], (-1, nb_altitudes*nbH)),
												  # other (, nbCells, nbH, d) -> (, nbCells, nbH*d)
												  tf.keras.backend.reshape(x[2], (-1, nbH*other_dim)),
												  # rain (, nbCells, nbH, d) -> (, nbCells, nbH*d)
												  tf.keras.backend.reshape(x[3], (-1, nbH*humidity_dim)) ])]
	layers += [tf.keras.layers.Concatenate(name="concatenate_fufu", axis=-1)]

	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(32//2, use_bias=not batch_normalization, name="Fufu_1A")]
	if batch_normalization:
		layers += [tf.keras.layers.BatchNormalization()]
	layers += [tf.keras.layers.Activation("tanh")]

	
	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(16//2, use_bias=not batch_normalization, name="Fufu_1B")]
	if batch_normalization:
		layers += [tf.keras.layers.BatchNormalization()]
	layers += [tf.keras.layers.Activation("tanh")]
	

	layers += [tf.keras.layers.Dropout(dropout_rate)]
	layers += [tf.keras.layers.Dense(1, activation='sigmoid', name="Fufu_2")]
	layers += [tf.keras.layers.Lambda(lambda x: tf.keras.backend.tile(tf.keras.backend.reshape(x,
												# reshape
												(-1, model_content.nbCells(), 1)),
												# tile
												(1, 1, nb_altitudes)) )]

	for l,layer in enumerate(layers):
		result = layer if l==0 else layer(result)
	return tf.keras.models.Model(layers[0], result, name=name)



################################################################################################
# get_wind_block_spots
################################################################################################

# Estimates:

# - Wind direction weights: 8
# - Relevant altitude:      1

# Output:

# wind value 06h
# wind value 12h
# wind value 18h

class get_wind_block_spots(tf.keras.layers.Layer):

	nb_hours = 3
	wind_dim = 8

	def __init__(self, nb_spots, **kwargs):

		initial_wind_weight_value = 1.0
		initial_alt_value         = 2.0

		self.nb_spots = nb_spots

		self.initial_weights  = []
		self.initial_weights += [tf.keras.initializers.Constant(value = initial_wind_weight_value * np.ones((nb_spots, get_wind_block_spots.wind_dim)))]
		self.initial_weights += [tf.keras.initializers.Constant(value = initial_alt_value)]

		super(get_wind_block_spots, self).__init__(**kwargs)


	def build(self, input_shape): # input_shape: (?, 5, 3, 8)

		nb_altitudes = input_shape[1]
		nb_hours     = input_shape[2]
		wind_dim     = input_shape[3]

		# specific variable
		self.windWeights = self.add_weight(name        = 'windWeights',
		                                   shape       = (self.nb_spots, wind_dim),
		                                   trainable   = True,
		                                   initializer = self.initial_weights[0])

		self.alt         = self.add_weight(name        = 'alt',
				                           shape       = (self.nb_spots, 1),
				                           trainable   = True,
				                           initializer = self.initial_weights[1],
				                           constraint  = tf.keras.constraints.MinMaxNorm(min_value = 0.0,
				                                                                         max_value = nb_altitudes - 1.0))

		super(get_wind_block_spots, self).build(input_shape)  # Be sure to call this at the end


	def call(self, x): # x (?, nbAltitudes, nbHours, nbWindDirections)

		nb_altitudes = x.shape[1]
		nb_hours     = x.shape[2]
		wind_dim     = x.shape[3]

		x_permuted = tf.keras.backend.permute_dimensions(x, [0, 2, 1, 3]) # (?, nbHours, nbAltitudes, nbWindDirections)
		x_reshaped = tf.keras.backend.reshape(x_permuted, (-1, wind_dim)) # (?, nbAltitudes, nbWindDirections)

		results = []

		# x_permuted (?, 5, 8)
		for s in range(self.nb_spots):
			interpolation_kernel = tf.keras.backend.clip(np.array([range(nb_altitudes)], dtype=np.float) - self.alt[s,:] + 1.0, 0.0, 1.0) - \
			                       tf.keras.backend.clip(np.array([range(nb_altitudes)], dtype=np.float) - self.alt[s,:]      , 0.0, 1.0)

			wind_factor = tf.keras.backend.batch_dot(x_reshaped, tf.keras.backend.reshape(self.windWeights[s,:], (1, wind_dim)), axes=1) # (?, 1)
			wind_factor_each_alt     = tf.keras.backend.reshape(wind_factor, (-1, nb_altitudes)) # (?, 5)
			wind_factor_relevant_alt = tf.keras.backend.batch_dot(wind_factor_each_alt, interpolation_kernel, axes=1) # (?, 1)
			wind_factor_relevant_alt = tf.keras.backend.reshape(wind_factor_relevant_alt, (-1, 3))

			results += [wind_factor_relevant_alt]

		result = tf.keras.backend.stack(results, axis=1) # (?, nb_spots, 3)

		return result


	def compute_output_shape(self, input_shape):
		return (None, self.nb_spots, 3)


################################################################################################
# get_wind_block_cells
################################################################################################


class get_wind_block_cells(tf.keras.layers.Layer):

	def __init__(self, **kwargs):
		super(get_wind_block_cells, self).__init__(**kwargs)


	# inputs
	#   - mountainess: (, nbCells, nbWindAltitudes)
	# 	- wind:        (, nbCells, nbWindAltitudes, nbHours, nbWindDims)
	def build(self, inputs_shape):
		assert isinstance(inputs_shape, list)

		# specific variable
		self.mountainess_factor = self.add_weight(name        = 'mountainess_factor',
		                                          shape       = (1,), # un coeff pour la plaine et un pour la montagne
		                                          trainable   = True,
		                                          initializer = tf.keras.initializers.Constant(value=np.zeros((1,))), dtype=np.float)

		super(get_wind_block_cells, self).build(inputs_shape)  # Be sure to call this at the end



	def call(self, x):
		assert isinstance(x, list)

		mountainess     = x[0]                                                 # (, nbCells, nbWindAltitudes)
		mountainess     = tf.keras.backend.tile(tf.keras.backend.expand_dims(mountainess, -1), (1, 1, 1, 3)) # (, nbCells, nbWindAltitudes, nbHours)
		wind_norm       = tf.keras.backend.sum(x[1], axis=-1)                  # (, nbCells, nbWindAltitudes, nbHours)
		wind_prediction = (1.0 + mountainess*self.mountainess_factor[0]) * wind_norm

		return wind_prediction


	def compute_output_shape(self, inputs_shape):
		assert isinstance(inputs_shape, list)
		return inputs_shape[1][0:-1]


################################################################################################
# get_population_block
################################################################################################


class get_population_block(tf.keras.layers.Layer):

	def __init__(self, problem_formulation, var_date_factor, var_dow_factor, super_resolution, **kwargs):

		self.frozen_date_factor  = not type(var_date_factor).__name__ == "Variable"
		self.frozen_dow_factor   = not type(var_dow_factor).__name__ == "Variable"
		self.problem_formulation = problem_formulation
		self.var_date_factor     = var_date_factor
		self.var_dow_factor      = var_dow_factor
		self.super_resolution    = super_resolution

		super(get_population_block, self).__init__(**kwargs)


	def build(self, inputs_shape):
		assert isinstance(inputs_shape, list)
		shape_prediction, shape_date, shape_dow = inputs_shape

		# specific variable
		self.popu = self.add_weight( name        = 'kernel',
                                     shape       = (shape_prediction[-2]*self.super_resolution*self.super_resolution, shape_prediction[-1]), # (nbCells*super_resolution^2, nbAltitudes)
                                     trainable   = True,
                                     initializer = tf.keras.initializers.Constant(value=0.5),
		                             constraint  = tf.keras.constraints.NonNeg())

		# add trainable variables
		trainable_weights = []
		if not self.frozen_date_factor:
			trainable_weights += [self.var_date_factor]
		if not self.frozen_dow_factor:
			trainable_weights += [self.var_dow_factor]
		if len(trainable_weights) > 0:
			self.trainable_weights.extend(trainable_weights)

		super(get_population_block, self).build(inputs_shape)  # Be sure to call this at the end


	def call(self, x):
		assert isinstance(x, list)
		prediction, date, dow = x

		# I used to force sunday=1. but the convergence is more difficult like that.
		#dow_factor7 = tf.keras.backend.concatenate([self.var_dow_factor6, tf.keras.backend.constant(np.ones((1, 1), dtype=np.float))])  # sunday factor if forced to 1
		dow_factor7 = self.var_dow_factor

		prediction        = tf.keras.backend.repeat_elements(prediction, self.super_resolution*self.super_resolution, 1) # (?, nbCells*super_resolution^2, nbAltitudes)
		popu_reshaped     = tf.keras.backend.reshape(self.popu, (1, self.popu.shape[0], self.popu.shape[1])) # (1, nbCells*super_resolution^2, nbAltitudes)
		tiled_popu        = tf.keras.backend.tile(popu_reshaped, (tf.keras.backend.shape(prediction)[0], 1, 1)) # (?, nbCells*super_resolution^2, nbAltitudes)
		day_factor_vector = (1.0 + self.var_date_factor * date) * tf.keras.backend.batch_dot(dow, dow_factor7, axes=1) # (?, 1)
		day_factor_vector = tf.keras.backend.reshape(day_factor_vector, (tf.keras.backend.shape(day_factor_vector)[0], 1, 1))         # (?, 1, 1)
		day_factor_vector = tf.keras.backend.tile(day_factor_vector, (1, tiled_popu.shape[1], tiled_popu.shape[2]))    # (?, nbCells*super_resolution^2, nbAlts)
		tiled_popu = day_factor_vector * tiled_popu

		if self.problem_formulation == ProblemFormulation.CLASSIFICATION:
			pred_with_popu = tf.keras.backend.switch(tiled_popu > 1.0, (1.0 - (1.0 - prediction)**tf.keras.backend.clip(tiled_popu, 0.0, 100.0)), tiled_popu*prediction)
		else: # REGRESSION
			pred_with_popu = tiled_popu * prediction

		return pred_with_popu


	def compute_output_shape(self, inputs_shape):
		assert isinstance(inputs_shape, list)
		shape_prediction, shape_date, shape_dow = inputs_shape
		return (shape_prediction[0], shape_prediction[1]*self.super_resolution*self.super_resolution, shape_prediction[2])


#=================================================================================
# Extrude other et rain sur toutes les altitudes puis reshape en (?, 3*dataDim)
#
#   input[0]: wind  (?, nbCells, nbWindAltitudes, 3)
#   input[1]: other (?, nbCells,                  3, inputDimOther)
#   input[2]: rain  (?, nbCells,                  3, inputDimRain)
#
def encapsulate_flyability(flyabilityModel, nbCells, nbWindAltitudes_or_nbSpots, inputDimOther, inputDimRain, inputs):

	reshape_in =  tf.keras.layers.Lambda(lambda x: [
		# wind
		tf.keras.backend.reshape(x[0], (-1, 3 * 1)),
		# other
		tf.keras.backend.reshape(tf.keras.backend.tile(tf.keras.backend.reshape(x[1],
			# reshape
			(-1, nbCells, 1, 3, inputDimOther)),
			# tile
			( 1, 1, nbWindAltitudes_or_nbSpots, 1, 1)),
			# reshape
			(-1, 3 * inputDimOther)),
		# rain
		tf.keras.backend.reshape(tf.keras.backend.tile(tf.keras.backend.reshape(x[2],
			# reshape
			(-1, nbCells, 1, 3, inputDimRain)),
			# tile
			( 1, 1, nbWindAltitudes_or_nbSpots, 1, 1)),
			# reshape
			(-1, 3 * inputDimRain))])

	reshape_out = tf.keras.layers.Lambda(lambda x: tf.keras.backend.reshape(x,
		# reshape
		(-1, nbCells, nbWindAltitudes_or_nbSpots)))

	pre = reshape_in(inputs)
	flyabilityPrediction = flyabilityModel(pre)
	return reshape_out(flyabilityPrediction)


#######################################################################################################################################
#######################################################################################################################################
# ModelCells
#######################################################################################################################################
#######################################################################################################################################


class ModelCells:

	@classmethod
	def outputsNames(cls):
		return ["flown 1000",
		        "flown  900",
		        "flown  800",
		        "flown  700",
		        "flown  600",
		        "flown  fufu 1000",
		        "flown  fufu  900",
		        "flown  fufu  800",
		        "flown  fufu  700",
		        "flown  fufu  600",
		        "flown of wind 1000",
		        "flown of wind  900",
		        "flown of wind  800",
		        "flown of wind  700",
		        "flown of wind  600",
		        "flown of rain 1000",
		        "flown of rain  900",
		        "flown of rain  800",
		        "flown of rain  700",
		        "flown of rain  600"]


	@classmethod
	def createNewModel(cls, problem_formulation, model_content, wind_dim, other_dim, humidity_dim, nb_altitudes, initialization):
		Verbose.print_arguments()

		# ==============================================================================================================
		# Shared variables
		# ==============================================================================================================

		var_date_factor = tf.keras.backend.variable(np.array([[1.275]], dtype=np.float), name="var_date_factor")
		if ModelSettings.optimize_dow:
			var_dow_factor  = tf.keras.backend.variable(np.array(ModelSettings.dow_init, dtype=np.float), name="var_dow_factor")
		else:
			var_dow_factor  = tf.keras.backend.constant(np.array(ModelSettings.dow_init, dtype=np.float), name="var_dow_factor")

		# ==============================================================================================================
		# Inputs
		# ==============================================================================================================

		input_date        = tf.keras.layers.Input(shape=(1,),                                                 name="in_date")
		input_dow         = tf.keras.layers.Input(shape=(7,),                                                 name="in_dow")
		input_mountainess = tf.keras.layers.Input(shape=(model_content.nbCells(), nb_altitudes),              name="in_mountainess")
		input_other       = tf.keras.layers.Input(shape=(model_content.nbCells(), 3, other_dim),              name="in_other")
		input_humidity    = tf.keras.layers.Input(shape=(model_content.nbCells(), 3, humidity_dim),           name="in_rain")
		input_wind        = tf.keras.layers.Input(shape=(model_content.nbCells(), nb_altitudes, 3, wind_dim), name="in_wind")

		allInputs = [input_date, input_dow, input_mountainess, input_other, input_humidity, input_wind]

		# ==============================================================================================================
		# Blocks
		# ==============================================================================================================

		wind_block                = get_wind_block_cells(name="wind_block_cells")
		flyability_block          = get_flyability_block(other_dim, humidity_dim, name="flyability_block")
		population_block          = get_population_block(problem_formulation, var_date_factor, var_dow_factor, model_content.super_resolution, name="population_block")
		crossability_block        = get_crossability_block(other_dim, humidity_dim, nb_altitudes, wind_dim, model_content, name="crossability_block")
		wind_flyability_block     = get_wind_flyability_block(nb_altitudes, model_content, name="wind_flyability_block")
		humidity_flyability_block = get_humidity_flyability_block(nb_altitudes, model_content, humidity_dim, name="humidity_flyability_block")

		# ==============================================================================================================
		# Flyability/crossability
		# ==============================================================================================================

		wind_prediction                = wind_block([input_mountainess, input_wind])
		flyability_prediction          = encapsulate_flyability(flyability_block, model_content.nbCells(), nb_altitudes, other_dim, humidity_dim, [wind_prediction, input_other, input_humidity])
		crossability_prediction        = crossability_block([flyability_prediction, wind_prediction, input_other, input_humidity])
		wind_flyability_prediction     = wind_flyability_block(wind_prediction)
		humidity_flyability_prediction = humidity_flyability_block(input_humidity)

		#=========================================================================================
		# Apply population
		#=========================================================================================

		flown_prediction          = population_block([flyability_prediction,          input_date, input_dow])
		crossed_prediction        = population_block([crossability_prediction,        input_date, input_dow])
		wind_flown_prediction     = population_block([wind_flyability_prediction,     input_date, input_dow])
		humidity_flown_prediction = population_block([humidity_flyability_prediction, input_date, input_dow])

		#=========================================================================================
		# Make model
		#=========================================================================================

		return tf.keras.models.Model(allInputs, [flown_prediction, crossed_prediction, wind_flown_prediction, humidity_flown_prediction])


#######################################################################################################################################
#######################################################################################################################################
# Model
#######################################################################################################################################
#######################################################################################################################################


class ModelSpots:

	@classmethod
	def outputsNames(cls):
		return ["flown"]


	@classmethod # Spots
	def createNewModel(cls, problem_formulation, model_content, wind_dim, other_dim, humidity_dim, nb_altitudes, initialization):
		Verbose.print_arguments()

		# Check initialization
		assert(not initialization is None)
		for k in initialization:
			assert(k in ["date_factor", "dow_factor"])
		Verbose.print_text(1, "initialization "+ str(initialization))

		# ==============================================================================================================
		# Shared variables
		# ==============================================================================================================

		# Not trainable
		var_date_factor = tf.keras.backend.constant(value=initialization['date_factor'], name="var_date_factor")
		if ModelSettings.optimize_dow:
			var_dow_factor = tf.keras.backend.constant(value=initialization['dow_factor'], name="var_dow_factor")
		else:
			var_dow_factor = tf.keras.backend.constant(value=ModelSettings.dow_init, name="var_dow_factor")

		# ==============================================================================================================
		# Inputs
		# ==============================================================================================================

		input_date        = tf.keras.layers.Input(shape=(1,),                                                 name="in_date")
		input_dow         = tf.keras.layers.Input(shape=(7,),                                                 name="in_dow")
		input_mountainess = tf.keras.layers.Input(shape=(model_content.nbCells(), nb_altitudes),              name="in_mountainess")
		input_other       = tf.keras.layers.Input(shape=(model_content.nbCells(), 3, other_dim),              name="in_other")
		input_humidity    = tf.keras.layers.Input(shape=(model_content.nbCells(), 3, humidity_dim),           name="in_rain")
		input_wind        = tf.keras.layers.Input(shape=(model_content.nbCells(), nb_altitudes, 3, wind_dim), name="in_wind")

		all_inputs = [input_date, input_dow, input_mountainess, input_other, input_humidity, input_wind]

		# ==============================================================================================================
		# Blocks
		# ==============================================================================================================

		flyabilityModel = get_flyability_block(other_dim, humidity_dim, name="flyability_block", disable_dropout=True)
		flyabilityModel.trainable = False # freeze the block

		# ==============================================================================================================
		# Iterations over cells
		# ==============================================================================================================

		all_outputs = [] # 1 by cell

		for kc,c in enumerate(model_content.cells()):
			nb_spots = len(model_content.spots(c))
			if nb_spots > 0:
				# inputs for this cell
				input_wind_this_cell     = tf.keras.layers.Lambda(lambda x: x[:,kc,...])(input_wind)
				input_other_this_cell    = tf.keras.layers.Lambda(lambda x: x[:,kc,...])(input_other)
				input_humidity_this_cell = tf.keras.layers.Lambda(lambda x: x[:,kc,...])(input_humidity)

				# blocks
				population_block = get_population_block(problem_formulation, var_date_factor, var_dow_factor, 1, name="population__cell_%d"%c)
				wind_block       = get_wind_block_spots(nb_spots, name="wind_block_spots__cell_%d"%c)
				
				# Flyability
				wind_prediction       = wind_block(input_wind_this_cell)
				wind_prediction       = tf.keras.layers.Lambda(lambda x: tf.keras.backend.reshape(x, (-1, 1, nb_spots, 3)))(wind_prediction)
				flyability_prediction = encapsulate_flyability(flyabilityModel, 1, nb_spots, other_dim, humidity_dim, [wind_prediction, input_other_this_cell, input_humidity_this_cell])

				# Apply population
				flown_prediction = population_block([flyability_prediction, input_date, input_dow])
				flown_prediction = tf.keras.layers.Lambda(lambda x: tf.keras.backend.reshape(x, (-1, nb_spots)))(flown_prediction)

				all_outputs += [flown_prediction]


		#=========================================================================================
		# Make model
		#=========================================================================================

		return tf.keras.models.Model(all_inputs, all_outputs)
