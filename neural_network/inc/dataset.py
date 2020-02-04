# coding: utf-8

import sys, tqdm, copy, re, struct
import numpy as np

################################################################################################
#
################################################################################################

from inc.bin_obj     import BinObj
from inc.verbose     import Verbose
from inc.tiles_maths import TilesMaths

################################################################################################
# bin/data files description
################################################################################################

# meteo_days                [kDay  in range(  3281)]                   -> datetime.date
# meteo_params              [kp    in range(   195)]                   -> (hour, 'str_param', [level])
# meteo_content_by_cell_day [k     in range(318257)]                   -> np.array (195,)
# sorted_cells              [kCell in range(    97)]                   -> (row, col)
# sorted_cells_latlon       [kCell in range(    97)]                   -> (lat, lon)
# mountainess_by_cell_alt   [k     in range(    97)][kAlt in range(5)] -> mountainess in [0, 1]
# flights_by_cell_day       [kCell in range(318257)]                   -> [('yyyy-mm-dd hh:mm:ss', (score, alt, plaf, lat, lon, takeoff_alt, mountainess)), ...]

# spots                     [k     in range(  9966)]                      -> ('name', lat, lon)
# spots_merged              [k     in range(  8342)]                      -> ('name', lat, lon)
# flights_by_spot           [k     in range(  8342)]                      -> [('yyyy-mm-dd hh:mm:ss', (score, alt, 0.0, lat, lon)), ...]
# spots_by_cell             [k     in range(    97)]                      -> [kSpot1, kSpot2, ...]
# flights_by_cell_day_spot  [k     in range(    97)][kDay in range(3281)] -> {kSpot: [('yyyy-mm-dd hh:mm:ss', (score, None, 1173.0, lat, lon)), ...], ...}

################################################################################################
# Dataset
################################################################################################


class Data():

	@staticmethod
	def get_lines(cells, nb_cells, nb_days):
		return [d*nb_cells+c for c in cells for d in range(nb_days)]


#===================================================================================================
# DatasetParams
#===================================================================================================

# light class that does not load all the data but just get some params

class DatasetParams:

	def __init__(self):

		self.nb_days  = len(BinObj.load("meteo_days"))
		self.nb_cells = len(BinObj.load("sorted_cells")) # [kCell] -> (row, col)


#===================================================================================================
# GfsData
#===================================================================================================


class GfsData:

	@staticmethod
	def __create_parameters_vector(names):
		parametersVector = []
		for name in names:
			for level in name[1]:
				parametersVector += [(name[0], level)]
		return parametersVector


	def __init__(self):

		################################################################################################
		#
		################################################################################################

		self.g_grib_url_meteovars = ""
		self.g_grib_url_meteovars += "var_VVEL=on" + "&"
		self.g_grib_url_meteovars += "var_ABSV=on" + "&"
		self.g_grib_url_meteovars += "var_CWAT=on" + "&"
		self.g_grib_url_meteovars += "var_HGT=on" + "&"
		self.g_grib_url_meteovars += "var_PWAT=on" + "&"
		self.g_grib_url_meteovars += "var_RH=on" + "&"
		self.g_grib_url_meteovars += "var_TMP=on" + "&"
		self.g_grib_url_meteovars += "var_UGRD=on" + "&"
		self.g_grib_url_meteovars += "var_VGRD=on"

		self.g_grib_url_levels = ""
		self.g_grib_url_levels += "lev_200_mb=on" + "&"
		self.g_grib_url_levels += "lev_300_mb=on" + "&"
		self.g_grib_url_levels += "lev_400_mb=on" + "&"
		self.g_grib_url_levels += "lev_500_mb=on" + "&"
		self.g_grib_url_levels += "lev_600_mb=on" + "&"
		self.g_grib_url_levels += "lev_700_mb=on" + "&"
		self.g_grib_url_levels += "lev_800_mb=on" + "&"
		self.g_grib_url_levels += "lev_900_mb=on" + "&"
		self.g_grib_url_levels += "lev_1000_mb=on" + "&"
		self.g_grib_url_levels += "lev_entire_atmosphere=on" + "&"
		self.g_grib_url_levels += "lev_entire_atmosphere_%5C%28considered_as_a_single_layer%5C%29=on"

		################################################################################################
		# parameters_vector_all
		################################################################################################

		entireAtmosphere = [[('entireAtmosphere', 0), ('unknown', 0)]]

		levelsAll = [[('isobaricInhPa', 1000)],
		             [('isobaricInhPa', 900)],
		             [('isobaricInhPa', 800)],
		             [('isobaricInhPa', 700)],  # 3000m
		             [('isobaricInhPa', 600)],
		             [('isobaricInhPa', 500)],  # 5600m
		             [('isobaricInhPa', 400)],
		             [('isobaricInhPa', 300)],
		             [('isobaricInhPa', 200)]]

		levels600 = [[('isobaricInhPa', 1000)],
		             [('isobaricInhPa', 900)],
		             [('isobaricInhPa', 800)],
		             [('isobaricInhPa', 700)],  # 3000m
		             [('isobaricInhPa', 600)]]

		namesAll = [('Precipitable water', entireAtmosphere),  # PWAT
		            ('Cloud water', entireAtmosphere),  # CWAT
		            ('Vertical velocity', levelsAll),  # VVEL ?
		            ('Geopotential Height', levelsAll),  # HGT
		            ('Absolute vorticity', levelsAll),  # ABSV
		            ('Temperature', levelsAll),  # TMP
		            ('Relative humidity', levelsAll),  # RH
		            ('U component of wind', levelsAll),  # UGRD
		            ('V component of wind', levelsAll)]  # VGRD

		################################################################################################
		#
		################################################################################################

		self.parameters_vector_all          = self.__create_parameters_vector(namesAll)
		self.parameters_geopotential_height = self.__create_parameters_vector([('Geopotential Height', levels600)])
		self.parameters_wind                = self.__create_parameters_vector([(direction + ' component of wind', [lev])
																			   for lev in levels600 for direction in ["U", "V"]])
		self.parameters_humidity            = self.__create_parameters_vector([('Precipitable water', entireAtmosphere),  # PWAT
		                                                                       ('Cloud water',        entireAtmosphere)]) # CWAT
		self.parameters_other               = self.__create_parameters_vector([('Vertical velocity',   levelsAll),  # VVEL ?
		                                                                       ('Geopotential Height', levelsAll),  # HGT
		                                                                       ('Absolute vorticity',  levelsAll),  # ABSV
		                                                                       ('Temperature',         levelsAll),  # TMP
		                                                                       ('Relative humidity',   levelsAll)]) # RH


#===================================================================================================
# MeteoData
#===================================================================================================


class MeteoData():

	def __init__(self):

		self.sorted_cells = BinObj.load("sorted_cells")  # [kCell] -> (row, col)
		self.meteo_days   = BinObj.load("meteo_days")
		self.meteo_params = BinObj.load("meteo_params")
		self.meteo_content_by_cell_day = BinObj.load("meteo_content_by_cell_day")
		self.nb_days      = len(self.meteo_days)
		self.nb_cells     = len(self.sorted_cells)

	# returned lines order:
	# cell 0, day 0 
	# cell 0, day 1 
	# ... 
	# cell 1, day 0 
	# cell 1, day 1 
	# ... 
	def getMeteoMatrix(self, cells, meteo_params):
		# cells
		lIdx = Data.get_lines(cells, self.nb_cells, self.nb_days)
		# params
		cIdx = [self.meteo_params.index(pX) for pX in meteo_params]
		# return extracted part
		return self.meteo_content_by_cell_day[lIdx,:][:,cIdx]


#===================================================================================================
# FlightsData
#===================================================================================================


class FlightsData():

	def __init__(self):
		self.cell_resolution          = 1.0
		self.flights_by_cell_day      = BinObj.load("flights_by_cell_day") # [cell in range(0,318257))] -> [('yyyy-mm-dd hh:mm:ss', (score, alt, plaf, lat, lon, takeoff_alt, mountainess)), ...]
		self.cellKAltitudeMountainess = BinObj.load("mountainess_by_cell_alt") # [cell][kAlt] -> mountainess (in [0,1])
		self.nb_cells                 = len(BinObj.load("sorted_cells_latlon"))
		self.nb_days                  = len(self.flights_by_cell_day)//self.nb_cells


	def exportTakeoffsLandings(self):
		for cd in self.flights_by_cell_day:
			for f in cd:
				print(f[1][3], f[1][4])


	@staticmethod
	def getMountainessValue(lat, lon):
		mountainness_zoom = 7
		coords = TilesMaths.LatLonToTileCoords(mountainness_zoom, lat, lon)
		filename = "../tiler/_cache/elevation/%d/%d/%d.mountainess" % (mountainness_zoom, coords['tx'], coords['ty'])
		with open(filename, "rb") as f:
			content = f.read(256 * 256)
		return float(struct.unpack('B', content[coords['x'] * 256 + coords['y']])[0])/255.0


	def histoPlaf(self):
		from PIL import Image

		width  = 1000
		height = 1000
		data = np.zeros((height, width, 3), dtype=np.uint8)

		for dc in tqdm.tqdm(self.flights_by_cell_day):
			for f in dc:
				score      = f[1][0]
				plaf       = f[1][2]
				takeoffAlt = f[1][5]

				x = takeoffAlt/4.0
				y = plaf/4.0

				ix = min(width-1,  max(0, int(round(x))))
				iy = min(height-1, max(0, int(round(y))))

				if score>100:
					data[iy,ix,0] = min(255, data[iy,ix,0]+50)
				else:
					data[iy,ix,2] = min(255, data[iy,ix,2]+50)

		img = Image.fromarray(data, 'RGB')
		img.save('/tmp/plaf.png')
		#img.show()


	# altitude -> pressure
	@staticmethod
	def __barometricLeveling(z): 
		return 1013.25 * pow((1.0 - (0.0065 * z) / 288.15), 5.255)

	@staticmethod
	def kAltitude(altitude):
		return max(0, int((1050 - FlightsData.__barometricLeveling(altitude))//100))

	@staticmethod
	def __flownKAltitudes(daycell, points_limit = -1.0):
		return list(set([FlightsData.kAltitude(f[1][5]) for f in daycell if f[1][0]>=points_limit]))
	
	@staticmethod
	def __nbFlownForKAltitude(daycell, kAlt, points_limit = -1.0):
		return len([1 for f in daycell if f[1][0]>=points_limit and FlightsData.kAltitude(f[1][5])==kAlt])


	def get_flights_by_altitude_matrix(self, cells, nbWindAltitudes, super_resolution, problem_formulation_regression):

		res = [ np.zeros( (len(cells)*super_resolution*super_resolution*self.nb_days, nbWindAltitudes), dtype=np.float ),
				np.zeros( (len(cells)*super_resolution*super_resolution*self.nb_days, nbWindAltitudes), dtype=np.float ),
				np.zeros( (len(cells)*super_resolution*super_resolution*self.nb_days, nbWindAltitudes), dtype=np.float ),
				np.zeros( (len(cells)*super_resolution*super_resolution*self.nb_days, nbWindAltitudes), dtype=np.float )  ] # flyability at each altitude + fufu

		resLine = 0
		for cell in tqdm.tqdm(cells):
			lIdx = Data.get_lines([cell], self.nb_cells, self.nb_days)

			flight_list_this_day_cell = [[[[] for dc in lIdx] for srY in range(super_resolution)] for srX in range(super_resolution)]

			for kdc,dc in enumerate(lIdx):
				for f in self.flights_by_cell_day[dc]:
					# Calcul des coordonnées de la sous-cellule en cas de super_resolution
					# On évite de fragmenter une sous-cellule en synchronisant le % self.cell_resolution et les cells
					srX = int(((f[1][3]+0.5*self.cell_resolution) % self.cell_resolution)/self.cell_resolution * super_resolution)
					srY = int(((f[1][4]+0.5*self.cell_resolution) % self.cell_resolution)/self.cell_resolution * super_resolution)
					flight_list_this_day_cell[srX][srY][kdc] += [f]

			points_limit = 60.0

			for srX in range(super_resolution):
				for srY in range(super_resolution):

					# all the days for (srX, srY) in "cell"
					for daycell in flight_list_this_day_cell[srX][srY]:
						#print "daycell", daycell
						if len(daycell) > 0:

							# classification
							if not problem_formulation_regression: 
								flownAltitudes     = self.__flownKAltitudes(daycell, points_limit=-1.0)
								flownAltitudesFufu = self.__flownKAltitudes(daycell, points_limit=points_limit)

								res[0][resLine, flownAltitudes]     = 1.0 # flyability
								res[1][resLine, flownAltitudesFufu] = 1.0 # crossability
								res[2][resLine, flownAltitudes]     = 1.0 # wind-flyability
								res[3][resLine, flownAltitudes]     = 1.0 # rain-flyability

							# regression
							else: 
								for kAlt in range(nbWindAltitudes):
									nb_flown   = self.__nbFlownForKAltitude(daycell, kAlt, points_limit=-1.0)
									nb_crossed = self.__nbFlownForKAltitude(daycell, kAlt, points_limit=points_limit)

									res[0][resLine, kAlt] = nb_flown   # flyability
									res[1][resLine, kAlt] = nb_crossed # crossability
									res[2][resLine, kAlt] = nb_flown   # wind-flyability
									res[3][resLine, kAlt] = nb_flown   # rain-flyability
						else:
							pass # already initialized at 0
						resLine += 1

		return res

#===================================================================================================
# DaysData
#===================================================================================================


class DaysData():

	def __init__(self):

		self.meteo_days = BinObj.load("meteo_days")
		self.nb_days    = len(self.meteo_days)

	def getDow(self):

		X = np.zeros((self.nb_days, 7), dtype=np.float)
		X[np.arange(self.nb_days), [self.meteo_days[d].weekday() for d in range(self.nb_days)]] = 1.0
		return X

	def getDate(self):

		return np.array([float(d)/float(self.nb_days-1) for d in range(self.nb_days)], dtype=np.float)


#===================================================================================================
# SpotsData
#===================================================================================================


class Spot:

	def __init__(self, spot_tuple, id, nbFlights, prediction=None):
		self.name       = spot_tuple[0]
		self.lat        = spot_tuple[1]
		self.lon        = spot_tuple[2]
		self.id         = id
		self.nbFlights  = nbFlights
		self.prediction = prediction

	def toDict(self): # To be able to pickle it without knowing the Spot class via BinObj
		return {'name':       self.name,
				'lat':        self.lat,
				'lon':        self.lon,
				'id':         self.id,
				'nbFlights':  self.nbFlights,
				'prediction': self.prediction}

	def __str__(self):
		return "("+ ",".join([self.name.strip(), str(self.lat), str(self.lon), str(self.id), str(self.nbFlights)]) +")"

	def __repr__(self):
		return self.__str__()


class SpotsData:

	def __init__(self):

		self.threshold_nb_spot_flights = 200
		self.spots           = None # [('Kachanoll', 42.9711894497, 21.0862436942), ('Mokna', 42.8645327899, 20.5544962049), ...
		self.spots_by_cell   = None
		self.flights_by_spot = None # [[], [(u'2011-10-02 11:43:48', (11.04, None, 0.0, 44.9254, 16.0529)), (u'2012-06-17 09:45:45', (4.43, None, 0.0, 44.923366666667, 16.053283333333)), ...
		self.flights_by_cell_day_spot = None
		self.meteo_days      = None

		# Force recompute
		if False:
			self.__compute_spots_information()
			self.__save()


	def get_flown_by_spots(self, cells):
		self.__load_or_compute_data()

		nb_days  = len(self.meteo_days)
		nb_cells = len(self.spots_by_cell)
		nb_spots = len(self.flights_by_spot)

		#=====================================================================================
		# 
		#=====================================================================================

		all_Y_cell_spot = [[] for c in range(len(cells))] # [kCell][kSpot] -> vector of flown for all days

		# Apply threshold
		thresholded_spots = [ks for ks,lf in enumerate(self.flights_by_spot) if len(lf)>= self.threshold_nb_spot_flights]
		
		for kc, c in tqdm.tqdm(enumerate(cells)):
			for ks in self.spots_by_cell[c]:
				if ks in thresholded_spots:
					Y_spot = np.zeros((nb_days,), dtype=np.float)
					days_flown = [kd for kd in range(nb_days) if ks in self.flights_by_cell_day_spot[c][kd] and len(self.flights_by_cell_day_spot[c][kd][ks])>0]
					Y_spot[days_flown] = 1.0
					all_Y_cell_spot[kc] += [Y_spot]

		for kc in tqdm.tqdm(range(len(cells))):
			print(kc, len(all_Y_cell_spot[kc]))

		return all_Y_cell_spot


	def getSpots(self, cells):
		self.__load_or_compute_data()

		# Apply threshold to spots list
		thresholdedSpots = [ks for ks, lf in enumerate(self.flights_by_spot) if len(lf) >= self.threshold_nb_spot_flights]

		if False: # Debug, export spots_by_cell
			debug_out = ""
			for c in range(80):
				debug_out += "\n\n"+ str(c) +"\n\n"
				debug_out += str([s for s in self.spots_by_cell[c]])
			with open("/tmp/debug.txt", "w") as fout:
				fout.write(debug_out)

		# Return Spots of cells
		return [[Spot(self.spots[s], s, len(self.flights_by_spot[s])) for s in self.spots_by_cell[c] if s in thresholdedSpots] for c in cells]


	def data_not_loaded(self):
		return self.spots_by_cell is None or self.flights_by_spot is None or self.flights_by_cell_day_spot is None or self.spots is None


	def __load_or_compute_data(self):
		Verbose.print_arguments()

		if self.data_not_loaded():
			try:
				self.__load()
			except:
				pass

		if self.data_not_loaded():
			Verbose.print_text(0, "[WARNING] data_not_loaded, __computeSpotsInformation")
			self.__compute_spots_information()
			self.__save()


	def __load(self):

		self.spots                 = BinObj.load("spots_merged")  # ("name", lat, lon)
		self.spots_by_cell         = BinObj.load("spots_by_cell")
		self.flights_by_spot 	   = BinObj.load("flights_by_spot")
		self.flights_by_cell_day_spot = BinObj.load("flights_by_cell_day_spot")
		self.meteo_days            = BinObj.load("meteo_days")


	def __save(self):

		assert(not self.data_not_loaded())

		BinObj.save(self.spots,                    "spots_merged")
		BinObj.save(self.spots_by_cell,            "spots_by_cell")
		BinObj.save(self.flights_by_spot,          "flights_by_spot")
		BinObj.save(self.flights_by_cell_day_spot, "flights_by_cell_day_spot")


	def __compute_spots_information(self):

		self.meteo_days     = BinObj.load("meteo_days")
		cells 	            = BinObj.load("sorted_cells_latlon")
		flights_by_cell_day = BinObj.load("flights_by_cell_day") # [cell] -> [('yyyy-mm-dd hh:mm:ss', (score, alt, plaf, lat, lon, takeoff_alt, mountainess)), ...]
		self.spots_before_merge = BinObj.load("spots") # ("name", lat, lon)
		self.spots          = self.__fusion_of_close_spots(self.spots_before_merge) # ("name", lat, lon)
		cells_resolution    = 1.0
		spotsWidth          = 0.1

		nb_days  = len(self.meteo_days)
		nb_cells = len(cells)
		nb_spots = len(self.spots)

		#=====================================================================================
		# Assign spots to cells
		#=====================================================================================
		
		self.spots_by_cell = [[] for c in range(nb_cells)] # [kCell] -> [kSpot1, kSpot2, ...]

		for ks,s in enumerate(self.spots):
			for kc,c in enumerate(cells):
				if abs(s[1]-c[0]) <= cells_resolution/2.0 and abs(s[2]-c[1]) <= cells_resolution/2.0:
					self.spots_by_cell[kc] += [ks]

		#=====================================================================================
		# Assign flights to cells
		#=====================================================================================
		
		flights_by_cell = [[f for d in range(nb_days) for f in flights_by_cell_day[d*nb_cells + c]] for c in range(nb_cells)]

		#=====================================================================================
		# Assign flights to spots
		#=====================================================================================

		self.flights_by_spot = [[] for s in range(nb_spots)]

		for kc in tqdm.tqdm(range(nb_cells)):
			for f in flights_by_cell[kc]:
				closest_dist = 1000000.0
				closest_spot = -1
				for s in self.spots_by_cell[kc]:
					dlat = (self.spots[s][1]-f[1][3])
					dlon = (self.spots[s][2]-f[1][4])
					dist = dlat**2 + dlon**2
					if dist < closest_dist and abs(dlat) <= spotsWidth and abs(dlon) <= spotsWidth:
						closest_spot = s
						closest_dist = dist
				self.flights_by_spot[closest_spot] += [f]

		#=====================================================================================
		# flights_by_cell_day_spot[kCell][kDay][kSpot] = list of flights
		#=====================================================================================

		# strday -> kday
		strDay_to_kDay = {}
		for kday, day in enumerate(self.meteo_days):
			strDay_to_kDay[str(day)] = kday


		self.flights_by_cell_day_spot = [[{} for d in range(nb_days)] for c in range(nb_cells)]

		for kc in tqdm.tqdm(range(nb_cells)):
			for ks in self.spots_by_cell[kc]:
				for f in self.flights_by_spot[ks]:
					kd = strDay_to_kDay[str(f[0]).split(" ")[0]]
					if ks not in self.flights_by_cell_day_spot[kc][kd]:
						self.flights_by_cell_day_spot[kc][kd][ks] = []
					self.flights_by_cell_day_spot[kc][kd][ks] += [f]


	# https://en.wikibooks.org/w/index.php?title=Algorithm_Implementation/Strings/Longest_common_substring
	@staticmethod
	def __longest_common_substring(s1, s2):
		m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
		longest, x_longest = 0, 0
		for x in range(1, 1 + len(s1)):
			for y in range(1, 1 + len(s2)):
				if s1[x - 1].lower() == s2[y - 1].lower():
					m[x][y] = m[x - 1][y - 1] + 1
					if m[x][y] > longest:
						longest = m[x][y]
						x_longest = x
				else:
					m[x][y] = 0
		return s1[x_longest - longest: x_longest]


	@staticmethod
	def __name_clean_for_comparison(name):
		noNums = re.sub("[0-9]+", "", name)
		return noNums.replace("_", " ").replace(".", " ").replace("\t", " ").replace("  ", " ").replace("  ", " ")


	@classmethod
	def __get_fusion_name2(cls, names):
		name1 = cls.__name_clean_for_comparison(names[0])
		for kname in range(1, len(names)):
			name2 = cls.__name_clean_for_comparison(names[kname])
			name1 = SpotsData.__longest_common_substring(name1, name2).strip(' (_-')
		return name1


	@classmethod
	def __get_fusion_name(cls, names):
		assert(len(names)>1)
		fusioned = cls.__get_fusion_name2(names)

		if len(fusioned)<5 and len(names)>2:
			for excluded in range(len(names)):
				candidate = cls.__get_fusion_name2([names[kn] for kn in  range(len(names)) if kn != excluded])
				if len(candidate) > len(fusioned):
					fusioned = candidate

		if len(fusioned)<5:
			fusioned = names[0]

		return fusioned +",,,"+ ",,".join(set(names))


	@staticmethod
	def __merge_clusters(clusters1):
		clusters2 = []
		for c1 in clusters1:
			merged = False
			for s in c1:
				for kc2, c2 in enumerate(clusters2):
					if s in c2:
						clusters2[kc2] = clusters2[kc2] | c1
						merged = True
			if not merged:
				clusters2 += [c1]
		return clusters2


	@staticmethod
	def __clean_spot_name(name):
		return name.replace('_', ' ')


	def __fusion_of_close_spots(self, spots):
		FUSION_DISTANCE = 0.01*0.01 #((45.310 - 45.307) * (45.310 - 45.307) + (5.891 - 5.888) * (5.891 - 5.888))

		#==========================================================
		# Liste les couples de spots trop proches
		closeCouples = []

		nbSpots = len(spots)
		for ks1 in tqdm.tqdm(range(nbSpots)):
			s1 = spots[ks1]
			for ks2 in range(ks1):
				s2 = spots[ks2]
				if (s2[1]-s1[1])*(s2[1]-s1[1]) + (s2[2]-s1[2])*(s2[2]-s1[2]) <= FUSION_DISTANCE:
					closeCouples += [[ks1, ks2]]

		#==========================================================
		# Crée un dictionnaire des spots proches
		# {ks1 => [ks1, ks2, ks3], ...
		correspondences = {}

		for couple in closeCouples:
			ks1 = couple[0]
			ks2 = couple[1]
			if ks1 not in correspondences:
				correspondences[ks1] = [ks1]
			if ks2 not in correspondences:
				correspondences[ks2] = [ks2]
			correspondences[ks1] += [ks2]
			correspondences[ks2] += [ks1]

		#==========================================================
		# Clusterise correctement
		clusters = []

		for cor in correspondences:
			clusters += [set(correspondences[cor])]

		for itFusion in range(4):
			clusters = SpotsData.__merge_clusters(copy.copy(clusters))

		#==========================================================
		# Create the center spot of each cluster
		centroids = []

		for clu in clusters:
			centroid_lat  = sum([spots[ks][1] for ks in clu])/float(len(clu))
			centroid_lon  = sum([spots[ks][2] for ks in clu])/float(len(clu))
			centroid_name = SpotsData.__get_fusion_name([spots[ks][0] for ks in clu])
			centroids += [(centroid_name, centroid_lat, centroid_lon)]
			#print centroid_name.ljust(25), [spots[ks][0] for ks in clu]

		#==========================================================
		# New spots list with fusions
		new_spots = []

		# add all the non-clustered spots
		for ks in range(len(spots)):
			inCluster = False
			for clu in clusters:
				if ks in clu:
					inCluster = True
					break
			if not inCluster:
				new_spots += [spots[ks]]

		# add the clustered spots
		for centroid in centroids:
			new_spots += [centroid]


		# ==========================================================
		# Clean names
		for ks in range(len(new_spots)):
			new_spots[ks] = (self.__clean_spot_name(new_spots[ks][0]),) + new_spots[ks][1:]


		# ==========================================================
		# Return new spots list with fusions
		return new_spots

