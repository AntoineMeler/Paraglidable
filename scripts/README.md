# Scripts

## To be executed ones

```bash
python download_data.py             # Download training weather and flights data (200MB)
python download_elevation_tiles.py  # Download elevation data (260MB)
python download_background_tiles.py # Download background tiles (facultative) (180MB)
sh build_tiler.sh                   # Build the C++ tiler

python download_GFS.py # Optional, download the source .grib weather data files from GFS
```

## To be executed once per session

```bash
sh start_server.sh  # Start Apache server
sh start_jupyter.sh # Start Jupyter server for the neural network documentation
```

## To be executed if needed

```bash
sh update_nn_README.sh # If you have modified the neural network documentation
```
