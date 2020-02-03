from datetime import date
from dateutil.rrule import rrule, DAILY, YEARLY
import sys, os, urllib.request, datetime, colorama
colorama.init(autoreset=True)


data_directory      = "/volume/"
training_start_date = "2019-01-01"
training_end_date   = "2019-12-31" # (included)


def downloadGFS(day):
	gfs_data_subdirectory      = ["GFS", "anl"]
	min_expected_gfs_file_size = 10000000 # 10Mo

    for h in [0, 6, 12, 18]:
        dth = day+datetime.timedelta(hours=h)
        for dh in [0]:
            for resolution in [3]:

                destinationDir = os.path.join(*([data_directory] + gfs_data_subdirectory + [dth.strftime("%Y-%m")]))
                os.makedirs(destinationDir, exist_ok=True)

                nbOk = 0
                for gribVersion in ["grb", "grb2"]: # We try to download .grb and .grb2 as it has changed over time
                    fname = ("gfsanl_%d_"%resolution) + dth.strftime("%Y%m%d_%H") + ("00_00%d." % dh) + gribVersion
                    fullfname = os.path.join(*[destinationDir, fname])

                    if not os.path.isfile(fullfname) or not os.path.getsize(fullfname) > min_expected_gfs_file_size:
                        url = "https://nomads.ncdc.noaa.gov/data/gfsanl/"+ \
                               dth.strftime("%Y%m") + "/"  + \
                               dth.strftime("%Y%m%d") + "/" + \
                               fname

                        print("Downloading", colorama.Fore.BLUE + fullfname)

                        try: # Because we try to download .grb and .grb2 as it has changed over time
                            urllib.request.urlretrieve(url, fullfname)
                            nbOk += 1
                        except urllib.error.HTTPError:
                            pass
                    else:
                        nbOk += 1
                
                # Check if we could find either a .grb or a .grb2 file
                if nbOk==0:
                    print(colorama.Fore.RED+"ERROR: could not download file for "+ dth.strftime("%Y%m%d_%H"))
                    #sys.exit(1)


def downloadWeatherData():
    start = datetime.datetime.strptime(training_start_date, '%Y-%m-%d').date()
    end   = datetime.datetime.strptime(training_end_date,   '%Y-%m-%d').date()

    for day in rrule(DAILY, dtstart=start, until=end):
        downloadGFS(day)


if __name__ == "__main__":
    downloadWeatherData()