import os
import inc.google_drive_downloader

scripts_dir = os.path.dirname(os.path.realpath(__file__))

root_dir = scripts_dir + "/.."
dest_dir = root_dir + "/tiler/_cache/elevation"
if os.path.isdir("/workspaces/Paraglidable"): # in docker
	www_dir = root_dir + "/www/
else: # on production server
	www_dir = "/var/www/html/"

os.makedirs(dest_dir, exist_ok=True)
os.makedirs(www_dir + "data", exist_ok=True)
os.system("ln -s "+ dest_dir +" "+ www_dir +"data/elevation")

files = [("1rnA5qbvY3FhPnkpTj4EgOssQd4TI6bMX", "5.zip"),
		 ("1ErLEzdxCFnvy9_-28s7T4YSeXMfTSrpO", "6.zip"),
		 ("1TPajsz5R2PJk8wgbI5z_H-2JfOyvsT_G", "7.zip"),
		 ("1qEZ2tnWfCbYwD-7X4CycTXKNh61RCGCX", "8.zip"),
		 ("1gmrIyHynNWXb5bY0n833mHF7fEn8tC-_", "9.zip")]

for file_id, res_file in files:
	print("Downloading", dest_dir+"/"+res_file, "...")
	inc.google_drive_downloader.download(file_id, dest_dir, res_file)
