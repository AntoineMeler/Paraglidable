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
from inc.predict       import Predict, ForecastAndAnl
from inc.dataset       import SpotsData, Spot, GfsData, DaysData, FlightsData
from inc.model         import ModelType, ProblemFormulation
from inc.trained_model import ModelContent
from inc.forecast_data import ForecastData

################################################################################################
#
################################################################################################

if __name__ == "__main__":

	prediction_filename_for_tiler = "prediction_filename_for_tiler"
	tiler_arguments_filename      = "tmp/tilerArguments.json"
	tiler_cache_dir               = "/workspaces/Paraglidable/tiler/_cache"
	tiler_program                 = "/workspaces/Paraglidable/tiler/Tiler/Tiler"
	geo_json_borders              = "/workspaces/Paraglidable/tiler/data/Europe_africa_med_red.geo.json"
	background_tiles_dir          = "/workspaces/Paraglidable/tiler/background_tiles"
	skipped_tiles                 = "/workspaces/Paraglidable/tiler/data/skippedTiles.txt"
	min_tiles_zoom = 5
	max_tiles_zoom = 6

	src_anl_dir = "/Volumes/PARA2/GFS/anl/"

	flightsData = FlightsData()
	meteo_days = DaysData().meteo_days

	for kd,day in enumerate(meteo_days):
		tiles_dir_this_day   = "../www/data/tiles_anl/"+ day.strftime("%Y/%Y-%m-%d")
		flights_dir_this_day = "../www/data/flights_anl/"+ day.strftime("%Y/%Y-%m-%d")
		nb_tiles = len(glob.glob(tiles_dir_this_day+"/256/*/*/*.png"))

		if False and nb_tiles != 118: # already computed

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

			ForecastAndAnl.compute_prediction_file_cells(# predictions
												ForecastAndAnl.compute_cells_forecasts(models_directory, problem_formulation, meteo_matrix),
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

			ForecastAndAnl.generate_tiler_argument_file(	tiler_arguments_filename,
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

		json_content = "{\"flights\":"+ str(flights).replace("(", "[").replace(")", "]") +"}"
		os.makedirs(flights_dir_this_day, exist_ok=True)
		with open(flights_dir_this_day+"/flights.json", "w") as fout:
			fout.write(json_content)
		print("\n\n")
		print(json_content)
		print("\n\n")
