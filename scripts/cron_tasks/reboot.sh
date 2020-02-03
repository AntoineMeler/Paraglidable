sleep 20
sh /home/antoine/GIT/Paraglidable/scripts/cron_tasks/renew_certificates.sh
docker run -d -v /data/:/data/ -p 8001:80 klokantech/osmnames-sphinxsearch
