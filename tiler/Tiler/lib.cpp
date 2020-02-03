#include "lib.h"

#include <QFile>
#include <QDebug>

QString readFile(QString filename)
{
    QString content;

    QFile file(filename);
    if (file.open(QIODevice::ReadOnly | QIODevice::Text))
    {
        content = file.readAll();
        file.close();
    }
    else
    {
        qDebug() << "ERROR: could not open file" << filename;
        exit(1);
    }

    return content;
}
