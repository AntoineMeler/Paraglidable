sudo rm -rf /var/www/html
sudo ln -s $(pwd)/../www /var/www/html
sudo bash -c 'echo "ServerName paraglidable.com" >> /etc/apache2/apache2.conf'
sudo service apache2 start
echo "http://localhost:8001/\n"
