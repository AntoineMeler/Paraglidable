import math



# http://www.maptiler.org/google-maps-coordinates-tile-bounds-projection/
class TilesMaths():

	ORIGIN_SHIFT       = (2.0 * math.pi * 6378137.0 / 2.0)
	INITIAL_RESOLUTION = (2.0 * math.pi * 6378137.0)

	@staticmethod
	def Resolution(zoom):
		return TilesMaths.INITIAL_RESOLUTION / (2.0**zoom)


	@staticmethod
	def MetersToPixels(mx, my, zoom):
		res = TilesMaths.Resolution(zoom)
		px = (mx + TilesMaths.ORIGIN_SHIFT) / res
		py = (my + TilesMaths.ORIGIN_SHIFT) / res
		return (px, py)


	# "Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913"
	@staticmethod
	def LatLonToMeters(lat, lon):
		mx = lon * TilesMaths.ORIGIN_SHIFT/180.0
		my = math.log( math.tan((90.0 + lat) * math.pi/360.0)) / (math.pi / 180.0)
		my = my * TilesMaths.ORIGIN_SHIFT / 180.0
		return (mx, my)


	@staticmethod
	def LatLonToTileCoords(zoom, lat, lon):
		meters = TilesMaths.LatLonToMeters(-lat, lon)
		TxTy   = TilesMaths.MetersToPixels(meters[0], meters[1], zoom)

		x = max(0, min(255, int(math.fmod(TxTy[0], 1) * 256.0)))
		y = max(0, min(255, int(math.fmod(TxTy[1], 1) * 256.0)))

		coords = {'tx': int(TxTy[0]),
				  'ty': int(TxTy[1]),
				  'x' : x,
				  'y' : y }

		return coords
