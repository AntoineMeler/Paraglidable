<img src="www/imgs/logo/logo.svg" width="80" align="right" />

# Paraglidable

Paraglidable is an A.I.-based flying conditions forecasting program for paragliding.<br/>
You can find it live here: https://paraglidable.com

This repository contains:
* Scripts for setting and training the neural network, downloading +10 days forecasts data from third parties and running a prediction in `/neural_network/`
* Program for generating the map tiles from a prediction in `/tiler/`
* Complete web site in `/www/`

## Requirements

The easiest way to start playing with Paraglidable is to use [Docker](https://www.docker.com). I will only provide support for this workflow. But you can also check the [Dockerfile](docker/Dockerfile) and install dependencies on your own.

The main dependencies are:
* [Python 3](https://www.python.org/)
* [TensorFlow 2](https://www.tensorflow.org/)
* [Qt 5](https://www.qt.io/)
* [Apache HTTP Server](https://httpd.apache.org/) with [PHP](https://www.php.net/)

## Installation

```bash
git clone https://github.com/AntoineMeler/Paraglidable.git
```
<pre>
docker build Paraglidable/docker/
docker run -it -p 8001:80 -p 8888:8888 -v $(pwd)/Paraglidable:/workspaces/Paraglidable <b><i>IMAGE</i></b>
</pre>
```bash
cd /workspaces/Paraglidable/scripts/
python download_data.py             # Download training weather and flights data (200MB)
python download_elevation_tiles.py  # Download elevation data (260MB)
python download_background_tiles.py # Download background tiles (facultative) (180MB)
sh build_tiler.sh                   # Build the C++ tiler
```

You're all set!

## Usage

* `/neural_network/train.py` run a new training
* `/neural_network/forecast.py` run +10 days forecast and generate tiles
* `/scripts/start_server.sh` start Apache server to visualize the forecast on the local website

## Docummentation

### Neural Network

You can find the neural network description here: [neural network documentation](neural_network/)

## Contributing

Contributions on any subject are welcome by doing a [pull request from a fork](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/creating-a-pull-request-from-a-fork)!

## License

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)