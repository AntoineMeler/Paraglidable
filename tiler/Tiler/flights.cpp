#include "flights.h"

#include <QDebug>
#include <QFile>
#include <QTextStream>

FlightPoint::FlightPoint(float lat, float lon, float alt)
{
    this->lat = lat;
    this->lon = lon;
    this->alt = alt;
}

float decodeIgcLatLonValue(QString strVal)
{
    strVal.remove(0,1); // remove 'S' or 'E'
    return strVal.toFloat();
}

std::vector<FlightPoint> Flight::readIgc(QString &content)
{
    std::vector<FlightPoint> track;

    QStringList lines = content.split("\n");
    for (int l=0; l<lines.size(); l++)
    {
        if (lines[l].size() < 10)
            continue;

        if (lines[l].at(0) == 'T')
        {
            // parse line
            QStringList arLine = lines[l].split(" ");
            //qDebug() << arLine;

            float lat = arLine[2].remove(0,1).toFloat();
            float lon = arLine[3].remove(0,1).toFloat();
            float alt = arLine[6].toFloat();

            track.push_back(FlightPoint(lat, lon, alt));
            //qDebug() << lat << lon << alt;
        }
    }

    return track;
}

Flight::Flight(QString filename)
{
    QFile fin(filename);
    if (fin.open(QFile::ReadOnly | QFile::Text))
    {
        QTextStream in(&fin);
        QString content = in.readAll();


        m_track = readIgc(content);


        fin.close();
    }
    else
    {
        qDebug() << "ERROR loading " << filename;
    }
}

Flights::Flights(QStringList filenames)
{
    for (int f=0; f<filenames.size(); f++)
    {
        qDebug() << filenames[f];
        m_flights.push_back(Flight(filenames[f]));
    }
}
