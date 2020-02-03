
#include <QDebug>
#include <QFile>
#include <QDir>
#include <QDataStream>
#include <QFileInfo>
#include <math.h>
#include <set>

#include "elevation.h"
#include "tilesmath.h"

#define TILE_RESOLUTION 256

//===================================================================================================
//===================================================================================================
// GMTED2010 (North, not in SRTM)
//===================================================================================================
//===================================================================================================

#define GMTED2010_SIZE (9600 * 2*14400)

// Used for Norway with script GMTED2010.py
int getGMTEDelevation(qint32 *buff, float lat, float lon)
{
    const float minLat = 50.0f;
    const float maxLat = 70.0f;
    const float minLon =  0.0f;
    const float maxLon = 60.0f;

    if (lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon)
    {
        int iLat = 9600-1 - qMin((int)9600,  (int)((lat-minLat)/(maxLat-minLat)*9600));
        int iLon = qMin((int)(2*14400), (int)((lon-minLon)/(maxLon-minLon)*2*14400));
        int p = iLat*2*14400 + iLon;
        return (int)buff[p];
    }
    else {
        return 0;
    }
}

qint32* loadGMTEDdata(const char* filename)
{
    qint32* elevationBuff = new qint32[GMTED2010_SIZE];

    QFile elevation(filename);
    QDataStream data(&elevation);
    elevation.open(QIODevice::ReadOnly);
    for (int i=0; i<GMTED2010_SIZE; i++) {
        data >> elevationBuff[i];
    }

    return elevationBuff;
}

//===================================================================================================
//===================================================================================================
//
//===================================================================================================
//===================================================================================================


struct less_than_key
{
    std::pair<int,int> ref;

    less_than_key(std::pair<int,int> ref)
    {
        this->ref = ref;
    }

    int distanceToRef(const std::pair<int,int>& p1)
    {
        if (p1.first < ref.first && p1.second < ref.second) // on ne devrait plus en avoir besoin pour ce zoom
            return 100000;
        else
            return qMin(qAbs(p1.first - ref.first), qAbs(p1.second - ref.second));
    }

    inline bool operator() (const std::pair<int,int>& p1, const std::pair<int,int>& p2)
    {
        return (distanceToRef(p1) < distanceToRef(p2));
    }
};

void Elevation::freeCachedFiles(int nbFilesToFree, std::pair<int,int> ilatlon)
{
    // free the nbFilesToFree farest from ilatlon

    std::vector< std::pair<int,int> > keys;

    for(std::map< std::pair<int,int>, std::vector<qint16> >::iterator it = m_data.begin(); it != m_data.end(); ++it)
    {
        keys.push_back(it->first);
    }

    // find the farests

    std::sort(keys.begin(), keys.end(), less_than_key(ilatlon));

    // erase them

    for (int f=0; f<qMin(nbFilesToFree, (int)keys.size()); f++)
    {
        m_data.erase(keys[(int)keys.size()-1-f]);
    }
}

QString Elevation::getFilename(float lat, float lon)
{
    std::pair<int,int> ilatlon = std::pair<int,int>(lat >= 0.0f ? (int)lat : (int)lat-1, lon >= 0.0f ? (int)lon : (int)lon-1);
    return getFilename(ilatlon);
}

int Elevation::getElevation(float lat, float lon)
{
    std::pair<int,int> ilatlon = std::pair<int,int>(lat >= 0.0f ? (int)lat : (int)lat-1, lon >= 0.0f ? (int)lon : (int)lon-1);

    if ((int)m_data.size() > MAX_CACHED_FILES) {
        freeCachedFiles(MAX_CACHED_FILES/4, ilatlon);
    }

    loadFileIfNeeded(ilatlon);

    if (m_data.find(ilatlon) == m_data.end() || (int)m_data[ilatlon].size() < SAMPLES*SAMPLES) // file not found
    {
        return DEFAULT_ELEVATION;
    }
    else
    {
        int latRow = (int)round((lat >= 0.0f ? (lat - (int)lat) : (lat - (int)lat + 1)) * (SAMPLES - 1));
        int lonRow = (int)round((lon >= 0.0f ? (lon - (int)lon) : (lon - (int)lon + 1)) * (SAMPLES - 1));

        int idx = lonRow + SAMPLES*(SAMPLES - 1 - latRow);
#if 0
        if (idx < 0 || idx >= SAMPLES*SAMPLES)
        {
            qDebug() << "ERROR";
            qDebug() << "idx" << idx;
            qDebug() << "lat, lon" << lat << lon;
            qDebug() << "(int)lat, (int)lon" << (int)lat << (int)lon;
            qDebug() << "latRow, lonRow" << latRow << lonRow;

            exit(1);

        }
#endif
        return (int)m_data[ilatlon][idx];
    }
}

QString Elevation::getFilename(std::pair<int,int> ilatlon)
{
    int ilat = ilatlon.first;
    int ilon = ilatlon.second;

    QString ns, ew;

    if (ilat >= 0)
        ns = "N";
    else
        ns = "S";

    if (ilon >= 0)
        ew = "E";
    else
        ew = "W";

    char buffLat[16];
    char buffLon[16];

    sprintf(buffLat, "%02d", ilat>=0 ? ilat : -ilat);
    sprintf(buffLon, "%03d", ilon>=0 ? ilon : -ilon);

    return DIR_SRTM3 + "/"+ ns + QString(buffLat) + ew + QString(buffLon) + ".hgt";
}

void Elevation::loadFileIfNeeded(std::pair<int,int> ilatlon)
{
    if (m_data.find(ilatlon) != m_data.end()) // already loaded
        return;

    QString filename = getFilename(ilatlon);
    QFile myfile;
    myfile.setFileName(filename);
    if(!myfile.open(QIODevice::ReadOnly))
    {
        m_data[ilatlon] = std::vector<qint16>(0); // empty data
        return;
    }

    QDataStream data(&myfile);
    data.setByteOrder(QDataStream::BigEndian);
    std::vector<qint16> result;

    qDebug() << filename;

    while(!data.atEnd()) {
        qint16 elev;
        data >> elev;
        result.push_back(elev);
    }

    //qDebug() << (int)result.size();
    //exit(0);

    m_data[ilatlon] = result;
}

//============================================================================
// ElevationTiles
//============================================================================


ElevationTiles::ElevationTiles(QString cacheDir) :
    m_elevation("/Volumes/PARA2/SRTM3"),
    m_cacheDir(cacheDir)
{
}

qint16 ElevationTiles::getElevationValueInElevationTile(std::vector<qint16> &data, int tx, int ty)
{
    if (data.size()==0 || tx>=TILE_RESOLUTION || ty>=TILE_RESOLUTION || tx<0 || ty<0) {
        return 0;
    } else {
        return data[tx*TILE_RESOLUTION + ty];
    }
}

void ElevationTiles::computeTile(int zoom, int tx, int ty, QString tileFilename, qint32* GMTED2010buff=NULL)
{
    QFile file(tileFilename);
    file.open(QIODevice::WriteOnly);
    QDataStream out(&file);

    bool onlyZeros = true;

    std::map< QString, std::vector<qint16> > prev_zoom_tiles;

    for (int x=0; x<TILE_RESOLUTION; x++)
    {
        for (int y=0; y<TILE_RESOLUTION; y++)
        {
            double dx = tx + ((double)x+0.5)/((double)TILE_RESOLUTION);
            double dy = ty + ((double)y+0.5)/((double)TILE_RESOLUTION);
            std::pair<float, float> latlon = tilePixelToLatLon(dx, dy, zoom);

            qint16 elev = 0;
            if (zoom == 9)
            {
                if (GMTED2010buff != NULL && latlon.first >= 60.15)
                {
                    elev = qMax(0, getGMTEDelevation(GMTED2010buff, latlon.first, latlon.second));
                }
                else
                {
                    elev = qMax(0, m_elevation.getElevation(latlon.first, latlon.second));
                }
            }
            else
            {
                int tx_prev_z = 2*tx + ((x >= TILE_RESOLUTION/2) ? 1 : 0);
                int ty_prev_z = 2*ty + ((y >= TILE_RESOLUTION/2) ? 1 : 0);
                QString prev_filename = getFilename(zoom+1, tx_prev_z, ty_prev_z);

                // load sub-tile if not loaded
                if (prev_zoom_tiles.find(prev_filename) == prev_zoom_tiles.end())
                {
                    prev_zoom_tiles[prev_filename] = loadElevationTile(prev_filename);
                }

                qint16 elev00 = getElevationValueInElevationTile(prev_zoom_tiles[prev_filename], (x % (TILE_RESOLUTION/2))*2 + 0, (y % (TILE_RESOLUTION/2))*2 + 0);
                qint16 elev01 = getElevationValueInElevationTile(prev_zoom_tiles[prev_filename], (x % (TILE_RESOLUTION/2))*2 + 0, (y % (TILE_RESOLUTION/2))*2 + 1);
                qint16 elev10 = getElevationValueInElevationTile(prev_zoom_tiles[prev_filename], (x % (TILE_RESOLUTION/2))*2 + 1, (y % (TILE_RESOLUTION/2))*2 + 0);
                qint16 elev11 = getElevationValueInElevationTile(prev_zoom_tiles[prev_filename], (x % (TILE_RESOLUTION/2))*2 + 1, (y % (TILE_RESOLUTION/2))*2 + 1);
                elev = (qint16)(0.5 + (elev00+elev01+elev10+elev11)/4.0);
            }

            out << (qint16)elev;

            onlyZeros = (onlyZeros && (elev == 0));
        }
    }

    file.close();

    // il n'y a que des 0, pour gagner de la place, on supprime le fichier
    if (onlyZeros)
    {
        QFile file (tileFilename);
        file.remove();
    }
}

QString ElevationTiles::getFilenameDir(int zoom, int tx, int ty)
{
    Q_UNUSED(ty);

    QString tileFilename = m_cacheDir +"/elevation/"+ QString::number(zoom) +"/"+ QString::number(tx);
    return tileFilename;
}

QString ElevationTiles::getFilename(int zoom, int tx, int ty, const QString ext)
{
    QString tileFilename = getFilenameDir(zoom, tx, ty) +"/"+ QString::number(ty) + ext;
    return tileFilename;
}

std::vector<qint16> ElevationTiles::loadElevationTile(QString tileFilename)
{
    QFile myfile;
    myfile.setFileName(tileFilename);
    if(!myfile.open(QIODevice::ReadOnly))
    {
        // empty data means all zeros
        return std::vector<qint16>(0);
    }
    else
    {
        QDataStream data(&myfile);
        std::vector<qint16> result;

        while(!data.atEnd()) {
            qint16 elev;
            data >> elev;
            result.push_back(elev);
        }

        return result;
    }
}

bool fileExists(QString path) {
    QFileInfo check_file(path);
    // check if file exists and if yes: Is it really a file and no directory?
    if (check_file.exists() && check_file.isFile()) {
        return true;
    } else {
        return false;
    }
}

void ElevationTiles::computeAllTiles()
{
    qint32* GMTED2010buff = loadGMTEDdata("/Volumes/PARA2/elevation_GMTED2010/concatenated_by_python");

    for(int zoom=9; zoom>=5; zoom--)
    {
        int scaleFactor = powint(2, zoom-5);

        for (int tx=(15)*scaleFactor; tx<(18+1)*scaleFactor; tx++)
        {
            //for (int ty=(9-1)*scaleFactor; ty<(13)*scaleFactor; ty++)
            for (int ty=(9-2)*scaleFactor; ty<(9)*scaleFactor; ty++)
            {
                QString filenameDir  = getFilenameDir(zoom, tx, ty);
                QString tileFilename = getFilename(zoom, tx, ty);

                QDir dirCache(filenameDir);
                if (!dirCache.exists()) {
                    dirCache.mkpath(".");
                }
                if (true || !fileExists(tileFilename)) {
                    qDebug() << "computing..." << tileFilename;
                    computeTile(zoom, tx, ty, tileFilename, GMTED2010buff);
                }
            }
        }
    }

    delete [] GMTED2010buff;
}

Mountainess::Mountainess(QString cacheDir) : m_elevationTiles(cacheDir)
{
}

void Mountainess::loadTiles()
{
    const int zoom = MOUNTAINESS_TILES_ZOOM;
    const int scaleFactor = powint(2, zoom-5);

    for (int tx=(15)*scaleFactor; tx<(18+1)*scaleFactor; tx++)
    {
        for (int ty=(9-1)*scaleFactor; ty<(13)*scaleFactor; ty++)
        {
            qDebug() << "loading" << tx << ty;
            m_allElevationTiles[std::pair<int,int>(tx, ty)] = m_elevationTiles.loadElevationTile(m_elevationTiles.getFilename(zoom, tx, ty));
        }
    }
}

float Mountainess::computeMountainess(int tx, int ty, int x, int y)
{
    const int kernelHalfSize = 25*2;
    const float sigma = kernelHalfSize/1.75f;

    float maxElev   = 0.f;
    float sumElev   = 0.f;
    float sumWeight = 0.f;

    for (int dx=-kernelHalfSize; dx<=kernelHalfSize; dx++)
    {
        for (int dy=-kernelHalfSize; dy<=kernelHalfSize; dy++)
        {
            int tx_ = tx;
            int ty_ = ty;
            int  x_ = x + dx;
            int  y_ = y + dy;

            // déborde sur tile d'à côté
            if      (x_ < 0)                { x_ += TILE_RESOLUTION; tx_ -= 1; }
            else if (x_ >= TILE_RESOLUTION) { x_ -= TILE_RESOLUTION; tx_ += 1; }
            if      (y_ < 0)                { y_ += TILE_RESOLUTION; ty_ -= 1; }
            else if (y_ >= TILE_RESOLUTION) { y_ -= TILE_RESOLUTION; ty_ += 1; }


            qint16 elev = m_elevationTiles.getElevationValueInElevationTile(m_allElevationTiles[std::pair<int,int>(tx_, ty_)], x_, y_);

            float weight = exp(-(dx*dx+dy*dy)/(2.f*sigma*sigma));
            float felev  = weight * float(elev);
            sumWeight   += weight;
            sumElev     += felev;
            maxElev      = qMax(maxElev, felev);
        }
    }

    return maxElev - sumElev/sumWeight;
}

void Mountainess::computeAllMountainessTiles()
{
    const int zoom = MOUNTAINESS_TILES_ZOOM;
    const int scaleFactor = powint(2, zoom-5);

    ElevationTiles elevationTiles("/Users/antoine/GIT/paraglidable/tiler/CACHE");

    for (int tx=(15)*scaleFactor; tx<(18+1)*scaleFactor; tx++)
    {
        for (int ty=(9-1)*scaleFactor; ty<(13)*scaleFactor; ty++)
        {
            QString tileFilename = elevationTiles.getFilename(zoom, tx, ty, ".mountainess");
            qDebug() << "tileFilename" << tileFilename;
            QFile file(tileFilename);
            file.open(QIODevice::WriteOnly);
            QDataStream out(&file);

            for (int x=0; x<TILE_RESOLUTION; x++)
            {
                for (int y=0; y<TILE_RESOLUTION; y++)
                {
                    float mountainess = computeMountainess(tx, ty, x, y);
                    float m = qMax(0.f, qMin(1.f, mountainess/800.f));
                    out << quint8( m * float(std::numeric_limits<quint8>::max()) );
                }
            }

            file.close();
        }
    }
}

quint8 Mountainess::getMountainessValueInTile(std::vector<quint8> &data, int tx, int ty)
{
    if (data.size()==0 || tx>=TILE_RESOLUTION || ty>=TILE_RESOLUTION || tx<0 || ty<0) {
        return 0;
    } else {
        return data[tx*TILE_RESOLUTION + ty];
    }
}

std::vector<quint8> Mountainess::loadMountainessTile(QString tileFilename)
{
    QFile myfile;
    myfile.setFileName(tileFilename);
    if(!myfile.open(QIODevice::ReadOnly))
    {
        // empty data means all zeros
        return std::vector<quint8>(0);
    }
    else
    {
        QDataStream data(&myfile);
        std::vector<quint8> result;

        while(!data.atEnd()) {
            quint8 elev;
            data >> elev;
            result.push_back(elev);
        }

        return result;
    }
}
