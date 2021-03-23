# coding: utf-8

import os, requests, urllib, re, datetime, sys, signal, shutil
from subprocess import call
import numpy as np

################################################################################################
#
################################################################################################

from inc.bin_obj       import BinObj
from inc.utils         import Utils
from inc.verbose       import Verbose
from inc.predict       import Predict, ForecastAndAnl
from inc.dataset       import SpotsData, Spot, GfsData
from inc.model         import ModelType, ProblemFormulation
from inc.trained_model import ModelContent
from inc.forecast_data import ForecastData

################################################################################################
#
################################################################################################

class Forecast:

	def __init__(self, models_directory, problem_formulation):

		if Forecast.on_the_server():
			root = "/home/antoine/GIT/Paraglidable/"
			self.DEBUG_MODE                    = False
			self.last_forecast_time_file_dir   = "/tmp/lastForecastTime"
			self.downloaded_forecasts_dir      = "/tmp/forecasts"
			self.prediction_filename_for_tiler = "/tmp/predictions.txt"
			self.tiler_arguments_filename      = "/tmp/tilerArguments.json"
			self.tiles_dir                     = "/var/www/html/data/tiles"
			self.tiler_program                 = root+"tiler/Tiler/Tiler"
			self.tiler_cache_dir               = root+"tiler/_cache"
			self.background_tiles_dir          = root+"tiler/background_tiles"
			self.geo_json_borders              = root+"tiler/data/Europe_africa_med_red.geo.json"
			self.skipped_tiles                 = root+"tiler/data/skippedTiles.txt"
			self.min_tiles_zoom                = 5
			self.max_tiles_zoom                = 9
			self.render_tiles                  = True
			self.forced_meteo_files            = None
		elif Forecast.in_docker():
			root = "/workspaces/Paraglidable/"
			self.DEBUG_MODE                    = False
			self.last_forecast_time_file_dir   = "/tmp/lastForecastTime"
			self.downloaded_forecasts_dir      = "/tmp/forecasts"
			self.prediction_filename_for_tiler = "/tmp/predictions.txt"
			self.tiler_arguments_filename      = "/tmp/tilerArguments.json"
			self.tiles_dir                     = root+"www/data/tiles"
			self.tiler_program                 = root+"tiler/Tiler/Tiler"
			self.tiler_cache_dir               = root+"tiler/_cache"
			self.background_tiles_dir          = root+"tiler/background_tiles"
			self.geo_json_borders              = root+"tiler/data/Europe_africa_med_red.geo.json"
			self.skipped_tiles                 = root+"tiler/data/skippedTiles.txt"
			self.min_tiles_zoom                = 5
			self.max_tiles_zoom                = 8
			self.render_tiles                  = True
			self.forced_meteo_files            = None
		else:
			sys.exit(1)

		self.destination_forecast_file = os.path.join(self.downloaded_forecasts_dir, "%s")
		self.problem_formulation       = problem_formulation
		self.grid_desc_predictions     = (0.25, 0.25, -0.125, -0.125)  # can be different from meteo grid
		self.GFS_resolution            = "0p25"
		self.nb_days                   = 10

		# Coordinates of the 2 data rectangles taken into the GRIB file
		# Will fail when the grid will change in the GRIB files
		# TODO use lat/lon bbox and get indices using distinctLatitudes and distinctLongitudes

		# Le crop doit être un peu plus grand que celui du Tiler C++
		# Il faut ajouter les tiles d'elevation aussi
		self.crops = [(93, 274, 0, 140), (93, 274, 1394, 1440)]

		os.makedirs(self.last_forecast_time_file_dir, exist_ok=True)
		os.makedirs(self.downloaded_forecasts_dir, exist_ok=True)

		self.meteoParams = BinObj.load("meteo_params")

		self.models_directory = models_directory

	@staticmethod
	def on_the_server():
		return os.path.isdir("/root") and not os.path.isdir("/workspaces/Paraglidable")

	@staticmethod
	def in_docker():
		return os.path.isdir("/root") and os.path.isdir("/workspaces/Paraglidable")

	@staticmethod
	def __download(url, path):
		Verbose.print_arguments()
		r = requests.get(url, stream=True)

		downloaded_size = 0
		tmpPath = path + ".downloading"
		with open(tmpPath, 'wb') as f:
			for chunk in r.iter_content(chunk_size=None):
				if chunk:
					if downloaded_size // (1024 * 1024) != (downloaded_size + len(chunk)) // (1024 * 1024):
						Verbose.print_text(1, str(round(downloaded_size/(1024.0 * 1024.0),1)) +"Mo", True)
					downloaded_size += len(chunk)
					f.write(chunk)
		os.rename(tmpPath, path)
		Verbose.print_text(1, "")


	@staticmethod
	def get_last_forecast_times(grid):
		#  https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl
		url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_"+ grid +".pl"
		content = urllib.request.urlopen(url).read().decode('utf-8')
		forecast_times = re.findall("\">gfs\\.([0-9]+)</a>", content)

		res = []
		for ft in forecast_times[0:2]:
			url2 = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_"+ grid +".pl?dir=%2Fgfs."+ ft
			content2 = urllib.request.urlopen(url2).read().decode('utf-8')
			forecast_times2 = re.findall("gfs."+ ft +"%2F([0-9]{2})", content2)
			print(ft, forecast_times2)
			for ft2 in forecast_times2:
				res += [ft + ft2]

		return res


	@staticmethod
	def download_forecast(forecastTime, grid, h, forecastHour, path):
		forecastTime = forecastTime[0:4+2+2] +"%2F"+ forecastTime[-2:]
		url = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_"+ grid +".pl?file=gfs.t"+ ("%02d"%forecastHour) +"z.pgrb2."+ grid +".f"+ ("%03d"%h) +"&"+ GfsData().g_grib_url_levels +"&"+ GfsData().g_grib_url_meteovars +"&leftlon=0&rightlon=360&toplat=90&bottomlat=-90&dir=%2Fgfs."+ forecastTime +"%2Fatmos"
		Verbose.print_text(1, url)
		Forecast.__download(url, path)

	# ===========================================================================
	# Progress
	# ===========================================================================

	def set_progress(self, percent, strdate):
		filename = self.tiles_dir+"/"+strdate+"/progress.txt"
		with open(filename, "w") as f:
			f.write(str(percent))

	#===========================================================================
	# check if their is a new forecast since last computation
	#===========================================================================

	def check_need_to_update_forecast(self, valid_date, last_forecast_time):
		last_forecast_time_file = os.path.join(self.last_forecast_time_file_dir, valid_date.strftime('%Y-%m-%d'))
		if os.path.isfile(last_forecast_time_file):
			with open(last_forecast_time_file, "r") as file:
				contentLastForecastTime = file.read()
			if contentLastForecastTime >= last_forecast_time:
				Verbose.print_text(1, "forecast is up-to-date")
				return False # my forecast is up-to-date
		return True

	def save_last_update_time(self, valid_date, last_forecast_time):
		last_forecast_time_file = os.path.join(self.last_forecast_time_file_dir, valid_date.strftime('%Y-%m-%d'))
		# save last update time
		with open(last_forecast_time_file, "w") as file:
			file.write(last_forecast_time)

	#==================================================================
	# clean files
	#==================================================================

	@staticmethod
	def remove_file(path):
		try:
			os.remove(path)
			print("[removed       ]", path)
		except OSError:
			print("[does not exist]", path)

	@staticmethod
	def clean_meteo_files(meteo_files):
		for mf in meteo_files:
			Forecast.remove_file(mf)

	#==================================================================
	#
	#==================================================================

	@staticmethod
	def __check_meteo_files(meteo_files):
		ok = True
		for mf in meteo_files:
			ok = ok and os.path.isfile(mf) and os.path.getsize(mf) > 5000
		if ok:
			Verbose.print_text(1, "[OK   ] Meteo files found")
			return True
		else:
			Verbose.print_text(1, "[WARNING] Meteo files not found")
			return False


	#==================================================================
	# MAIN
	#==================================================================

	def main(self):
		last_forecast_times = Forecast.get_last_forecast_times(self.GFS_resolution)
		Verbose.print_text(1, "last_forecast_times: "+ str(last_forecast_times))

		for last_forecast_time in last_forecast_times[0:4]:

			last_forecast_time_dt = datetime.datetime(int(last_forecast_time[0:4]), int(last_forecast_time[4:6]), int(last_forecast_time[6:8]))
			last_forecast_hour    = int(last_forecast_time[-2:]) # 0, 6, 12, 18
			Verbose.print_text(2, "last_forecast_hour: "+ str(last_forecast_hour))
			Verbose.print_text(2, "last_forecast_time: "+ str(last_forecast_time))

			#==================================================================
			# Update each day
			#==================================================================

			for days in range(self.nb_days):
				day_datetime       = last_forecast_time_dt + datetime.timedelta(days=days)
				strdate            = day_datetime.strftime("%Y-%m-%d")
				tiles_dir_this_day = self.tiles_dir +"/"+ strdate

				#======================================================================================
				# Skip if no need to update
				#======================================================================================

				if not self.check_need_to_update_forecast(day_datetime, last_forecast_time):
					continue

				#======================================================================================
				# Make tiles dir
				#======================================================================================

				os.makedirs(tiles_dir_this_day, exist_ok=True)

				#======================================================================================
				# Download / update next hours grib files
				#======================================================================================

				if self.forced_meteo_files is None:

					meteo_files = []
					l_h = [(hh+24*days-last_forecast_hour) for hh in [6, 12, 18] if (hh+24*days-last_forecast_hour)>=0]
					for kh,h in enumerate(l_h):
						forecast_datetime_with_hours = datetime.datetime(int(last_forecast_time[0:4]), int(last_forecast_time[4:6]), int(last_forecast_time[6:8]), int(last_forecast_time[8:10]))
						valid_datetime = forecast_datetime_with_hours + datetime.timedelta(hours=h)
						meteo_file     = self.destination_forecast_file % valid_datetime.strftime("%Y-%m-%d-%H")

						Verbose.print_text(1, "download "+ meteo_file)

						if not self.DEBUG_MODE or not os.path.exists(meteo_file):
							self.download_forecast(last_forecast_time, self.GFS_resolution, h, last_forecast_hour, meteo_file)

						meteo_files += [meteo_file]

					#======================================================================================
					# Re-create a complete list of 3 files even with those not updated (in the past)
					#
					# params:
					#    - destinationForecastFile
					# input:
					#    - dayDateTime
					# output:
					#    - meteo_files
					#======================================================================================

					meteo_files = [self.destination_forecast_file % (day_datetime+datetime.timedelta(hours=h)).strftime("%Y-%m-%d-%H") for h in [6,12,18]]

					Verbose.print_text(1, str(meteo_files))

				else: # self.forced_meteo_files is not None

					# ======================================================================================
					# Use forced meteo files
					#
					# params:
					#    - forced_meteo_files
					# ======================================================================================

					assert(len(self.forced_meteo_files) == 3)

					meteo_files = ["/tmp/forced_meteo_06", "/tmp/forced_meteo_12", "/tmp/forced_meteo_18"]
					for m in range(len(meteo_files)):
						shutil.copyfile(self.forced_meteo_files[m], meteo_files[m])


				#======================================================================================
				# Skip if meteo files are missing
				#======================================================================================

				if not self.__check_meteo_files(meteo_files):
					if not self.DEBUG_MODE:
						Forecast.clean_meteo_files(meteo_files)
					else:
						for mf in meteo_files:
							if os.path.isfile(mf) and os.path.getsize(mf) <= 5000:
								Forecast.remove_file(mf)
					continue

				#======================================================================================
				# PROGRESS: start computation
				#======================================================================================

				self.set_progress(10, strdate)

				#======================================================================================
				# Read weather data
				#======================================================================================

				distinct_latitudes, distinct_longitudes, meteo_matrix = ForecastData.readWeatherData(meteo_files, self.crops)

				#======================================================================================
				# Compute and generate the predictions file for tiler
				#======================================================================================

				ForecastAndAnl.compute_prediction_file_cells(# predictions
												   ForecastAndAnl.compute_cells_forecasts(self.models_directory, self.problem_formulation, meteo_matrix),
												   # other params
												   self.prediction_filename_for_tiler,
				                                   distinct_latitudes,
				                                   distinct_longitudes,
												   np.copy(meteo_matrix),
												   self.crops,
												   self.meteoParams,
												   self.grid_desc_predictions)

				#======================================================================================
				# Compute spots prediction
				#======================================================================================

				if True:
					self.__compute_spots_forecasts(self.models_directory,
												   self.problem_formulation,
					                               distinct_latitudes,
												   distinct_longitudes,
					                               np.copy(meteo_matrix),
					                               os.path.join(self.tiles_dir, os.path.join(strdate, "spots.json")))

				#======================================================================================
				# Clean files
				#======================================================================================

				if not self.DEBUG_MODE:
					Forecast.clean_meteo_files(meteo_files)

				#========================================================================
				# PROGRESS: end of prediction computation
				#========================================================================

				self.set_progress(20, strdate)

				#========================================================================
				# Render tiles
				#========================================================================

				if self.render_tiles:
					ForecastAndAnl.generate_tiler_argument_file(self.tiler_arguments_filename,
												        self.prediction_filename_for_tiler,
												        tiles_dir_this_day,
												        self.tiler_cache_dir,
												        self.geo_json_borders,
												        self.min_tiles_zoom,
												        self.max_tiles_zoom,
												        self.background_tiles_dir,
												        True,
												        "",
												        self.skipped_tiles,
												        generateTranspaVersion = True)

					call([self.tiler_program, self.tiler_arguments_filename])

				#========================================================================
				# Set last update date
				#========================================================================

				self.save_last_update_time(day_datetime, last_forecast_time)

				#========================================================================
				# PROGRESS: end for this date
				#========================================================================

				self.set_progress(100, strdate)



	def __compute_spots_forecasts(self, models_directory, problem_formulation, lats, lons, meteo_matrix, filename):
		Verbose.print_arguments()

		predict = Predict(models_directory, ModelType.SPOTS, problem_formulation)
		predict.set_meteo_data(meteo_matrix, GfsData().parameters_vector_all)

		#=============================================================
		# depend de GribReader.get_values_array(self, params, crops):
		forecastCellsLine = {}
		line = 0
		for crop in self.crops:
			for iLat in range(crop[0], crop[1]):
				for iLon in range(crop[2], crop[3]):
					forecastCellsLine[(iLat, iLon)] = line
					line += 1

		#=============================================================
		# Compute or load cells_and_spots
		#=============================================================

		filename_cells_and_spots = "Forecast_cellsAndSpots_"+ "_".join([str(crop[d]) for crop in self.crops for d in range(4)])

		if not BinObj.exists(filename_cells_and_spots):
			Verbose.print_text(0, "Generating precomputation file because of new crop, it may crash on the server... To be computed on my computer")
			cells_and_spots = {}
			# find forecast cell for each spot
			# C'est comme le cellsAndSpots de Train sauf que les cellules sont les cells de forecast (32942 cells)
			spots_data = SpotsData()
			spots = spots_data.getSpots(range(80))
			for kc, cell_spots in enumerate(spots):
				for ks, spot in enumerate(cell_spots):
					iCell = (np.abs(lats  - spot.lat).argmin(), np.abs(lons - spot.lon).argmin())
					cellLine = forecastCellsLine[iCell]
					kcks_spot = ((kc, ks), spot.toDict())  # (training cell, ks)
					if not cellLine in cells_and_spots:
						cells_and_spots[cellLine] = [kcks_spot]
					else:
						cells_and_spots[cellLine] += [kcks_spot]
			BinObj.save(cells_and_spots, filename_cells_and_spots)
		else:
			cells_and_spots = BinObj.load(filename_cells_and_spots)

		#=============================================================
		# Create a model with 1 cell of 1 spot
		#=============================================================

		predict.set_trained_spots()

		#=============================================================
		# Compute prediction for each spot, one by one
		#=============================================================

		spots_and_prediction = []
		for kcslst, cslst in enumerate(cells_and_spots.items()):
			meteoLine, spotsLst = cslst
			for cs in spotsLst:
				modelContent = ModelContent()
				modelContent.add(cs[0][0], cs[0][1])
				predict.trainedModel.load_all_weights(modelContent) # TODO do not reload shared weights
				predict.set_prediction_population()
				NN_X = predict.get_X([meteoLine])
				prediction = predict.trainedModel.model.predict(NN_X)[0][0]
				spots_and_prediction += [Spot((cs[1]['name'], cs[1]['lat'], cs[1]['lon']), cs[1]['id'], cs[1]['nbFlights'], prediction)] #[cs[1]]


		#=============================================================
		# Export all results
		#=============================================================

		Forecast.__export_spots_forecasts(spots_and_prediction, filename)


	# TODO: move this in the bin/data files
	@staticmethod
	def __fix_spots_name(name):
		return name.replace("Laut Sodkopf", "Lauf Sodkopf")


	@staticmethod
	def __export_spots_forecasts(spots_and_prediction, filename): #[Spot(name, lat, lon, prediction), ...]
		Verbose.print_arguments()

		content = """	
		{
			"type": "FeatureCollection",
			"features": [
		"""
		sep = ""
		for ks, s in enumerate(spots_and_prediction):
			content += sep + """
						{
							"type": "Feature",
							"geometry": {
											"type": "Point",
											"coordinates": [""" + str(s.lon) + "," + str(s.lat) + """]
										},
							"properties": {
							
											"id": \""""      + str(s.id)   + """\",
											"name": \""""    + Forecast.__fix_spots_name(s.name).replace('"', '\\"')   + """\",
											"nbFlights": """ + str(s.nbFlights)  + """,
											"flyability": """+ str(s.prediction) + """
										}
						}
						"""
			sep = ","
		content += "]}"

		with open(filename, "w") as fout:
			fout.write(content)


##########################################################################################################
# main
##########################################################################################################


if __name__ == "__main__":

	problem_formulation = ProblemFormulation.CLASSIFICATION
	model_dir = "./bin/models/%s_1.0.0" % str(problem_formulation).split(".")[-1]

	#######################################################################
	# Check if script is already running
	#######################################################################

	process = Utils.get_elapsed_time("forecast.py")
	if len(process)>1:
		Verbose.print_text(0, "[WARNING] already running: "+str(process))
		for p in process:
			if p[1] > 4*3600:
				Verbose.print_text(0, "[WARNING] running for more than 3h, killing it !")
				os.kill(p[0], signal.SIGTERM)
			else:
				sys.exit(0)

	#######################################################################
	# RUN
	#######################################################################

	forecast = Forecast(model_dir, problem_formulation)
	forecast.main()
