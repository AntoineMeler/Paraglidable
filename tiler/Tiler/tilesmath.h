#ifndef TILESMATH_H
#define TILESMATH_H

#define TILE_RESOLUTION 256

#include <vector>

int powint(int v, int p);
double Resolution(int zoom);
std::pair<double, double> MetersToLatLon(std::pair<double, double> m);
std::pair<double, double> LatLonToMeters(double lat, double lon);
std::pair<double, double> PixelsToMeters(double px, double py, int zoom);
std::pair<double, double> MetersToPixels(std::pair<double, double> mxy, double zoom);
std::pair<double, double> tilePixelToLatLon(double x, double y, int zoom);

#endif // TILESMATH_H
