# coding: utf-8

import math, os, errno, random, tqdm, subprocess, re, pickle, shutil
import numpy as np

class Utils:

	@staticmethod
	def rm_dir(thedir):
		if os.path.exists(thedir):
			shutil.rmtree(thedir)

	@staticmethod
	def copy_dir(src, dst):
		Utils.rm_dir(dst)
		shutil.copytree(src, dst)

	@staticmethod
	def move_dir(src, dst):
		Utils.rm_dir(dst)
		shutil.move(src, dst)	
	
	#=======================================================================
	# Color map
	#=======================================================================

	@staticmethod
	def color_map(val, vals, colors):
		if val < vals[0]:
			val = vals[0]
		if val > vals[-1]:
			val = vals[-1]

		for v in range(len(vals) - 1):
			if val <= vals[v + 1]:
				colorR = int(colors[v][0:2], 16), int(colors[v + 1][0:2], 16)
				colorG = int(colors[v][2:4], 16), int(colors[v + 1][2:4], 16)
				colorB = int(colors[v][4:6], 16), int(colors[v + 1][4:6], 16)

				interp = (val - vals[v]) / (vals[v + 1] - vals[v])
				colorRint = interp * (colorR[1] - colorR[0]) + colorR[0]
				colorGint = interp * (colorG[1] - colorG[0]) + colorG[0]
				colorBint = interp * (colorB[1] - colorB[0]) + colorB[0]

				return (int(0.5 + colorRint), int(0.5 + colorGint), int(0.5 + colorBint))

		return (0, 0, 0)

	#=======================================================================
	# Wind
	#=======================================================================

	@staticmethod
	def wind_UV_to_n(UVcols, n):
		assert (UVcols.shape[1] == 2)
		nbVals = UVcols.shape[0]

		if False:
			res = np.empty((nbVals, n), dtype=np.float)
			for ia in range(n):
				a = float(ia) / float(n) * 2.0 * math.pi
				res[:, ia] = np.clip(math.cos(a) * UVcols[:, 0] + math.sin(a) * UVcols[:, 1], a_min=0.0, a_max=None)
		else:
			angle = np.mod((np.around(np.arctan2(UVcols[:,1], UVcols[:,0]) / (2.0*math.pi) * n) + n/2).astype(int), n)

			res = np.zeros((nbVals, n), dtype=np.float)
			res[np.arange(nbVals), angle] = np.sqrt(UVcols[:, 0]*UVcols[:, 0] + UVcols[:, 1]*UVcols[:, 1])
			#print res


		return res

	# X_wind_UV must be UVUVUVUV...
	@staticmethod
	def convert_wind_matrix(X_wind_UV, nbWindDims):
		X_wind = np.empty((X_wind_UV.shape[0], nbWindDims*X_wind_UV.shape[1]//2), dtype=np.float)
		for w in range(X_wind_UV.shape[1]//2):
			X_wind[:,range(8*w,8*(w+1))] = Utils.wind_UV_to_n(X_wind_UV[:,range(2*w,2*(w+1))], nbWindDims)
		return X_wind

	#=======================================================================
	#
	#=======================================================================

	@staticmethod
	def compute_normalization_coeffs(X):
		xArrayMean = np.mean(X, axis=0)
		xArraySquaredMean = np.square(xArrayMean)
		xArrayMeanSquare = np.mean(np.square(X), axis=0)
		xArrayStd = np.sqrt(xArrayMeanSquare - xArraySquaredMean)

		return xArrayMean, xArrayStd

	@staticmethod
	def apply_normalization(X, normalization_mean, normalization_std):
		for d in range(X.shape[0]):
			X[d, :] = (X[d, :] - normalization_mean.transpose()) / normalization_std.transpose()

	#=======================================================================
	#
	#=======================================================================

	@staticmethod
	def convert_longitude(lon):
		if lon <= 180.0:
			return lon
		else:
			return lon - 360

	#=======================================================================
	#
	#=======================================================================

	@staticmethod
	def get_elapsed_time(searched):
		output = subprocess.Popen(["ps", "-eo", "pid,etime,args"], encoding='utf8', stdout=subprocess.PIPE).communicate()[0]
		results = []
		for line in output.split("\n"):
			if searched in line:
				splitted = line.split()
				if len(splitted) >= 2:
					pid = int(splitted[0])
					res = re.findall("(([0-9]+)\\-)?(([0-9]+):)?([0-9]+):([0-9]+)", splitted[1])
					if len(res) > 0:
						_, days, _, hours, minutes, seconds = res[0]
						if days == '':
							days = '0'
						if hours == '':
							hours = '0'

						nbElapsedSeconds = int(seconds) + 60 * int(minutes) + 3600 * int(hours) + 24 * 3600 * int(days)

						results += [(pid, nbElapsedSeconds)]
		return results
