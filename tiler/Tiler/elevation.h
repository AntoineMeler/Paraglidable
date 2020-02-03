#ifndef ELEVATION_H
#define ELEVATION_H

#include <map>
#include <QString>

#define MOUNTAINESS_TILES_ZOOM 7

class Elevation
{
    const int     SAMPLES;
    const int     DEFAULT_ELEVATION;
    const QString DIR_SRTM3;
    const int     MAX_CACHED_FILES;

    std::map< std::pair<int,int>, std::vector<qint16> > m_data;

    QString getFilename(std::pair<int,int> ilatlon);
    void loadFileIfNeeded(std::pair<int,int> ilatlon);
    void freeCachedFiles(int nbFilesToFree, std::pair<int,int> ilatlon);

public:

    Elevation(QString dataDir) :
        SAMPLES(1201),
        DEFAULT_ELEVATION(0),
        DIR_SRTM3(dataDir),
        MAX_CACHED_FILES(400)
    {
    }

    QString getFilename(float lat, float lon); // debug, find holes
    int getElevation(float lat, float lon);
};


class ElevationTiles
{
    Elevation m_elevation;
    QString   m_cacheDir;

    void computeTile(int zoom, int tx, int ty, QString tileFilename, qint32* GMTED2010buff);
    QString getFilenameDir(int zoom, int tx, int ty);

public:
    QString getFilename(int zoom, int tx, int ty, const QString ext=".elev");
    std::vector<qint16> loadElevationTile(QString tileFilename);
    qint16 getElevationValueInElevationTile(std::vector<qint16> &data, int tx, int ty);

    ElevationTiles(QString cacheDir);
    void computeAllTiles();
};



class Mountainess
{
    QString m_cacheDir;
    ElevationTiles m_elevationTiles;
    std::map<std::pair<int,int>, std::vector<qint16>> m_allElevationTiles;

public:
    Mountainess(QString cacheDir);
    void loadTiles();
    float computeMountainess(int tx, int ty, int x, int y);
    void computeAllMountainessTiles();

    // used for tiles drawing
    quint8 getMountainessValueInTile(std::vector<quint8> &data, int tx, int ty);
    std::vector<quint8> loadMountainessTile(QString tileFilename);
};

#endif // ELEVATION_H
