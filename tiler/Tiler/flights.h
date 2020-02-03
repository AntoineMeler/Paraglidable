#ifndef FLIGHTS_H
#define FLIGHTS_H

#include <QString>
#include <QStringList>

#include <vector>

class FlightPoint
{
public:
    float lat, lon, alt;

    FlightPoint(float lat, float lon, float alt);
    FlightPoint() {}
};

class Flight
{

    // readers
    static std::vector<FlightPoint> readIgc(QString &content);

public:
    std::vector<FlightPoint> m_track;

    Flight(QString filename);
    int size() {return (int)m_track.size(); }
};

class Flights
{

public:
    std::vector<Flight> m_flights;

    Flights() {}
    Flights(QStringList filenames);
    int size() {return (int)m_flights.size(); }
};

#endif // FLIGHTS_H
