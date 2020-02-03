#include <QCoreApplication>
#include <QImage>
#include <QFile>
#include <QDir>
#include <QDebug>
#include <QVector>
#include <QJsonDocument>
#include <QJsonObject>
#include <QVariantMap>
#include <QPixmap>
#include <QPainter>

#include <iostream>

#include <set>
#include <math.h>

#include "arguments.h"
#include "elevation.h"
#include "flights.h"
#include "tilesmath.h"

#define ALPHA_VALUE 160


class DataPoint
{
public:
    float lat, lon;
    std::vector<float> vals;
    int idp = 0;

    DataPoint()
    {

    }
    DataPoint(int idp, float lat, float lon, std::vector<float> vals)
    {
        this->idp  = idp;
        this->lat  = lat;
        this->lon  = lon;
        this->vals = vals;
    }
    DataPoint(float lat, float lon)
    {
        this->lat  = lat;
        this->lon  = lon;
    }
    QString toString() const
    {
        QString str = QString::number(lat) +" "+ QString::number(lon);
        for (int v=0; v<(int)vals.size(); v++)
            str += " "+ QString::number(vals[v]);
        return str;
    }

    static float distance(DataPoint dp1, DataPoint dp2)
    {
        //return fabs(dp1.lat-dp2.lat) + fabs(dp1.lon-dp2.lon);
        return (dp1.lat-dp2.lat)*(dp1.lat-dp2.lat) + (dp1.lon-dp2.lon)*(dp1.lon-dp2.lon);
    }
};

class DataPointComparison
{
    DataPoint refPoint;

public:

    DataPointComparison(float lat, float lon)
    {
        this->refPoint = DataPoint(lat, lon);
    }

    bool operator() (const DataPoint& dp1, const DataPoint& dp2)
    {
        float dist1 = DataPoint::distance(refPoint, dp1);
        float dist2 = DataPoint::distance(refPoint, dp2);
        return dist1 < dist2;
    }
};

class MapData
{
public:
    std::vector<DataPoint> m_points;
    std::vector<DataPoint> m_pointsTmpSorted;
    float minLat, maxLat, minLon, maxLon;


    MapData()
    {
        minLat =  100000.0f;
        maxLat = -100000.0f;
        minLon =  100000.0f;
        maxLon = -100000.0f;
    }

    bool readFile(QString filename)
    {
        m_points.clear();

        QFile file(filename);
        if(!file.open(QIODevice::ReadOnly)) {
            qDebug() << "ERR: could not open " << filename;
            return false;
        }

        QTextStream in(&file);
        int idp = 0;

        while(!in.atEnd())
        {
            QString line = in.readLine();
            QStringList fields = line.split(" ");
            if (fields.size() >= 3)
            {
                float lat  = fields[0].toFloat();
                float lon  = fields[1].toFloat();
                QVector<float> vals;
                for (int v=0; v<fields.size()-2; v++)
                {
                    vals.append(fields[v+2].toFloat());
                }

                m_points.push_back(DataPoint(idp, lat, lon, vals.toStdVector()));

                minLat = qMin(minLat, lat);
                maxLat = qMax(maxLat, lat);
                minLon = qMin(minLon, lon);
                maxLon = qMax(maxLon, lon);

                idp++;
            }

        }

        file.close();


        m_pointsTmpSorted = m_points;

        return true;
    }

    void printData()
    {
        qDebug() << m_points.size() << " points";
        for (int p=0; p<(int)m_points.size(); p++)
        {
            qDebug() << m_points[p].toString();
        }
    }

    std::vector<DataPoint> findClosests(float lat, float lon, int nbc)
    {
        std::sort(m_pointsTmpSorted.begin(), m_pointsTmpSorted.end(), DataPointComparison(lat, lon));
        return std::vector<DataPoint>(m_pointsTmpSorted.begin(), m_pointsTmpSorted.begin()+nbc);
    }

    std::vector<int> findCellCorners(float lat, float lon)
    {
        const bool verbose = false;
        const float epsilon = 0.00001;

        int pLatpLon = -1;
        int pLatmLon = -1;
        int mLatpLon = -1;
        int mLatmLon = -1;

        if (verbose) qDebug() << "0)";

        if (lat >= minLat-epsilon && lat <= maxLat+epsilon &&
            lon >= minLon-epsilon && lon <= maxLon+epsilon )
        {
            if (verbose) qDebug() << "1)";

            std::vector<DataPoint> closests = findClosests(lat, lon, 8);
            for (int c=0; c<(int)closests.size(); c++)
            {
                if (closests[c].lat <= lat) {
                    if (closests[c].lon <= lon) {
                        if (mLatmLon < 0) mLatmLon = closests[c].idp;
                    }
                    if (closests[c].lon >= lon) {
                        if (mLatpLon < 0) mLatpLon = closests[c].idp;
                    }
                }
                if (closests[c].lat >= lat) {
                    if (closests[c].lon <= lon) {
                        if (pLatmLon < 0) pLatmLon = closests[c].idp;
                    }
                    if (closests[c].lon >= lon) {
                        if (pLatpLon < 0) pLatpLon = closests[c].idp;
                    }
                }
            }
        }
        else {
            //qDebug() << "out";
        }

        std::vector<int> res(4);
        res[0] = mLatmLon;
        res[1] = mLatpLon;
        res[2] = pLatmLon;
        res[3] = pLatpLon;
        return res;
    }
};

bool betweenCorners(float lat, float lon, std::vector<DataPoint> &corners)
{
    if (corners[0].lat <= lat &&
        corners[0].lon <= lon &&

        corners[1].lat <= lat &&
        corners[1].lon >= lon &&

        corners[2].lat >= lat &&
        corners[2].lon <= lon &&

        corners[3].lat >= lat &&
        corners[3].lon >= lon)
        return true;
    else
        return false;
}

std::vector<float> linearInterpolation(float lat, float lon, std::vector<DataPoint> &corners)
{
    float dx = lon - corners[0].lon;
    float dy = lat - corners[0].lat;
    float Dx = corners[1].lon - corners[0].lon;
    float Dy = corners[2].lat - corners[0].lat;

    std::vector<float> vals;
    for (int v=0; v<(int)corners[0].vals.size(); v++)
    {
        float Dfx  = corners[1].vals[v] - corners[0].vals[v];
        float Dfy  = corners[2].vals[v] - corners[0].vals[v];
        float Dfxy = corners[0].vals[v] + corners[3].vals[v] - corners[1].vals[v] - corners[2].vals[v];

        vals.push_back(Dfx*dx/Dx + Dfy*dy/Dy + Dfxy*dx*dy/(Dx*Dy) + corners[0].vals[v]);
    }

    return vals;
}


class ValToColor
{
    std::vector<float> vals;
    std::vector<QRgb>  colors;

    QRgb hexToQRgb(QString str)
    {
        int r = str.mid(0,2).toInt(NULL, 16);
        int g = str.mid(2,2).toInt(NULL, 16);
        int b = str.mid(4,2).toInt(NULL, 16);
        return qRgb(r,g,b);
    }

public:
    ValToColor()
    {
        vals.push_back(0.0);
        vals.push_back(0.5);
        vals.push_back(1.0);

        colors.push_back(hexToQRgb("A00000"));
        colors.push_back(hexToQRgb("A07000"));
        colors.push_back(hexToQRgb("00A000"));
    }

    QRgb getColor(float val)
    {
        if (val < vals[0])
            val = vals[0];
        if (val > vals[vals.size()-1])
            val = vals[vals.size()-1];

        for (int v=0; v<(int)vals.size()-1; v++)
        {
            if (val <= vals[v+1])
            {
                float interp = (val - vals[v])/(float)(vals[v+1] - vals[v]);
                int colorRint = interp*(qRed  (colors[v+1])-qRed  (colors[v])) + qRed  (colors[v]) + 0.5;
                int colorGint = interp*(qGreen(colors[v+1])-qGreen(colors[v])) + qGreen(colors[v]) + 0.5;
                int colorBint = interp*(qBlue (colors[v+1])-qBlue (colors[v])) + qBlue (colors[v]) + 0.5;

                return qRgb(colorRint, colorGint, colorBint);
            }
        }
        return qRgb(0, 0, 0);
    }
};

float smoothstep(float x, float edge0, float edge1)
{
    float t = qMax(0.0f, qMin(1.0f, (x - edge0) / (edge1 - edge0) ));
    return t * t * (3.0 - 2.0 * t);
}

void drawFufu(QImage &img, int x, int y, float val)
{
#if 1
        int freq = 16.0;
        float rx = (float)x;
        float ry = (float)y;
        float mag = sin((rx/(float)TILE_RESOLUTION)*(2.0*M_PI)*freq)*sin((ry/(float)TILE_RESOLUTION)*(2.0*M_PI)*freq);
        mag = smoothstep(fabs(mag)*(val), 0.0, 1.0);

        //for (int i=0; i<=10; i++)
        //    qDebug() << i << smoothstep(i/10.0f, 0.0, 1.0);

#else
        int freq = 1.0/32.0*TILE_RESOLUTION;
        float rx = (x % freq) - freq/2.0 + 0.5;
        float ry = (y % freq) - freq/2.0 + 0.5;
        float mag = (val-0.5)*2.0*(1.0 - sqrt(rx*rx + ry*ry)/(freq/2.0 + 0.5)/(sqrt(2.0));
#endif

        QRgb pix = img.pixel(x, y);

        img.setPixel(x, y, qRgba((1.0-mag)*qRed(pix)   + mag*255,
                                 (1.0-mag)*qGreen(pix) + mag*255,
                                 (1.0-mag)*qBlue(pix)  + mag*255,
                                 qAlpha(pix) + (255-qAlpha(pix))*mag ));
}

// [x][y][i] -> (bl, sl)
std::vector< std::vector< std::vector< std::pair<int,int> > > > fillBordersHistoTile(std::vector< std::vector< std::pair<double,double> > > &borders, int tx, int ty)
{
    std::vector< std::vector< std::vector< std::pair<int,int> > > > histo(TILE_RESOLUTION);
    for (int x=0; x<TILE_RESOLUTION; x++) {
        histo[x].resize(TILE_RESOLUTION);
    }

    for (int bl=0; bl<(int)borders.size(); bl++)
    {
        for (int sl=1; sl<(int)borders[bl].size(); sl++)
        {
            float x1 = (borders[bl][sl-1].first  - tx)*TILE_RESOLUTION - 0.5;
            float y1 = (borders[bl][sl-1].second - ty)*TILE_RESOLUTION - 0.5;
            float x2 = (borders[bl][sl  ].first  - tx)*TILE_RESOLUTION - 0.5;
            float y2 = (borders[bl][sl  ].second - ty)*TILE_RESOLUTION - 0.5;

            if ( (x1 < 0 && x2 < 0) ||
                 (x1 >= TILE_RESOLUTION && x2 >= TILE_RESOLUTION) ||
                 (y1 < 0 && y2 < 0) ||
                 (y1 >= TILE_RESOLUTION && y2 >= TILE_RESOLUTION) )
                continue;

            std::pair<int,int> segment(bl, sl-1);

            // algo de tracé de segment:
            // https://fr.wikipedia.org/wiki/Analyseur_diff%C3%A9rentiel_num%C3%A9rique

            float longueur;
            if (fabs(x2-x1) >= fabs(y2-y1)) {
                longueur = fabs(x2-x1);
            } else {
                longueur = fabs(y2-y1);
            }

            float dx = (x2-x1) / longueur;
            float dy = (y2-y1) / longueur;
            float x = x1 + 0.5;
            float y = y1 + 0.5;
            int i = 0;
            while(i<=longueur) {
                int px = (int)x;
                int py = (int)y;
                if (px>=0 && px<TILE_RESOLUTION && py>=0 && py<TILE_RESOLUTION)
                    histo[px][py].push_back(segment);
                x += dx;
                y += dy;
                i++;
            }
        }
    }

    return histo;
}

float distance(float x1, float y1, float x2, float y2)
{
    float d2 = (x2-x1)*(x2-x1) + (y2-y1)*(y2-y1);
    return sqrt(d2);
}

float distancePointSegment(float x, float y, float x1, float y1, float x2, float y2)
{
    float sx = x2 - x1;
    float sy = y2 - y1;

    float ux = x - x1;
    float uy = y - y1;

    float dp = sx*ux + sy*uy;
    if (dp<0) return distance(x1, y1, x, y);

    float sn2 = sx*sx + sy*sy;
    if (dp>sn2) return distance(x2, y2, x, y);

    float ah2 = dp*dp / sn2;
    float un2 = ux*ux + uy*uy;
    return sqrt(un2 - ah2);
}

void drawBordersUsingHisto(QImage &img, std::vector< std::vector< std::pair<double,double> > > &borders, int tx, int ty)
{
    std::vector< std::vector< std::vector< std::pair<int,int> > > > bordersHisto = fillBordersHistoTile(borders, tx, ty);

    for (int x=0; x<TILE_RESOLUTION; x++)
    {
        for (int y=0; y<TILE_RESOLUTION; y++)
        {
            float minDist = 1000.0;
            std::set<int> bls; // pour distinguer frontieres entre 2 pays/ ou avec la mer

            for (int dx=-1; dx<=1; dx++)
            {
                for (int dy=-1; dy<=1; dy++)
                {
                    if (x+dx < 0 || x+dx >= TILE_RESOLUTION || y+dy < 0 || y+dy >= TILE_RESOLUTION)
                        continue;

                    if (bordersHisto[x+dx][y+dy].size() > 0)
                    {
                        for (int s=0; s<(int)bordersHisto[x+dx][y+dy].size(); s++)
                        {
                            std::pair<int,int> segment = bordersHisto[x+dx][y+dy][s];

                            bls.insert(segment.first);

                            float x1 = (borders[segment.first][segment.second  ].first  - tx)*TILE_RESOLUTION - 0.5;
                            float y1 = (borders[segment.first][segment.second  ].second - ty)*TILE_RESOLUTION - 0.5;
                            float x2 = (borders[segment.first][segment.second+1].first  - tx)*TILE_RESOLUTION - 0.5;
                            float y2 = (borders[segment.first][segment.second+1].second - ty)*TILE_RESOLUTION - 0.5;

                            float dist = distancePointSegment((float)x, (float)y, x1, y1, x2, y2);
                            if (dist<minDist)
                                minDist = dist;
                        }
                    }
                }

                float lineWidth = 1.65f;
                if (minDist < lineWidth && bls.size()>1)
                {
                    QRgb color = img.pixel(x, y);

                    img.setPixel(x, y, qRgba(qRed(color)  *(0.25*minDist/lineWidth + 0.75),
                                             qGreen(color)*(0.25*minDist/lineWidth + 0.75),
                                             qBlue(color) *(0.25*minDist/lineWidth + 0.75),
                                             ALPHA_VALUE //qMax(0, qMin(255, 255 - (int)(minDist/lineWidth*(255-ALPHA_VALUE)))) //qMax(0, 255 - (int)(minDist*255)) //qMax(0, 255 - (int)(minDist*255))
                                             ) );
                }
            }
        }
    }
}

/*
// simple aliazed version
void drawBorders(QImage &img, std::vector< std::vector< std::pair<double,double> > > &borders, int tx, int ty)
{
    QPainter p(&img);

    for (int bl=0; bl<(int)borders.size(); bl++)
    {
        if (bl%4==0)
            p.setPen(Qt::black);
        else if (bl%4==1)
            p.setPen(Qt::blue);
        else if (bl%4==2)
            p.setPen(Qt::green);
        else
            p.setPen(qRgba(255, 0, 0, 0));

        for (int sl=1; sl<(int)borders[bl].size(); sl++)
        {
            //qDebug() << borders[bl][sl-1].first << borders[bl][sl-1].second;
            double x1 = (borders[bl][sl-1].first  - tx)*TILE_RESOLUTION - 0.5;
            double y1 = (borders[bl][sl-1].second - ty)*TILE_RESOLUTION - 0.5;
            double x2 = (borders[bl][sl  ].first  - tx)*TILE_RESOLUTION - 0.5;
            double y2 = (borders[bl][sl  ].second - ty)*TILE_RESOLUTION - 0.5;
            p.drawLine(x1, y1, x2, y2);
        }
    }

    p.end();
}
*/

class Deco
{
public:
    float lat, lon, points;
    Deco()
    {
        lat = 45.4683264;
        lon = 5.9895125;
        points = 100.0f;
    }
    Deco(float lat, float lon, float points)
    {
        this->lat    = lat;
        this->lon    = lon;
        this->points = points;
    }
};

struct less_than_key
{
    inline bool operator() (const Deco& struct1, const Deco& struct2)
    {
        return (struct1.points > struct2.points);
    }
};

std::vector<Deco> readDecos(QString filename)
{
    std::vector<Deco> decos;

    QFile inputFile(filename);
    if (inputFile.open(QIODevice::ReadOnly))
    {
       QTextStream in(&inputFile);
       while (!in.atEnd())
       {
          QStringList line = in.readLine().split(",");

          if (line.size() == 3) {
              decos.push_back(  Deco(line[0].toFloat(),
                                     line[1].toFloat(),
                                     line[2].toFloat())  );
          }
       }
       inputFile.close();
    }


    // sorting

    std::sort(decos.begin(), decos.end(), less_than_key());

    return decos;
}

QRgb mixColors(QRgb c1, QRgb c2, float blend)
{
    int r1 = qRed  (c1);
    int g1 = qGreen(c1);
    int b1 = qBlue (c1);

    int r2 = qRed  (c2);
    int g2 = qGreen(c2);
    int b2 = qBlue (c2);

    return qRgb( (int)(r1*blend + r2*(1.f-blend) + 0.5f),
                 (int)(g1*blend + g2*(1.f-blend) + 0.5f),
                 (int)(b1*blend + b2*(1.f-blend) + 0.5f)  );
}
void drawDecos(QImage &img, std::vector<Deco> &decos, int zoom, int tx, int ty)
{
    float border = 1.0;
    QRgb borderColor = qRgb(0, 255, 255);
    QRgb fillColor   = qRgb(0,   0, 255);


    for (int d=0; d<(int)decos.size(); d++)
    {
        Deco &deco = decos[d];
        std::pair<double, double> pt   = MetersToPixels(LatLonToMeters(-deco.lat, deco.lon), zoom);

        float x = (pt.first   - tx)*TILE_RESOLUTION;
        float y = (pt.second  - ty)*TILE_RESOLUTION;
        float r = 1.0 + deco.points * 0.05;

        for (int xdx= (int)(x-r-border)-1; xdx<=(int)(x+r+border)+1; xdx++)
        {
            for (int ydy= (int)(y-r-border)-1; ydy<=(int)(y+r+border)+1; ydy++)
            {
                if (xdx >= 0 && ydy >= 0 && xdx < img.width() && ydy < img.height())
                {
                    QRgb color = img.pixel(xdx, ydy);
                    float distCenter = sqrt( (xdx - x)*(xdx - x) + (ydy - y)*(ydy - y) );
                    if (distCenter < r-border)
                    {
                        color = fillColor;
                    }
                    else if (distCenter <= r)
                    {
                        color = mixColors(borderColor, fillColor, (distCenter-(r-border))/border);
                    }
                    else if (distCenter <= r+border)
                    {
                        color = mixColors(color, borderColor, (distCenter-r)/border);
                    } else {
                        continue;
                    }

                    //img.setPixel(xdx, ydy, color);
                    img.setPixel(xdx, ydy, qRgba(qRed(color), qGreen(color), qBlue(color), 255));
                }
            }
        }
    }
}

void drawFlights(QImage &img, Flights &flights, int zoom, int tx, int ty)
{
    if (flights.size() == 0)
        return;

    QPainter painter(&img);
    painter.setPen(Qt::blue);

    for (int f=0; f<(int)flights.size(); f++)
    {
        for (int p=1; p<(int)flights.m_flights[f].size(); p++)
        {
            std::pair<double, double> ptm1 = MetersToPixels(LatLonToMeters(-flights.m_flights[f].m_track[p-1].lat, flights.m_flights[f].m_track[p-1].lon), zoom);
            std::pair<double, double> pt   = MetersToPixels(LatLonToMeters(-flights.m_flights[f].m_track[p  ].lat, flights.m_flights[f].m_track[p  ].lon), zoom);

            double x1 = (ptm1.first  - tx)*TILE_RESOLUTION - 0.5;
            double y1 = (ptm1.second - ty)*TILE_RESOLUTION - 0.5;
            double x2 = (pt.first    - tx)*TILE_RESOLUTION - 0.5;
            double y2 = (pt.second   - ty)*TILE_RESOLUTION - 0.5;
            painter.drawLine(x1, y1, x2, y2);
        }
    }

    painter.end();
}

// altitude -> pression
float nivellementBarometrique(float z)
{
    return 1013.25*pow((1.0 - (0.0065 * z)/288.15), 5.255);
}
// altitude -> pression knowing geopotentials
// geopotentials: [(altitude (m), pression), .. ]
float nivellementBarometrique(float z, std::vector< std::pair<float,float> > &geopotentials)
{
    if (z <= geopotentials[0].first)
    {
        return geopotentials[0].second;
    }
    else if (z >= geopotentials[geopotentials.size()-1].first)
    {
        return geopotentials[geopotentials.size()-1].second;
    }
    else
    {
        for (unsigned int kp=0; kp<(unsigned int)(geopotentials.size()-1); kp++)
        {
            if (z <= geopotentials[kp+1].first)
            {
                float z0     = geopotentials[kp  ].first;
                float p0     = geopotentials[kp  ].second;
                float z1     = geopotentials[kp+1].first;
                float p1     = geopotentials[kp+1].second;
                float interp = (z0 - z) / (z0 - z1);
                float interpolatedPression = interp*p1 + (1.0f-interp)*p0;

                return interpolatedPression;
            }
        }
    }

    return 0.0;
}
/*
 * TODO test pour le cache
 *
int readInt24(QDataStream* streamCache)
{
    qint16 head;
    uchar  tail;
    *streamCache >> head;
    *streamCache >> tail;
    return (((int)head) << 8) + (int)(unsigned int)tail;
}
void writeInt24(QDataStream* streamCache, int val)
{
    qint16 head = (val >> 8);
    uchar  tail = (val & 255);
    *streamCache << head;
    *streamCache << tail;
}
*/

void rename(QFile* file, QString newName)
{
    QFile newFile(newName);
    if (newFile.exists())
        newFile.remove();

    file->rename(newName);
}


float interpolateAltitude(float pression, std::vector<float> &vals)
{
    float fidx = (1000.0f - pression)/100.0f;
    const int maxIdx = 4;

    if (fidx < 0.0f)
        fidx = 0.0;
    else if (fidx > (float)maxIdx)
        fidx = (float)maxIdx;

    const int idx0 = qMax(0, qMin(maxIdx, (int)fidx  ));
    const int idx1 = qMax(0, qMin(maxIdx, (int)fidx+1));

    float interpolatedVal;
    if (idx0 != idx1)
        interpolatedVal = (fidx-idx0)*vals[idx1] + (1.0f-(fidx-idx0))*vals[idx0];
    else
        interpolatedVal = vals[idx0];

    return interpolatedVal;
}

void drawTile(int zoom, int tx, int ty,
              int xMin, int xMax,
              int yMin, int yMax,
              std::vector<int> &shifts, MapData &mapData,
              QString tilePath,     // PNG tile
              QString dataTilePath, // data tile for API, can be empty
              bool drawPngTiles,
              QString baseCacheDir,
              std::vector< std::vector< std::pair<double,double> > > &borders_this_zoom,
              Flights &flights,
              std::vector<Deco> &decos,
              QString backgroundTilesDir = "",
              bool alsoSaveTranspa=false)
{
    const bool verbose = false;
    const bool generateDataTile = !dataTilePath.isEmpty();

    // Load elevation for this tile
    ElevationTiles elevationTiles(baseCacheDir);
    Mountainess    mountainessTiles(baseCacheDir);
    std::vector<qint16> elevationData   = elevationTiles.loadElevationTile    (elevationTiles.getFilename(zoom, tx, ty));
    std::vector<quint8> mountainessData = mountainessTiles.loadMountainessTile(elevationTiles.getFilename(zoom, tx, ty, ".mountainess"));

    QString cacheFile = QString("%1/%2/%3/%4/%5_%6_%7_%8_%9").arg(baseCacheDir).arg(TILE_RESOLUTION).arg(zoom).arg(tx).arg(ty).arg(xMin).arg(xMax).arg(yMin).arg(yMax);
    QString cacheDir  = QFileInfo(cacheFile).dir().path();

    ValToColor valToColor;

    std::vector<int> corners(0);
    std::vector<DataPoint> cornersData(0);


    //=======================================================
    // Create tile directory
    // Must be done before opening any file
    //=======================================================
    {
        QFileInfo finfo(tilePath);
        QDir dir(finfo.dir().path());
        if (!dir.exists()) {
            dir.mkpath(".");
        }
    }


    //==================>
    QFileInfo fileInfo(cacheFile);
    bool updateThisCacheFile = (!fileInfo.exists() || (fileInfo.size()==0));
    QFile* fileCache;
    QDataStream* streamCache;
    if (updateThisCacheFile)
    {
        QDir dirCache(cacheDir);
        if (!dirCache.exists()) {
            dirCache.mkpath(".");
        }
        fileCache = new QFile(cacheFile+"_TMP"); // renamed at the end
        fileCache->open(QIODevice::WriteOnly);
    }
    else
    {
        fileCache = new QFile(cacheFile);
        fileCache->open(QIODevice::ReadOnly);
    }
    streamCache = new QDataStream(fileCache);
    //==================>


    QFile*       fileDataTile   = NULL;
    QDataStream* streamDataTile = NULL;
    if (generateDataTile)
    {
        fileDataTile = new QFile(dataTilePath +"_TMP"); // renamed at the end
        if (!fileDataTile->open(QIODevice::WriteOnly)) {
            qDebug() << "Could not open "<< dataTilePath +"_TMP";
            exit(1);
        }
        streamDataTile = new QDataStream(fileDataTile);
    }

    QImage img(xMax-xMin, yMax-yMin, QImage::Format_ARGB32);

    if (drawPngTiles)
        img.fill(qRgba(255,255,255, 0));

    for (int x=xMin; x<xMax; x++)
    {
        for (int y=yMin; y<yMax; y++)
        {
            //======================================
            // 4 cell corners for this pixel tile
            //======================================

            double dx = tx + ((double)x+0.5)/((double)TILE_RESOLUTION);
            double dy = ty + ((double)y+0.5)/((double)TILE_RESOLUTION);
            std::pair<float, float> latlon = tilePixelToLatLon(dx, dy, zoom);

            //==================>
            if (updateThisCacheFile)
            {
                if (cornersData.size() == 0 || !betweenCorners(latlon.first, latlon.second, cornersData))
                {
                    if (cornersData.size() == 4)
                    {
                        bool found = false;

                        // try to translate all the corners points in +1 ilat
                        for (int s=0; s<(int)shifts.size(); s++)
                        {
                            std::vector<int> newCorners = corners;
                            for (int c=0; c<4; c++)
                                newCorners[c] = corners[c]+shifts[s];

                            if (newCorners[0] >= (int)mapData.m_points.size() || newCorners[0]<0) continue;
                            if (newCorners[1] >= (int)mapData.m_points.size() || newCorners[1]<0) continue;
                            if (newCorners[2] >= (int)mapData.m_points.size() || newCorners[2]<0) continue;
                            if (newCorners[3] >= (int)mapData.m_points.size() || newCorners[3]<0) continue;

                            std::vector<DataPoint> newcornersData(4);
                            newcornersData[0] = mapData.m_points[newCorners[0]];
                            newcornersData[1] = mapData.m_points[newCorners[1]];
                            newcornersData[2] = mapData.m_points[newCorners[2]];
                            newcornersData[3] = mapData.m_points[newCorners[3]];

                            if (betweenCorners(latlon.first, latlon.second, newcornersData))
                            {
                                corners = newCorners;
                                found = true;
                                break;
                            }
                        }

                        if (!found)
                        {
                            if (verbose) qDebug() << "D";

                            int corners0avant = corners[0];
                            // slow brute force algo
                            corners = mapData.findCellCorners(latlon.first, latlon.second);
                            if (!(corners[0] == -1 || corners[1] == -1 || corners[2] == -1 || corners[3] == -1))
                                shifts.push_back(corners[0] - corners0avant);
                        }
                    }
                    else
                    {
                        if (verbose) qDebug() << "E";

                        // slow brute force algo
                        corners = mapData.findCellCorners(latlon.first, latlon.second);
                    }
                }

                *streamCache << corners[0];
                *streamCache << corners[1];
                *streamCache << corners[2];
                *streamCache << corners[3];
            }
            else
            {
                corners.resize(4);
                *streamCache >> corners[0];
                *streamCache >> corners[1];
                *streamCache >> corners[2];
                *streamCache >> corners[3];
            }
            //==================>

            if (corners[0] == -1 || corners[1] == -1 || corners[2] == -1 || corners[3] == -1)
                continue;

            //======================================
            // val for this tile pixel
            //======================================

            cornersData.resize(4);
            cornersData[0] = mapData.m_points[corners[0]];
            cornersData[1] = mapData.m_points[corners[1]];
            cornersData[2] = mapData.m_points[corners[2]];
            cornersData[3] = mapData.m_points[corners[3]];

            std::vector<float> vals = linearInterpolation(latlon.first, latlon.second, cornersData);

            //======================================
            // Set pixel color
            //======================================
#if 0
            //vals[0] = elevationTiles.getElevationValueInElevationTile(elevationData, x, y)/3000.0f;
            //vals[1] = 0;
            QRgb color = valToColor.getColor(vals[0]);

#elif 0 // when rgb values are directly given instead of prediction

            QRgb color = qRgb(qMax(0.0f,qMin(255.0f,vals[0]*20)),
                              qMax(0.0f,qMin(255.0f,vals[1]*20)),
                              qMax(0.0f,qMin(255.0f,vals[2]*20)));
#else
            int elev = elevationTiles.getElevationValueInElevationTile(elevationData, x, y);

            const float MIN_ALTITUDE  = 600.0f;
            const float ADD_ELEVATION = 400.0f;

            elev = qMax((float)(elev+ADD_ELEVATION), MIN_ALTITUDE);

            std::vector< std::pair<float,float> > geopotentials;
            geopotentials.push_back(std::pair<float,float>(vals[0], 1000.0f));
            geopotentials.push_back(std::pair<float,float>(vals[1],  900.0f));
            geopotentials.push_back(std::pair<float,float>(vals[2],  800.0f));
            geopotentials.push_back(std::pair<float,float>(vals[3],  700.0f));
            geopotentials.push_back(std::pair<float,float>(vals[4],  600.0f));
            float pression = nivellementBarometrique(qMax((float)elev, MIN_ALTITUDE), geopotentials);

            std::vector<float> windAngles;
            for (int alt=0; alt<5; alt++)
            {
                float U = vals[18+alt];
                float V = vals[23+alt];
                float angle = atan2(V, U);

                if (alt > 0)
                {
                    if (windAngles[alt-1] < angle - M_PI)
                    {
                        angle -= 2.0*M_PI;
                    }
                    else if (windAngles[alt-1] > angle + M_PI)
                    {
                        angle += 2.0*M_PI;
                    }
                }
                windAngles.push_back(angle);
            }

            std::vector<float> valsFlyabilityAltitude        = std::vector<float>(vals.begin() +  5, vals.begin() +  5 + 5);
            std::vector<float> valsWindFlyabilityAltitude    = std::vector<float>(vals.begin() + 11, vals.begin() + 11 + 5);

            const float interpolatedVal       = interpolateAltitude(pression, valsFlyabilityAltitude);
            const float interpolateWindVal    = interpolateAltitude(pression, valsWindFlyabilityAltitude);
            const float fufuVal               = vals[10];
            const float interpolateWindAngle  = interpolateAltitude(pression, windAngles);

            const float minPossibleAngle = -2.0*M_PI;
            const float maxPossibleAngle =  2.0*M_PI;

            if (generateDataTile)
            {
                if (!fileDataTile->isOpen())
                {
                    qDebug() << "!fileDataTile->isOpen() before *streamDataTile << (uchar)( ... );";
                    exit(1);
                }
                *streamDataTile << (uchar)( qMax(0, qMin(255, (int)(0.5 + interpolatedVal       * 255.0f))) ); // flyability at point altitude
                *streamDataTile << (uchar)( qMax(0, qMin(255, (int)(0.5 + fufuVal               * 255.0f))) ); // fufu at usual altitude
                *streamDataTile << (uchar)( qMax(0, qMin(255, (int)(0.5 + interpolateWindVal    * 255.0f))) ); // wind
                *streamDataTile << (uchar)( qMax(0, qMin(255, (int)(0.5 + vals[16]              * 255.0f))) ); // precipitation
                *streamDataTile << (uchar)( qMax(0, qMin(255, (int)(0.5 + vals[27]              * 255.0f))) ); // Attractiveness
                *streamDataTile << (uchar)( qMax(0, qMin(255, (int)(0.5 + (interpolateWindAngle-minPossibleAngle)/(maxPossibleAngle-minPossibleAngle) * 255.0f))) ); // Attractiveness
            }
#endif
            if (drawPngTiles)
            {
#if 0 // draw wind direction (validated)

                if (x%21==10 && y%21==10)
                {
                    QPainter painter;
                    painter.begin(&img);
                    painter.setPen(Qt::red);

                    int wx1 = -cos(interpolateWindAngle)*10;
                    int wy1 =  sin(interpolateWindAngle)*10;

                    painter.drawLine(qMax(xMin, qMin(xMax-1, x + wx1)),
                                     qMax(yMin, qMin(yMax-1, y + wy1)),
                                     qMax(xMin, qMin(xMax-1, x - wx1)),
                                     qMax(yMin, qMin(yMax-1, y - wy1)) );

                    for (int ddx=-2; ddx<=2; ddx++)
                    {
                        for (int ddy=-2; ddy<=2; ddy++)
                        {
                            img.setPixel(qMax(xMin, qMin(xMax-1, x + wx1 + ddx)),
                                         qMax(yMin, qMin(yMax-1, y + wy1 + ddy)),
                                         qRgb(255, 0, 0));
                        }
                    }
                }

#else
                QRgb color;
                if (false) // DEBUG: elevation
                {
                    color = valToColor.getColor((float)elev/400.0f);
                }
                else if (false) // DEBUG: mountainess
                {
                    if (zoom == MOUNTAINESS_TILES_ZOOM)
                    {
                        quint8 m = mountainessTiles.getMountainessValueInTile(mountainessData, x, y);
                        color = valToColor.getColor(float(m)/255.f);
                        //qDebug() << m;
                    }
                }
                else // flyability prediction
                {
                    color = valToColor.getColor(interpolatedVal);
                }

                // flyability
                img.setPixel(x-xMin, y-yMin, qRgba(qRed(color), qGreen(color), qBlue(color), ALPHA_VALUE));

                // fufu
                drawFufu(img, x-xMin, y-yMin, fufuVal);
#endif
            }
        }
    }

    //---------------------------------------------------------------------------
    // Borders
    //---------------------------------------------------------------------------

    if (drawPngTiles)
        drawBordersUsingHisto(img, borders_this_zoom, tx, ty);

    //---------------------------------------------------------------------------
    // Flights
    //---------------------------------------------------------------------------

    if (drawPngTiles)
        drawFlights(img, flights, zoom, tx, ty);

    //---------------------------------------------------------------------------
    // Decos
    //---------------------------------------------------------------------------

    if (drawPngTiles)
        drawDecos(img, decos, zoom, tx, ty);

    //---------------------------------------------------------------------------
    // Background tiles
    //---------------------------------------------------------------------------

    if (drawPngTiles && !backgroundTilesDir.isEmpty())
    {
        //---------------------------------------------------------------------------
        // Save transpa version before adding background
        //---------------------------------------------------------------------------

        if (alsoSaveTranspa)
        {
            QString tilePathTranspa = tilePath;
            tilePathTranspa.replace(".png", "_transpa.png");
            img.save(tilePathTranspa);
        }

        //---------------------------------------------------------------------------
        // Compute background version
        //---------------------------------------------------------------------------

        for (int btx = tx; btx <= tx + (xMax-1)/TILE_RESOLUTION; btx++)
        {
            for (int bty = ty; bty <= ty + (yMax-1)/TILE_RESOLUTION; bty++)
            {
                QString filename = backgroundTilesDir +"/"+ QString::number(zoom) +"/"+ QString::number(btx) +"/"+ QString::number(bty) +".png";
                QFile f(filename);

                if(f.exists())
                {
                    QImage imgBackground(filename);

                    for (int x=0; x<TILE_RESOLUTION; x++)
                    {
                        for (int y=0; y<TILE_RESOLUTION; y++)
                        {
                            int x_img = x - xMin + TILE_RESOLUTION*(btx-tx);
                            int y_img = y - yMin + TILE_RESOLUTION*(bty-ty);

                            if (x_img>=0 && x_img<img.width() && y_img>=0 && y_img<img.height())
                            {
                                QRgb foregroundPix = img.pixel(x_img, y_img);
                                QRgb backgroundPix = imgBackground.pixel(x, y);

                                int grayVal = (qRed(backgroundPix)+qGreen(backgroundPix)+qBlue(backgroundPix)) / 3;

                                float r = (qRed  (foregroundPix) * ALPHA_VALUE + (255-ALPHA_VALUE)*grayVal) / 255.0f;
                                float g = (qGreen(foregroundPix) * ALPHA_VALUE + (255-ALPHA_VALUE)*grayVal) / 255.0f;
                                float b = (qBlue (foregroundPix) * ALPHA_VALUE + (255-ALPHA_VALUE)*grayVal) / 255.0f;

                                QRgb blendedPix = qRgb( qRound(r), qRound(g), qRound(b) );

                                img.setPixel(x_img, y_img, blendedPix);
                            }
                        }
                    }
                }
            }
        }
    }

    //---------------------------------------------------------------------------
    // Write file
    //---------------------------------------------------------------------------

    qDebug() << tilePath;
    if (drawPngTiles)
        img.save(tilePath);

    //---------------------------------------------------------------------------
    // Commit cache file
    //---------------------------------------------------------------------------
    if (updateThisCacheFile) {
        rename(fileCache, cacheFile);
    }
    fileCache->close();
    delete fileCache;
    delete streamCache;

    //---------------------------------------------------------------------------
    // Commit data tile file
    //---------------------------------------------------------------------------

    if (generateDataTile)
    {
        rename(fileDataTile, dataTilePath);
        fileDataTile->close();
        delete fileDataTile;
        delete streamDataTile;
    }
}

void addLatLon(QVariantList ptvariant, std::vector< std::pair<double,double> > &segmentsString)
{
    double lat = ptvariant[1].toDouble();
    double lon = ptvariant[0].toDouble();

    segmentsString.push_back(std::pair<double,double>(lat, lon));
}

std::vector< std::vector< std::pair<double,double> > > loadGeoJson(QString filename)
{
    std::vector< std::vector< std::pair<double,double> > > allSegmentsStrings;

    if (filename.isEmpty())
        return allSegmentsStrings;

    QString content;

    QFile file(filename);
    file.open(QIODevice::ReadOnly | QIODevice::Text);
    content = file.readAll();
    file.close();

    QJsonDocument doc = QJsonDocument::fromJson(content.toUtf8());

    //get the jsonObject
    QJsonObject jObject = doc.object();

    //convert the json object to variantmap
    QVariantMap mainMap = jObject.toVariantMap();

    QList<QVariant> listCountries = mainMap["features"].toList();


    for (int country=0; country<listCountries.size(); country++)
    {
        QVariantMap countryMap = listCountries[country].toMap();

        qDebug() << countryMap["properties"].toMap()["sovereignt"];

        QVariantList geo = countryMap["geometry"].toMap()["coordinates"].toList();

        for (int igeo=0; igeo<geo.size(); igeo++)
        {
/*

// qd ya qu'une liste de segments pour le pays:

"coordinates":[

    [
        [
            28.591929559043194,
            69.06477692328666
        ],
        [


// qd ya plusieurs listes de segments pour le pays

"coordinates":[

[
    [
        [
            -52.55642473001839,
            2.504705308437053
        ],

        ...

        [
            -52.55642473001839,
            2.504705308437053
        ]
    ]

],
[

    [
        [
            9.560016310269134,
            42.15249197037957
        ],
*/

            QVariantList lstPts = geo[igeo].toList();
            std::vector< std::pair<double,double> > segmentsString;

            for (int pt=0; pt<lstPts.size(); pt++)
            {
                QVariantList list = lstPts[pt].toList();

                if (!list[0].canConvert(QMetaType::Double))
                {
                    std::vector< std::pair<double,double> > segmentsString;

                    for (int pt2=0; pt2<list.size(); pt2++)
                    {
                        QVariantList lstPts2 = list[pt2].toList();
                        addLatLon(lstPts2, segmentsString);
                    }

                    if (segmentsString.size() > 1)
                        allSegmentsStrings.push_back(segmentsString);
                }
                else
                {
                    addLatLon(list, segmentsString);
                }
            }

            if (segmentsString.size() > 1)
                allSegmentsStrings.push_back(segmentsString);
        }
    }

    return allSegmentsStrings;
}

std::vector< std::vector< std::pair<double,double> > > convertBordersCoords(std::vector< std::vector< std::pair<double,double> > > borders, int zoom)
{
    std::vector< std::vector< std::pair<double,double> > > converted_borders;

    for (int bl=0; bl<(int)borders.size(); bl++)
    {
        converted_borders.push_back( std::vector< std::pair<double,double> >(0) );

        for (int sl=0; sl<(int)borders[bl].size(); sl++)
        {
            std::pair<double,double> pt = MetersToPixels(LatLonToMeters(-borders[bl][sl].first, borders[bl][sl].second), zoom);

            converted_borders[bl].push_back(pt);
        }
    }

    return converted_borders;
}

void drawLegende(QString filename1, QString filename2, QString filename3)
{
    ValToColor valToColor;

    //======================================================
    // draw volabilite
    //======================================================

    if (!filename1.isEmpty())
    {
        QImage img(256+1, 32+1, QImage::Format_ARGB32);

        for (int x=0; x<img.width(); x++)
        {
            float val = (float)x/(float)(img.width()-1);
            QRgb color = valToColor.getColor(val);

            for (int y=0; y<img.height(); y++)
            {
                img.setPixel(x, y, qRgba(qRed(color), qGreen(color), qBlue(color), ALPHA_VALUE));
            }
        }

        img.save(filename1);
    }

    //======================================================
    // draw fufu
    //======================================================

    if (!filename2.isEmpty())
    {
        QImage img(256+1, 32+1, QImage::Format_ARGB32);
        QRgb color = valToColor.getColor(1.0);

        for (int x=0; x<img.width(); x++)
        {
            float val = (float)x/(float)(img.width()-1);

            for (int y=0; y<img.height(); y++)
            {
                img.setPixel(x, y, qRgba(qRed(color), qGreen(color), qBlue(color), ALPHA_VALUE));
                drawFufu(img, x, y, val);
            }
        }

        img.save(filename2);
    }

    //======================================================
    // fufu pattern
    //======================================================

    if (!filename3.isEmpty())
    {
        QImage imgFufuPattern(16*4+1, 16*4+1, QImage::Format_ARGB32);
        imgFufuPattern.fill(qRgba(255,255,255,0));

        for (int x=0; x<imgFufuPattern.width(); x++)
        {
            for (int y=0; y<imgFufuPattern.height(); y++)
            {
                drawFufu(imgFufuPattern, x, y, 1.0);
            }
        }

        imgFufuPattern.save(filename3);
    }
}

void setProgress(int percent, QString progressFile)
{
    if (progressFile.isEmpty())
        return;

    QFile file(progressFile);
    if (file.open(QIODevice::WriteOnly))
    {
        QTextStream stream(&file);
        stream << percent;
        file.close();
    }
}

struct TileCoord
{
    int z, tx, ty;
    TileCoord(int z, int tx, int ty)
    {
        this->z  = z;
        this->tx = tx;
        this->ty = ty;
    }
    TileCoord() {}
};

// skippedTiles[zoom][tx][ty] = true
std::vector<TileCoord> loadSkippedTiles(QString filename)
{
    QFile myTextFile(filename);

    if (myTextFile.open(QIODevice::ReadOnly))
    {
        std::vector<TileCoord> res;
        while(!myTextFile.atEnd())
        {
            QString line = myTextFile.readLine();

            QStringList lst = line.split(" ");
            if (lst.size()==3) {
                int z  = lst[0].toInt();
                int tx = lst[1].toInt();
                int ty = lst[2].toInt();
                std::cout << "skippedTiles: " << z << " " << tx << " " << ty << std::endl;

                res.push_back(TileCoord(z, tx, ty));
            }
        }
        myTextFile.close();
        return res;
    }

    return std::vector<TileCoord>(0);
}


int main(int argc, char *argv[])
{
#if 0
    {
        Mountainess mountainess("/Users/antoine/GIT/paraglidable/tiler/CACHE");
        mountainess.loadTiles();
        mountainess.computeAllMountainessTiles();
        return 0;
    }
#endif

#if 0
    drawLegende("/tmp/legend1.png", "/tmp/legend2.png", "/tmp/legend3.png");
    return 0;
#endif

// Compute elevation values for each tile pixel
// Must be computed ones and copied on the server
#if 0
    ElevationTiles elevationTiles("/Users/antoine/GIT/paraglidable/tiler/CACHE");
    elevationTiles.computeAllTiles();
    exit(0);
#endif

    if (argc != 2)
    {
        qDebug() << "ERROR: no JSON argument file given";
        exit(1);
    }

    Arguments arguments(argv[1]);
    arguments.print();


#if DRAW_FLIGHTS // test
    QDir directory("/Volumes/PARAGLIDABL/tracks/CFD/002/");
    QFileInfoList tracks = directory.entryInfoList(QStringList() << "*.igc", QDir::Files);
    QStringList absolutePaths;
    for (int t=0; t<tracks.size(); t++)
        absolutePaths << tracks[t].absoluteFilePath();
    Flights flights(absolutePaths);
#else
    Flights flights;
#endif

    // Load prediction
    MapData mapData;
    if (!arguments.m_predictionFilename.isEmpty())
        mapData.readFile(arguments.m_predictionFilename);

    // Load borders
    std::vector< std::vector< std::pair<double,double> > > borders;
    if (!arguments.m_bordersFilename.isEmpty())
        borders = loadGeoJson(arguments.m_bordersFilename);

    // Load takes off
    std::vector<Deco> decos;
    if (!arguments.m_takesOffFilename.isEmpty())
        decos = readDecos(arguments.m_takesOffFilename);

    std::vector<TileCoord> skippedTiles;
    if (!arguments.m_skippedTiles.isEmpty())
        skippedTiles = loadSkippedTiles(arguments.m_skippedTiles);

    //=====================================================================
    // Draw legend images
    //=====================================================================

    if (!arguments.m_legendImg1.isEmpty() ||
        !arguments.m_legendImg2.isEmpty() ||
        !arguments.m_legendImg3.isEmpty()  )
    {
        drawLegende(arguments.m_legendImg1, arguments.m_legendImg2, arguments.m_legendImg3);
    }

    //=====================================================================
    // Generate tiles
    //=====================================================================

    if (!arguments.m_tilesDir.isEmpty())
    {
        //---------------------------------------
        // Vignette
        //---------------------------------------
        {
            std::vector<int> shifts(1, 1);
            int zoom = 5;

            // borders
            std::vector< std::vector< std::pair<double,double> > > borders_this_zoom;
            if (zoom >= arguments.m_minBordersZoom && zoom <= arguments.m_maxBordersZoom)
                borders_this_zoom = convertBordersCoords(borders, zoom);

            drawTile(zoom, 15, 10,
                     114, TILE_RESOLUTION*4 - 233,
                     127, TILE_RESOLUTION*3 - 234,
                     shifts, mapData,
                     arguments.m_tilesDir + "/vignette.png",
                     "",
                     arguments.m_drawPngTiles,
                     arguments.m_cacheDir,
                     borders_this_zoom,
                     flights,
                     decos,
                     arguments.m_backgroundTiles,
                     false);
        }

        //---------------------------------------
        // Tiles
        //---------------------------------------

        for (int zoom=arguments.m_minZoom; zoom<=arguments.m_maxZoom; zoom++)
        {
            if (arguments.m_maxZoom > arguments.m_minZoom)
                setProgress(25 + ((zoom-arguments.m_minZoom)*(70-25))/(arguments.m_maxZoom-arguments.m_minZoom), arguments.m_progressFilename);

            // borders
            std::vector< std::vector< std::pair<double,double> > > borders_this_zoom;
            if (zoom >= arguments.m_minBordersZoom && zoom <= arguments.m_maxBordersZoom)
                borders_this_zoom = convertBordersCoords(borders, zoom);

            int scaleFactor = powint(2, zoom-5);
            std::vector<int> shifts(1, 1);

            for (int tx=(15)*scaleFactor; tx<(18+1)*scaleFactor; tx++)
            {
                for (int ty=(9-1)*scaleFactor; ty<(13)*scaleFactor; ty++)
                {
                    // Check if this tile must be skipped
                    bool skip = false;
                    for (unsigned int t=0; t<skippedTiles.size(); t++)
                    {
                        if (zoom==skippedTiles[t].z && tx==skippedTiles[t].tx && ty==skippedTiles[t].ty) {
                            skip = true;
                            break;
                        }
                    }
                    if (skip) {
                        continue;
                    }

                    QString tilePath = QString("%1/%2/%3/%4.png").arg(arguments.m_tilesDir).arg(zoom).arg(tx).arg(ty);
                    drawTile(zoom, tx, ty,
                             0, TILE_RESOLUTION,
                             0, TILE_RESOLUTION,
                             shifts, mapData,
                             tilePath,
                             zoom==7 ? QString(tilePath).replace(".png", ".data") : "",
                             arguments.m_drawPngTiles,
                             arguments.m_cacheDir,
                             borders_this_zoom,
                             flights,
                             decos,
                             arguments.m_backgroundTiles,
                             arguments.m_generateTranspaVersion);//zoom==arguments.m_maxZoom); // also save transparent version if backgroundTiles not empty
                }
            }
        }
    }

    return 0;
}
