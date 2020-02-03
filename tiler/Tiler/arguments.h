#ifndef ARGUMENTS_H
#define ARGUMENTS_H

#include <QVariantMap>
#include <QString>

class Arguments
{
public:
    QString m_predictionFilename;
    QString m_cacheDir;
    QString m_progressFilename;
    QString m_bordersFilename;
    int     m_minBordersZoom;
    int     m_maxBordersZoom;
    QString m_takesOffFilename;
    QString m_backgroundTiles;
    QString m_legendImg1;
    QString m_legendImg2;
    QString m_legendImg3;
    QString m_tilesDir;
    int     m_minZoom;
    int     m_maxZoom;
    bool    m_drawPngTiles;
    QString m_skippedTiles;
    bool    m_generateTranspaVersion;

    Arguments(QString jsonFilename);
    void print();
};

#endif // ARGUMENTS_H
