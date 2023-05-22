import os, datetime, shutil, subprocess

nb_days                    = 10
last_forecast_time_fileDir = "/tmp/lastForecastTime"
downloaded_forecasts_dir   = "/tmp/forecasts"
tiles_dir                  = "/var/www/html/data/tiles"
api_referers               = "/tmp/apiCalls.txt"


def remove_dir(path):
	try:
		shutil.rmtree(path)
		print("[removed       ]", path)
	except OSError:
		print("[does not exist]", path)

def remove_file(path):
	try:
		os.remove(path)
		print("[removed       ]", path)
	except OSError:
		print("[does not exist]", path)


if __name__ == "__main__":
	remove_file(api_referers)

	# all past days
	for delta_days in range(1, 100):
		strday = (datetime.datetime.now() + datetime.timedelta(days = -delta_days)).strftime("%Y-%m-%d")
		remove_file(os.path.join(last_forecast_time_fileDir, strday))
		for h in [6, 12, 18]:
			meteoFile = os.path.join(downloaded_forecasts_dir, strday + ("-%02d"%h))
			remove_file(meteoFile)

	# far past days, to be removed
	for delta_days in range(nb_days+1-4, 100):
		strday = (datetime.datetime.now() + datetime.timedelta(days = -delta_days)).strftime("%Y-%m-%d")
		remove_dir(os.path.join(tiles_dir, strday))

