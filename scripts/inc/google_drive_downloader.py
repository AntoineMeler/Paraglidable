import os, subprocess

def is_big_file(res_file):
	with open(res_file, "r") as fin:
		try:
			return "Google Drive - Virus scan warning" in fin.read()
		except UnicodeDecodeError:
			return False

def download(file_id, dest_dir, res_file, zipped=True):
	os.makedirs(dest_dir, exist_ok=True)
	subprocess.run("wget \"https://docs.google.com/uc?export=download&id="+ file_id +"\" -O "+ dest_dir+"/"+res_file, shell=True, check=True)
	if is_big_file(dest_dir+"/"+res_file):
		os.remove(dest_dir+"/"+res_file)
		subprocess.run("wget --load-cookies /tmp/cookies.txt \"https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id="+ file_id +"' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\\1\\n/p')&id="+ file_id +"\" -O "+ dest_dir+"/"+res_file +" && rm -rf /tmp/cookies.txt", shell=True, check=True)

	if zipped:
		os.system("unzip "+ dest_dir+"/"+res_file +" -d "+ dest_dir +"/")
		os.remove(dest_dir+"/"+res_file)
