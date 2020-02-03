# coding: utf-8

import ssl, urllib.request, datetime, os, sys
ssl._create_default_https_context = ssl._create_unverified_context


class CheckServer:

	def __locationSearch(self):
		url = "https://paraglidable.com/apps/search.php?q=q/chaparei.js"
		req = urllib.request.Request(url)
		req.add_header('Referer', 'https://paraglidable.com/')
		content = urllib.request.urlopen(req).read().decode('utf-8')
		return "Croix du Mont Granier" in content

	def __forecasts(self):
		tilesDir = "/var/www/html/data/tiles"
		strDate = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
		filename = os.path.join(os.path.join(tilesDir, strDate), "progress.txt")
		if os.path.exists(filename):
			elapsedTime = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.stat(filename).st_mtime)
			return elapsedTime.total_seconds()/3600 < 10 # dernier update inferieur à 10h
		else:
			return False

	def checkAll(self):
		try:
			return self.__locationSearch(), self.__forecasts()
		except:
			return False, False


##########################################################################################################
# main
##########################################################################################################


if __name__ == "__main__":

	check_search, check_forecasts = CheckServer().checkAll()

	if not check_search or not check_forecasts:
		from email.mime.text import MIMEText
		from subprocess import Popen, PIPE
		import socket    
		hostname = socket.gethostname() 

		txt = "Paraglidable: check server %s  %s %s" % (hostname, str(check_search),str(check_forecasts))
		msg = MIMEText(txt)
		msg["From"]    = "bot@paraglidable.com"
		msg["To"]      = "antoine@paraglidable.com"
		msg["Subject"] = txt
		p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
		p.communicate(msg.as_string())