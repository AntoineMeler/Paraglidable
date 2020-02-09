# coding: utf-8

import sys, os, tqdm, functools, math, random
import numpy as np
import tensorflow as tf

################################################################################################
# 
################################################################################################

from inc.bin_obj        import BinObj
from inc.utils          import Utils
from inc.model          import ModelType, ProblemFormulation
from inc.trained_model  import TrainedModel, ModelContent
from inc.dataset        import MeteoData, FlightsData, DaysData, SpotsData
from inc.verbose        import Verbose

##########################################################################################
# Train
################################################################################################

class MyTrainingLogger(tf.keras.callbacks.Callback):

	def __init__(self, model_type, log_file=None):
		super().__init__()
		self.iteration = 0
		self.model_type = model_type
		self.log_file = log_file

	@staticmethod
	def strcomp(val, valref):
		ratio = val/valref
		if ratio <= 1.:
			color = "\033[92m"
			sign  = "-"
		else:
			color = "\033[91m"
			sign  = "+"

		return color + "{0:>5}".format(sign+"%d%%"%abs(int(round((ratio-1.)*100.)))) +"\033[0m"

	@staticmethod
	def strval(val, valref=None):
		strv = "\033[93m%.4f\033[0m" % val
		if valref is None:
			return strv
		else:
			return strv + MyTrainingLogger.strcomp(val, valref)

	@staticmethod
	def strarr(arr, arrref=None):
		strres = ""
		for v,val in enumerate(arr):
			if v>0:
				strres += ", "
			strv = "\033[94m%.3f\033[0m" % val
			if arrref is None:
				strres += strv
			else:
				strres += strv + MyTrainingLogger.strcomp(val, arrref[v])
		return strres
	
	def on_epoch_end(self, epoch, logs=None):
		str_it = "% 4d "%self.iteration
		lr = float(tf.keras.backend.get_value(self.model.optimizer.lr))
		str_lr = " lr: %.2e" % lr
		
		if self.model_type==ModelType.CELLS:
			losses = ['population_block_loss', 'population_block_1_loss', 'population_block_2_loss', 'population_block_3_loss']

			str_training_losses = "loss: "+ self.strval(logs['loss']) +" ("+ self.strarr([logs[l] for l in losses]) +")"
			if 'val_loss' in logs:
				str_validation_losses = "val_loss: "+ self.strval(logs['val_loss'], logs['loss']) +" ("+ self.strarr([logs["val_"+l] for l in losses],
																													 [logs[l] for l in losses]) +")"
				print(str_it + str_training_losses +" "+ str_validation_losses + str_lr)
			else:
				print(str_it + str_training_losses + str_lr)

		else:
			str_training_losses = "loss: "+ self.strval(logs['loss'])
			print(str_it + str_training_losses + str_lr)

		# plot 'bin/models/CLASSIFICATION_1.0.0/CELLS.log' using 2 w l smooth bezier, 'bin/models/CLASSIFICATION_1.0.0/CELLS.log' using 3 w l smooth bezier
		if self.log_file is not None:
			with open(self.log_file, "a") as fout:
				str_val_loss = " %.8f" % logs['val_loss'] if 'val_loss' in logs else ""
				fout.write("%d %.8f%s %.4e\n" % (self.iteration, logs['loss'], str_val_loss, lr))

		self.iteration += 1


class Train:

	def __init__(self, models_directory, model_type, problem_formulation):

		self.model_type          = model_type
		self.problem_formulation = problem_formulation

		# Params
		self.wind_dim         = 8
		self.nb_altitudes     = 5
		self.all_cells        = [c for c in range(80)]
		self.models_directory = models_directory

		# model
		self.trained_model = TrainedModel(models_directory, problem_formulation)

		# All the training data
		self.__loadTrainingData()

		# Compute and save normalization at 12h
		normalization_mean_other, normalization_std_other       = Utils.compute_normalization_coeffs(self.X_other[1])
		normalization_mean_humidity, normalization_std_humidity = Utils.compute_normalization_coeffs(self.X_humidity[1])
		BinObj.save([normalization_mean_other, normalization_std_other, normalization_mean_humidity, normalization_std_humidity],
					 "normalization_%s"%str(self.model_type).split(".")[-1], self.models_directory)

		# Apply normalization
		for h in range(3):
			Utils.apply_normalization(self.X_other[h],    normalization_mean_other,    normalization_std_other)
			Utils.apply_normalization(self.X_humidity[h], normalization_mean_humidity, normalization_std_humidity)
			# wind is not normalized

		# Training data for the wanted cells
		self.all_X = None
		self.all_Y = None


	def __loadTrainingData(self):

		# Meteo: load data for chosen params
		meteo_params_other, meteo_params_wind, meteo_params_humidity = TrainedModel.meteoParams()
		meteo_data = MeteoData()
		self.X_other    = [					         meteo_data.getMeteoMatrix(self.all_cells, meteo_params_other[h])                for h in range(3)]
		self.X_wind     = [Utils.convert_wind_matrix(meteo_data.getMeteoMatrix(self.all_cells, meteo_params_wind[h]), self.wind_dim) for h in range(3)]
		self.X_humidity = [                          meteo_data.getMeteoMatrix(self.all_cells, meteo_params_humidity[h])             for h in range(3)]
		assert(self.X_wind[0].shape[-1] == self.wind_dim*self.nb_altitudes)

		# Days
		days_data = DaysData()
		self.X_dow   = days_data.getDow()
		self.X_date  = days_data.getDate()
		self.nb_days = days_data.nb_days

		# Flights
		self.flights_data = FlightsData()
		if self.model_type != ModelType.CELLS:
			self.Y_spots = SpotsData().get_flown_by_spots(self.all_cells) # [cell][spot] -> array of shape (nb_days,)


	# @const
	def __get_X(self, model_content): # The same for the 2 models
		Verbose.print_arguments()

		all_X = []

		# 0) date (nb_days,)
		all_X += [self.X_date]

		# 1) DOW hot vectors (nb_days, 7)
		all_X += [self.X_dow]

		# 2) mountainess (nb_days, nb_cells, nb_altitudes)
		all_X += [np.repeat(np.array([self.flights_data.cellKAltitudeMountainess[c][alt] for c in model_content.cells() for alt in range(self.nb_altitudes)], dtype=np.float).reshape(1, model_content.nbCells(), self.nb_altitudes), self.nb_days, 0)]

		# 3) other (nb_days, nb_cells, nbHours, dimOther)
		all_X += [np.stack([ np.stack([self.X_other[h][[c * self.nb_days + d for d in range(self.nb_days)], :] for c in model_content.cells()], 1) for h in range(3)], 2)]

		# 4) rain (nb_days, nb_cells, nbHours, dimRain)
		all_X += [np.stack([ np.stack([self.X_humidity[h][[c * self.nb_days + d for d in range(self.nb_days)], :] for c in model_content.cells()], 1) for h in range(3)], 2)]

		# 5) wind (nb_days, nb_cells, nb_altitudes, nbHours, dimWind)
		all_X += [np.stack([ np.stack([np.stack([self.X_wind[h][[c * self.nb_days + d for d in range(self.nb_days)], alt * self.wind_dim:(alt + 1) * self.wind_dim] for c in model_content.cells()], 1) for alt in range(self.nb_altitudes)], 2) for h in range(3)], 3)]

		# debug, print shapes
		if False:
			for ix in range(len(all_X)):
				print(str(ix).rjust(3) , all_X[ix].shape)

		return all_X


	# @const
	def __get_Y(self, model_content):
		Verbose.print_arguments()

		if self.model_type == ModelType.CELLS:
			Y = self.flights_data.get_flights_by_altitude_matrix(self.all_cells,
															     self.nb_altitudes,
															     model_content.super_resolution,
															     self.problem_formulation==ProblemFormulation.REGRESSION)

			nb_models = 4
			all_Y = [[] for model in range(nb_models)] # flyability, crossability, wind-flyability, rain-flyability

			for cell in [c * model_content.super_resolution * model_content.super_resolution + sc
			             for c  in model_content.cells()
			             for sc in range(model_content.super_resolution*model_content.super_resolution)]:
				for model in range(nb_models):
					all_Y[model] += [ Y[model][[cell*self.nb_days + d for d in range(self.nb_days)],:] ]

			return [np.stack(all_Y[model], 1) for model in range(nb_models)]

		else: # spots

			all_Y = [] # 1 per cell
			for c in model_content.cells():
				if len(self.Y_spots[c]) > 0:
					all_Y += [np.stack([self.Y_spots[c][s] for s in model_content.spots(c)], 1)]  # Y_spots: [cell][spot] -> array of shape (nb_days,)

			# all_Y[cell] = np array of shape (nb_days, nbSpots)

			return all_Y


	def set_trained(self, cells, super_resolution=1, load_weights=True):
		Verbose.print_arguments()

		model_content = ModelContent()

		if self.model_type == ModelType.CELLS:
			model_content.set_super_resolution(super_resolution)

		for c in cells:
			if self.model_type == ModelType.SPOTS:
				# All the spots of the cells
				model_content.add(c, [s for s in range(len(self.Y_spots[c]))])
			else:
				# All the cell
				model_content.add(c, -1)


		# Maybe the cell has no spots, which will crash at network creation
		if self.model_type == ModelType.SPOTS and model_content.total_nb_spots()==0:
			return False

		#===================================================================
		# Create model and load weights
		#===================================================================

		tf.keras.backend.clear_session() # https://github.com/keras-team/keras/issues/3579

		self.trained_model.new(model_content,
							   wind_dim     = self.wind_dim,
							   other_dim    = self.X_other[0].shape[-1],
							   humidity_dim = self.X_humidity[0].shape[-1],
							   nb_altitudes = self.X_wind[0].shape[-1]//self.wind_dim,
							   model_type   = self.model_type)

		# Re-load shared and specific weights if exists
		if load_weights:
			self.trained_model.load_all_weights()

		#===================================================================
		# Model intputs/outputs
		#===================================================================

		self.all_X = self.__get_X(model_content)
		self.all_Y = self.__get_Y(model_content)

		return True


	# Learning rate scheduler
	@staticmethod
	def schedule_with_params(lr_init=0.01, lr_end=1.e-6, nb_epochs=100):
		def schedule(epoch):
			s = (math.log(lr_init) - math.log(lr_end))/math.log(10.)
			lr = lr_init * 10.**(-float(epoch)/float(max(nb_epochs-1,1)) * s)
			return lr
		return tf.keras.callbacks.LearningRateScheduler(schedule)
 

	def train(self, lr_schedule, use_validation_set=False, train_crossability_only=False):
		Verbose.print_arguments()

		self.trained_model.compile([])  # re-compile for removing metrics
		#self.trained_model.model.summary()

		if self.model_type == ModelType.CELLS:
			if train_crossability_only:
				train.trained_model.freeze_all_but_crossability()
			else:
				train.trained_model.unfreeze_all()

		#===================================================================
		# Training/validation set split
		#===================================================================

		if use_validation_set:
			if False: # random validation set
				validation_split = 0.2
				permutation = np.random.permutation(self.nb_days)
				days_to_use_validation = permutation[0:int(round(self.nb_days*validation_split))]
			else: # non-random and well distributed validation set
				days_to_use_validation = np.array(range(0, self.nb_days, 2))
		else:
			if True: # during process tuning, still check the second optim with validation data
				days_to_use_validation = np.array(range(0, self.nb_days, 6))
			else:
				days_to_use_validation = np.array([])
		days_to_use_training = np.array([s for s in range(self.nb_days) if s not in days_to_use_validation])

		#===================================================================
		# Run training
		#===================================================================

		history = self.trained_model.model.fit(x          = [x[days_to_use_training,...] for x in self.all_X],
											   y          = [y[days_to_use_training,...] for y in self.all_Y],
											   validation_data = ( [x[days_to_use_validation,...] for x in self.all_X],
											   					   [y[days_to_use_validation,...] for y in self.all_Y] ) if days_to_use_validation.size>0 else None,
											   epochs     = lr_schedule[2],
											   batch_size = 32,
											   shuffle    = True,
											   verbose    = 0,
											   callbacks  = [self.schedule_with_params(lr_init   = lr_schedule[0],
																				       lr_end    = lr_schedule[1],
																				       nb_epochs = lr_schedule[2]),
															MyTrainingLogger(self.model_type, self.models_directory +"/"+ str(self.model_type).split(".")[-1] +".log")])

		if 'val_loss' in history.history:
			return np.mean(history.history['val_loss'][-5:])
		else:
			return None

	def evaluate(self, days_to_use=None):

		if days_to_use is None:
			days_to_use = range(self.nb_days)

		Verbose.print_text(1, "[INFO] Evaluation: "+ \
							  str(self.trained_model.model.evaluate(x = [x[days_to_use,...] for x in self.all_X],
										        					y = [y[days_to_use,...] for y in self.all_Y],
											    					verbose = 0)))


	def save(self):
		Verbose.print_arguments()
		self.trained_model.save_all_weights()


########################################################################
# MAIN
########################################################################

if __name__ == "__main__":

	nb_cells = 80
	problem_formulation = ProblemFormulation.CLASSIFICATION

	model_dir = "./bin/models/%s_2.0.0" % str(problem_formulation).split(".")[-1]

	#==========================================================================================
	if True: # 1) Train [weather] [cells population]
	#==========================================================================================

		nb_trainings = 20
		lr_schedules = (0.008, 7.e-4, 55), (0.0025, 4.e-4, 70)
		cur_model_dir = "tmp_trainings/"
		train = Train(model_dir, ModelType.CELLS, problem_formulation)

		Utils.rm_dir(cur_model_dir)

		# Run multiple trainings
		val_losses = []
		for m in range(nb_trainings):
			train.set_trained(range(55), super_resolution=1, load_weights=False)
			val_losses += [train.train(lr_schedules[0], use_validation_set=True)]
			train.save()
			Utils.move_dir(model_dir, cur_model_dir+str(m))
			os.makedirs(model_dir)

		# Keep best training
		best_training = np.argmin(np.array(val_losses))
		Utils.copy_dir(cur_model_dir+str(best_training), model_dir)

		# Re-train best with all samples
		train = Train(model_dir, ModelType.CELLS, problem_formulation)
		train.set_trained(range(55), super_resolution=1, load_weights=True)
		train.train(lr_schedules[1], use_validation_set=False)

		train.save()

	#==========================================================================================
	if True: # 2) Train [spots population], [wind + alti] by cell
	#==========================================================================================

		train = Train(model_dir, ModelType.SPOTS, problem_formulation)

		for c in range(0, nb_cells):
			Verbose.print_text(0, "=================================[ cell %d ]=================================" % c)
			if train.set_trained([c], load_weights=True):
				train.train((0.008, 5.e-6, 110))
				train.save()
			else:
				print("No spot in cell %d"%c)


