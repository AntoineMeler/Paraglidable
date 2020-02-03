
#include <math.h>

#include "tilesmath.h"


int powint(int v, int p)
{
    int res = 1;
    for (int i=0; i<p; i++)
    {
        res *= v;
    }
    return res;
}


// http://www.maptiler.org/google-maps-coordinates-tile-bounds-projection/

#define ORIGIN_SHIFT (2.0 * M_PI * 6378137.0 / 2.0)
#define INITIAL_RESOLUTION (2.0 * M_PI * 6378137.0)

// Resolution (meters/pixel) for given zoom level (measured at Equator)
double Resolution(int zoom)
{
    return INITIAL_RESOLUTION / pow(2.0, zoom);
}

// Converts XY point from Spherical Mercator EPSG:900913 to lat/lon in WGS84 Datum
std::pair<double, double> MetersToLatLon(std::pair<double, double> m)
{
    double mx = m.first;
    double my = m.second;

    double lon = (mx / ORIGIN_SHIFT) * 180.0;

    double lat = (my / ORIGIN_SHIFT) * 180.0;
    lat = 180.0 / M_PI * (2.0 * atan(exp(lat * M_PI/180.0)) - M_PI/2.0);

    return std::pair<double,double>(-lat, lon);
}
// "Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913"
std::pair<double, double> LatLonToMeters(double lat, double lon)
{
    double mx = lon * ORIGIN_SHIFT/180.0;
    double my = log( tan((90.0 + lat) * M_PI/360.0)) / (M_PI / 180.0);

    my = my * ORIGIN_SHIFT / 180.0;
    return std::pair<double, double>(mx, my);
}

// Converts pixel coordinates in given zoom level of pyramid to EPSG:900913
std::pair<double, double> PixelsToMeters(double px, double py, int zoom)
{
    double res = Resolution(zoom);
    double mx = px * res - ORIGIN_SHIFT;
    double my = py * res - ORIGIN_SHIFT;
    return std::pair<double, double>(mx, my);
}
// "Converts EPSG:900913 to pyramid pixel coordinates in given zoom level"
std::pair<double, double> MetersToPixels(std::pair<double, double> mxy, double zoom)
{
    double mx = mxy.first;
    double my = mxy.second;
    double res = Resolution( zoom );
    double px = (mx + ORIGIN_SHIFT) / res;
    double py = (my + ORIGIN_SHIFT) / res;
    return std::pair<double, double>(px, py);
}

std::pair<double, double> tilePixelToLatLon(double x, double y, int zoom)
{
    std::pair<double, double> latLon = MetersToLatLon(PixelsToMeters(x, y, zoom));
    return latLon;
}

