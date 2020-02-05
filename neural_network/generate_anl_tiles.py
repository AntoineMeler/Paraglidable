# coding: utf-8

import os, requests, urllib, re, datetime, sys, signal, shutil, glob
from subprocess import call
import numpy as np

################################################################################################
#
################################################################################################

from inc.bin_obj       import BinObj
from inc.grid_latlon   import GridLatLon, BBoxLatLon
from inc.utils         import Utils
from inc.verbose       import Verbose
from inc.predict       import Predict
from inc.dataset       import SpotsData, Spot, GfsData, DaysData, FlightsData
from inc.model         import ModelType, ProblemFormulation
from inc.trained_model import ModelContent
from inc.forecast_data import ForecastData


################################################################################################
#
################################################################################################

def compute_cells_forecasts(models_directory, problem_formulation, meteo_matrix):
	Verbose.print_arguments()
	predict = Predict(models_directory, ModelType.CELLS, problem_formulation)
	predict.set_meteo_data(meteo_matrix, GfsData().parameters_vector_all)
	predict.set_trained_cells()
	predict.trainedModel.load_all_weights()
	predict.set_prediction_population()
	NN_X = predict.get_X(range(meteo_matrix.shape[0]))
	return predict.trainedModel.model.predict(NN_X)

################################################################################################
#
################################################################################################

def compute_prediction_file_cells(cells_forecasts,
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

def jsonBool(val):
	if val:
		return "true"
	else:
		return "false"

def generate_tiler_argument_file(outputFilename, predictionFilename, tilesDir, tilerCacheDir, bordersFilename, minZoom,
	                                   maxZoom, backgroundTilesDir="", drawPngTiles=True, decos="", skippedTiles="",
	                                   generateTranspaVersion=True):
		content = """{
	        "predictionFilename":   \"""" + predictionFilename + """\",
	        "tilesDir":             \"""" + tilesDir + """/256",
	        "drawPngTiles":         """ + jsonBool(drawPngTiles) + """,
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

	        "generateTranspaVersion": """ + jsonBool(generateTranspaVersion) + """
	    }"""
		with open(outputFilename, "w") as file:
			file.write(content)

################################################################################################
#
################################################################################################

if __name__ == "__main__":

	prediction_filename_for_tiler = "prediction_filename_for_tiler"
	tiler_arguments_filename = "tmp/tilerArguments.json"
	tiler_cache_dir          = "/workspaces/Paraglidable/tiler/_cache"
	tiler_program            = "/workspaces/Paraglidable/tiler/Tiler/Tiler"
	geo_json_borders         = "/workspaces/Paraglidable/tiler/data/Europe_africa_med_red.geo.json"
	background_tiles_dir     = "/workspaces/Paraglidable/tiler/background_tiles"
	skipped_tiles            = "/workspaces/Paraglidable/tiler/data/skippedTiles.txt"
	min_tiles_zoom = 5
	max_tiles_zoom = 6

	src_anl_dir = "/Volumes/PARA2/GFS/anl/"

	flightsData = FlightsData()
	meteo_days = DaysData().meteo_days

	for kd,day in enumerate(meteo_days):
		tiles_dir_this_day  = "../www/data/tiles_anl/"+ day.strftime("%Y/%Y-%m-%d")
		nb_tiles = len(glob.glob(tiles_dir_this_day+"/256/*/*/*.png"))

		if nb_tiles != 118: # already computed

			meteo_files = [[f for f in glob.glob(src_anl_dir+day.strftime("%Y-%m/")+day.strftime("gfsanl_3_%Y%m%d_")+("%02d00"%h)+"*.grb*") if ".params" not in f][0] for h in [6,12,18]]

			#print(meteo_files, tiles_dir_this_day)
			#continue

			problem_formulation = ProblemFormulation.CLASSIFICATION
			models_directory = "bin/models/CLASSIFICATION_1.0.0/"
			meteoParams = BinObj.load("meteo_params")
			grid_desc_predictions = (1.0, 1.0, -0.5, -0.5)  # can be different from meteo grid
			crops = [(93//4, 274//4, 0, 136//4), (93//4, 274//4, 1394//4, 1440//4)]

			#======================================================================================
			# Read weather data
			#======================================================================================

			distinct_latitudes, distinct_longitudes, meteo_matrix = ForecastData.readWeatherData(meteo_files, crops)

			#======================================================================================
			# Compute and generate the predictions file for tiler
			#======================================================================================

			compute_prediction_file_cells(		# predictions
												compute_cells_forecasts(models_directory, problem_formulation, meteo_matrix),
												# other params
												prediction_filename_for_tiler,
												distinct_latitudes,
												distinct_longitudes,
												np.copy(meteo_matrix),
												crops,
												meteoParams,
												grid_desc_predictions)

			#========================================================================
			# Render tiles
			#========================================================================

			generate_tiler_argument_file(	tiler_arguments_filename,
											prediction_filename_for_tiler,
											tiles_dir_this_day,
											tiler_cache_dir,
											geo_json_borders,
											min_tiles_zoom,
											max_tiles_zoom,
											background_tiles_dir,
											True,
											"",
											skipped_tiles,
											generateTranspaVersion = True)

			call([tiler_program, tiler_arguments_filename])


		#========================================================================
		# Flights
		#========================================================================

		nb_cells = len(flightsData.flights_by_cell_day) // len(meteo_days)
		assert(nb_cells == 97)
		flights = [(f[1][3], f[1][4], f[1][0]) for cd in flightsData.flights_by_cell_day[kd*nb_cells:(kd+1)*nb_cells] for f in cd]
		print("flights", flights)
