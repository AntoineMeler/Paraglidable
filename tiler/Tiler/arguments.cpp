#include <QJsonDocument>
#include <QJsonObject>
#include <QDebug>

#include "arguments.h"
#include "lib.h"

QString getOptionalArgumentString(QVariantMap &mainMap, QString argName, QString defaultValue)
{
    if (mainMap.find(argName) != mainMap.end())
    {
        return mainMap[argName].toString();
    }
    else
    {
        return defaultValue;
    }
}

bool getOptionalArgumentBool(QVariantMap &mainMap, QString argName, bool defaultValue)
{
    if (mainMap.find(argName) != mainMap.end())
    {
        return mainMap[argName].toBool();
    }
    else
    {
        return defaultValue;
    }
}
int getOptionalArgumentInt(QVariantMap &mainMap, QString argName, int defaultValue)
{
    if (mainMap.find(argName) != mainMap.end())
    {
        return mainMap[argName].toInt();
    }
    else
    {
        return defaultValue;
    }
}

QString getMandatoryArgumentString(QVariantMap &mainMap, QString argName)
{
    if (mainMap.find(argName) != mainMap.end())
    {
        return mainMap[argName].toString();
    }
    else
    {
        qDebug() << "ERROR: could not find argument" << argName;
        exit(1);
    }
}

Arguments::Arguments(QString jsonFilename)
{
    QString content = readFile(jsonFilename);

    QJsonDocument doc = QJsonDocument::fromJson(content.toUtf8());
    QJsonObject jObject = doc.object();
    QVariantMap mainMap = jObject.toVariantMap();

    // Optional arguments
    m_predictionFilename = getOptionalArgumentString(mainMap, "predictionFilename", "");
    m_tilesDir           = getOptionalArgumentString(mainMap, "tilesDir",           "");
    m_drawPngTiles       = getOptionalArgumentBool  (mainMap, "drawPngTiles",     true);
    m_minZoom            = getOptionalArgumentInt   (mainMap, "minZoom",            -1);
    m_maxZoom            = getOptionalArgumentInt   (mainMap, "maxZoom",            -1);
    m_cacheDir           = getOptionalArgumentString(mainMap, "cacheDir",           "");

    m_progressFilename   = getOptionalArgumentString(mainMap, "progressFilename",   "");
    m_bordersFilename    = getOptionalArgumentString(mainMap, "bordersFilename",    "");
    m_minBordersZoom     = getOptionalArgumentInt   (mainMap, "minBordersZoom",     -1);
    m_maxBordersZoom     = getOptionalArgumentInt   (mainMap, "maxBordersZoom",     -1);
    m_takesOffFilename   = getOptionalArgumentString(mainMap, "takesOffFilename",   "");
    m_backgroundTiles    = getOptionalArgumentString(mainMap, "backgroundTiles",    "");
    m_skippedTiles       = getOptionalArgumentString(mainMap, "skippedTiles",       "");

    m_legendImg1         = getOptionalArgumentString(mainMap, "legendImg1",         "");
    m_legendImg2         = getOptionalArgumentString(mainMap, "legendImg2",         "");
    m_legendImg3         = getOptionalArgumentString(mainMap, "legendImg3",         "");

    m_generateTranspaVersion = getOptionalArgumentBool(mainMap, "generateTranspaVersion", true);
}

void Arguments::print()
{
    qDebug() << "predictionFilename:  " << m_predictionFilename;
    qDebug() << "tilesDir:            " << m_tilesDir;
    qDebug() << "minZoom:             " << m_minZoom;
    qDebug() << "maxZoom:             " << m_maxZoom;
    qDebug() << "cacheDir:            " << m_cacheDir;

    qDebug() << "progressFilename:    " << m_progressFilename;
    qDebug() << "bordersFilename:     " << m_bordersFilename;
    qDebug() << "minBordersZoom:      " << m_minBordersZoom;
    qDebug() << "maxBordersZoom:      " << m_maxBordersZoom;
    qDebug() << "takesOffFilename:    " << m_takesOffFilename;
    qDebug() << "backgroundTiles:     " << m_backgroundTiles;
    qDebug() << "skippedTiles:        " << m_skippedTiles;

    qDebug() << "legendImg1           " << m_legendImg1;
    qDebug() << "legendImg2           " << m_legendImg2;
    qDebug() << "legendImg3           " << m_legendImg3;

    qDebug() << "m_generateTranspaVersion " << m_generateTranspaVersion;
}
