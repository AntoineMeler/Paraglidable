<?php

//===========================================================================
// Functions
//===========================================================================

// tile math
// http://www.maptiler.org/google-maps-coordinates-tile-bounds-projection/
$ORIGIN_SHIFT       = (2.0 * M_PI * 6378137.0 / 2.0);
$INITIAL_RESOLUTION = (2.0 * M_PI * 6378137.0);

function Resolution($zoom)
{
    return $GLOBALS['INITIAL_RESOLUTION'] / pow(2.0, $zoom);
}

function MetersToPixels($mx, $my, $zoom)
{
	$res = Resolution($zoom);
	$px = ($mx + $GLOBALS['ORIGIN_SHIFT']) / $res;
	$py = ($my + $GLOBALS['ORIGIN_SHIFT']) / $res;
	return array($px, $py);
}

// "Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913"
function LatLonToMeters($lat, $lon)
{
    $mx = $lon * $GLOBALS['ORIGIN_SHIFT']/180.0;
    $my = log( tan((90.0 + $lat) * M_PI/360.0)) / (M_PI / 180.0);
    $my = $my * $GLOBALS['ORIGIN_SHIFT'] / 180.0;
    return array($mx, $my);
}

function LatLonToTileCoords($lat, $lon, $dataTilesZoom = 7)
{
	$meters = LatLonToMeters(-$lat, $lon);
	$TxTy   = MetersToPixels($meters[0], $meters[1], $dataTilesZoom);
	$xy     = array( max(0, min(255, intval(fmod($TxTy[0], 1)*256.0))),
				     max(0, min(255, intval(fmod($TxTy[1], 1)*256.0)))  );
	$TxTy   = array( intval($TxTy[0]), intval($TxTy[1]) );

	$coords = array('tx' 	=> $TxTy[0],
					'ty' 	=> $TxTy[1],
					'x'  	=> $xy[0],
					'y'  	=> $xy[1],
					'zoom' 	=> $dataTilesZoom );
	return $coords;
}

?>