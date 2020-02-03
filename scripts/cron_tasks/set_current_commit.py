import os, re
from subprocess import Popen, PIPE

os.chdir(os.path.dirname(os.path.realpath(__file__)))

output = Popen(["git", "log", "-1"], stdout=PIPE)
response = output.communicate()[0].decode('utf-8')
commit = re.findall("commit ([^\n]+)\n", response)[0]

with open("/var/www/html/data/commit.txt", "w") as fout:
	fout.write(commit)