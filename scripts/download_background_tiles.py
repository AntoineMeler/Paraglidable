import os, errno, urllib.request, time, sys, tqdm
import os.path
from PIL import Image

tiles_url            = "https://stamen-tiles-a.a.ssl.fastly.net/terrain/%d/%d/%d.png"
skippedTilesFilename = "../tiler/data/skippedTiles.txt"
dest_dir             = "../tiler/background_tiles"


def powint(v, p):
    res = 1
    for i in range(p):
        res *= v
    return res

fullWaterTiles = []


def needDownloadImage(destFile):
    if not os.path.isfile(destFile):
        return True
    else:
        # check image n'est pas tel partiellement
        try:
            if Image.open(destFile).size != (256, 256):
                return True
            else:
                return False
        except:
            return True


for zoom in [5,6,7,8,9]:
    scaleFactor = powint(2, zoom-5)

    for tx in range(15*scaleFactor,19*scaleFactor):
        for ty in range(7*scaleFactor, 13*scaleFactor):

            url = tiles_url % (zoom,tx,ty)
            destDir  = dest_dir +"/"+ str(zoom) +"/"+ str(tx)
            destFile = destDir +"/"+ str(ty) +".png"

            if needDownloadImage(destFile):
                print(destFile)
                os.makedirs(destDir, exist_ok=True)

                while True:
                    try:
                        localFile = open(destFile, "wb")
                        localFile.write(urllib.request.urlopen(url).read())
                        localFile.close()
                        break
                    except KeyboardInterrupt:
                        raise
                    except:
                        print("Error, trying again... (%s)" % sys.exc_info()[0])
                        time.sleep(3)

            # update fullWaterTiles list
            if os.path.getsize(destFile) == 103:
                fullWaterTiles += [(zoom,tx,ty)]

# dump water tiles list
waterTilesContent = ""
for w in fullWaterTiles:
    waterTilesContent += str(w[0]) +" "+ str(w[1]) +" "+ str(w[2]) +"\n"

with open(skippedTilesFilename, "w") as fout:
    fout.write(waterTilesContent)

