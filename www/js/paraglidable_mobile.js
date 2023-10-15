
var g_currentDate = "";


var g_appMode = (getQueryVariable("mode")=="app");

if (g_appMode) {
    //$("#header").css("height", "0px");
    $("#desktopIcon").css("visibility", "hidden");
    $("#desktopIcon").css("flex",       "0 0px");
}


var g_arrColorBlindAngles = [0, 110, 280];
var colorBlindValue = 0;

var map = L.map('map', {attributionControl: false, zoomControl: false}).setView(viewCenter, viewZoom);

var g_spotsCreated = false;
var g_currentOpenedSpotId = null;

function setCurrentOpenedSpot(spotId)
{
    if (spotId < 0)
    {
        g_currentOpenedSpotId = null;
        setCookie("spot", "-1", 30*6);
    }
    else
    {
        g_currentOpenedSpotId = spotId;
        setCookie("spot", spotId, 30*6);
    }
}

map.on('popupclose', function(e) {
    setCurrentOpenedSpot(-1);
});

var paraglidableTiles = null;
var Stamen_Terrain    = L.tileLayer('https://tile.osm.ch/switzerland/{z}/{x}/{y}.png', {
    attribution: '',
    subdomains: 'abcd',
    minZoom: 0,
    maxZoom: 16,
    maxNativeZoom: 14,
    ext: 'png',
    detectRetina: true,
    className: 'basetiles',
    errorTileUrl: '/imgs/tileNotFound.png'
}).addTo(map);

var oms = new OverlappingMarkerSpiderfier(map);

function tilesUrl(date)
{
    return 'data/tiles/'+ date +'/256/{z}/{x}/{y}_transpa.{ext}';
}

function createMyTilesLayers(date, className, isRetina)
{
    var layer = L.tileLayer(tilesUrl(date), {
        attribution: '',
        minNativeZoom: isRetina ? 4 : 5,
        maxNativeZoom: isRetina ? 8 : 9,
        ext: 'png',
        detectRetina: true,
        className: className,
        bounds: g_latLngBoundingBox,
        errorTileUrl: '/imgs/tileNotFound.png' });

    return layer;
}

function saveView(lat, lon, zoom)
{
    setCookie("view", lat +","+ lon +","+ zoom, 30*6);
}

function setPositionMobile(lat, lon, forcedZoom=-1)
{
    var zoom = Math.max(map.getZoom(), 7);

    if (forcedZoom >= 0) {
        zoom = forcedZoom;
    }

    map.setView([lat, lon], zoom);
    moveMarker(lat, lon, map);
    setValues(lat, lon);
    saveView(lat, lon, zoom);

    if (g_setPositionFunction != null)
        g_setPositionFunction(lat, lon);
}

map.on('click', function(e) {
        $('#dropdown').removeClass('active');
        $('#dropdown2').removeClass('active');

        $('.takeoffIcon.selected').removeClass('selected');
        setPositionMobile(e.latlng.lat, e.latlng.lng);
    });

function valToColor(val, vals, colors)
{
    if (val < vals[0])
        val = vals[0];
    if (val > vals[vals.length - 1])
        val = vals[vals.length - 1];

    for (v=0; v<vals.length-1; v++)
    {
        if (val <= vals[v+1])
        {
            colorR0 = parseInt(colors[v].substring(0,2), 16); colorR1 = parseInt(colors[v+1].substring(0,2), 16);
            colorG0 = parseInt(colors[v].substring(2,4), 16); colorG1 = parseInt(colors[v+1].substring(2,4), 16);
            colorB0 = parseInt(colors[v].substring(4,6), 16); colorB1 = parseInt(colors[v+1].substring(4,6), 16);

            interp = (val - vals[v])/(vals[v+1] - vals[v]);
            colorRint = 160.0/255.0*(interp*(colorR1-colorR0) + colorR0) + (255.0-160.0)*255.0/255.0;
            colorGint = 160.0/255.0*(interp*(colorG1-colorG0) + colorG0) + (255.0-160.0)*255.0/255.0;
            colorBint = 160.0/255.0*(interp*(colorB1-colorB0) + colorB0) + (255.0-160.0)*255.0/255.0;

            hexR = Math.floor(0.5+colorRint).toString(16);
            if (hexR.length == 1)
                hexR = "0"+hexR;
            hexG = Math.floor(0.5+colorGint).toString(16);
            if (hexG.length == 1)
                hexG = "0"+hexG;
            hexB = Math.floor(0.5+colorBint).toString(16);
            if (hexB.length == 1)
                hexB = "0"+hexB;
            return hexR+hexG+hexB;
        }
    }

    return "000000";
}





//========================================================================================
// spots
//========================================================================================

function valToColorLst(val, vals, colors)
{
    if (val < vals[0])
        val = vals[0];
    if (val > vals[vals.length-1])
        val = vals[vals.length-1];

    for (v=0; v<vals.length-1; v++)
    {
        if (val <= vals[v+1])
        {
            var colorR = [parseInt(colors[v].substring(0,2), 16), parseInt(colors[v+1].substring(0,2), 16)];
            var colorG = [parseInt(colors[v].substring(2,4), 16), parseInt(colors[v+1].substring(2,4), 16)];
            var colorB = [parseInt(colors[v].substring(4,6), 16), parseInt(colors[v+1].substring(4,6), 16)];

            var interp = (val - vals[v])/(vals[v+1] - vals[v]);
            var colorRint = interp*(colorR[1]-colorR[0]) + colorR[0];
            var colorGint = interp*(colorG[1]-colorG[0]) + colorG[0];
            var colorBint = interp*(colorB[1]-colorB[0]) + colorB[0];

            return [ Math.floor(0.5+colorRint),
                     Math.floor(0.5+colorGint),
                     Math.floor(0.5+colorBint) ];
        }
    }

    return [0,0,0];
}


//========================================================================================
//
//========================================================================================


function spotFlyabilityContent(flyability)
{
    return Math.round(flyability*100).toString() +"%";
}

function createMarkers(feature, spotToOpen=-1)
{
    var strId = feature.properties.id.toString();
    var icon = new L.divIcon({className: 'colorMap takeoffIcon takeoffIcon_'+strId});
    var marker = L.marker([feature.geometry.coordinates[1], feature.geometry.coordinates[0]], {icon: icon})

    marker.spotId     = feature.properties.id;
    marker.name       = feature.properties.name;
    marker.flyability = feature.properties.flyability;

    marker.addTo(map);
    oms.addMarker(marker); 

    if (spotToOpen>=0 && marker.spotId == spotToOpen) {
        //marker.fire('click'); // won't work if marker is clusterified
        onSpotClicked(marker);
    }
}

function updateTakeoffFlyability(flyability)
{
    if (flyability >= 0)
    {
        $('#takeoffFlyability').removeClass("waiting");
        $('#takeoffFlyability').html(spotFlyabilityContent(flyability));
        $('#takeoffFlyability').css('background-color', flyabilityColor_with_colorblind(flyability));
    }
    else
    {
        $('#takeoffFlyability').css('background-color', '');
        $('#takeoffFlyability').addClass("waiting");
        $('#takeoffFlyability').html("...");
    }
}

function updateMarkers(feature)
{
    var strId = feature.properties.id.toString();
    $(".takeoffIcon_"+strId).css("background", flyabilityColor(feature.properties.flyability));

    if (feature.properties.id == g_currentOpenedSpotId) {
        updateTakeoffFlyability(feature.properties.flyability);
    }
}

function markerSizeZoomFct(z)
{
    var pivot = 7.5;

    if (z <= pivot)
        return z;
    else
        return pivot + (z-pivot)/4.0;
}

function updateMarkersSize(zoom)
{
    var size = 0.1*Math.pow(2, markerSizeZoomFct(zoom));

    $('.takeoffIcon').css('width',  size);
    $('.takeoffIcon').css('height', size);
    $('.takeoffIcon').css('left', -Math.round(size/2));
    $('.takeoffIcon').css('top',  -Math.round(size/2));
}

var g_popup = new L.Popup();

function onSpotClicked(marker)
{
    var lat    = marker.getLatLng().lat;
    var lon    = marker.getLatLng().lng;
    var name   = marker.name;
    var spotId = marker.spotId;

    $('#dropdown').removeClass('active');
    $('#dropdown2').removeClass('active');
    
    g_popup.setContent(popupContent(name, 0.5, -1, -1));
    L.Util.setOptions(g_popup, {closeButton: false, offset: L.point(0, -10)});

    $('.takeoffIcon.selected').removeClass('selected');
    $(".takeoffIcon_"+spotId).addClass("selected");
    moveMarker(lat, lon, map); // move target img
    g_popup.setLatLng(L.latLng(lat, lon));
    map.openPopup(g_popup);
    updateTakeoffFlyability(-1);
    setCurrentOpenedSpot(spotId);
    setValues(lat, lon, spotId);

    if (g_setPositionFunction != null) // for Android
        g_setPositionFunction(lat, lon, spotId);
}

function loadSpots(decodedJson)
{
    if (!g_spotsCreated) {
        g_spotsCreated = true;

        oms.addListener('click', function(marker) {
            onSpotClicked(marker);
        });

        // Get spot to auto-open at loading
        var spotToOpen = getQueryVariable("spot"); // get spot from URL
        if (spotToOpen === false)
        {
            spotToOpen = -1;

            if (g_setPositionFunction == null) { // not coming from Android App
                var strSpot = getCookie("spot"); // else, get spot from cookie
                if (strSpot != "") {
                    spotToOpen = strSpot;
                }
            }
        }
        //-------------
        decodedJson.features.map(feature => createMarkers(feature, spotToOpen));

        map.on('zoomend', function(e) {
            updateMarkersSize(e.target._zoom);
            saveView(e.target._animateToCenter.lat, e.target._animateToCenter.lng, e.target._zoom);
        });
        updateMarkersSize(map.getZoom());


        // apply ColorBlind to spots
        if (typeof(applyColorBlind) !== "undefined") { 
            applyColorBlind("colorMap");
        }
    }

    decodedJson.features.map(feature => updateMarkers(feature));
}


//========================================================================================
//
//========================================================================================









function smoothstep(x, edge0, edge1)
{
    var t = Math.max(0.0, Math.min(1.0, (x - edge0) / (edge1 - edge0) ));
    return t * t * (3.0 - 2.0 * t);
}

function setDayValue(strDate, day, data)
{
    //data = "0.36,0.5";
    var strVals = data.split(",");

    valFlyability   = strVals[0];
    valCrossability = strVals[1];
    valWind         = strVals[2];
    valWater        = strVals[3];
    if (strVals.length >= 7) {
        valTakeoff  = strVals[6];
    } else {
        valTakeoff  = null;
    }

    if (valTakeoff && g_currentOpenedSpotId && strDate==g_currentDate) {
        updateTakeoffFlyability(valTakeoff);
    }

    if (valTakeoff) {
        takeoffSection = "<tr>\
                            <td class=\"cellValTxt\">takeoff:</td>\
                            <td class=\"cellVal\">"+ Math.round(valTakeoff*100) +"%</td>\
                          </tr>";
        flySection     = "";
    } else {
        takeoffSection = "";
        flySection     = "<tr>\
                            <td class=\"cellValTxt\">fly:</td>\
                            <td class=\"cellVal\">"+ Math.round(valFlyability*100) +"%</td>\
                          </tr>";
    }

    htmlVals = "<table>\
                    "+ takeoffSection +"\
                    "+ flySection +"\
                    <tr>\
                        <td class=\"cellValTxt\">XC:</td>\
                        <td class=\"cellVal\">"+ Math.round(valCrossability*100) +"%</td>\
                    </tr>\
                </table>";

    $("#vals"+day).html(htmlVals);
    if (valTakeoff) {
        hexColor = "#"+valToColor(valTakeoff, [0.0,0.5,1.0], ["A00000", "A07000", "00A000"]);
    } else {
        hexColor = "#"+valToColor(valFlyability, [0.0,0.5,1.0], ["A00000", "A07000", "00A000"]);
    }
    $("#color"+  day).css("background-color", hexColor);
    $("#pattern"+day).css("opacity", smoothstep(valCrossability, 0.0, 1.0));

    htmlIcons = '';
    if (valWind < 0.5)
        htmlIcons += "<img width=\"20px\" src=\"imgs/icons/wind.svg\" />";
    if (valWater < 0.5)
        htmlIcons += "<img width=\"20px\" src=\"imgs/icons/rain.svg\" />";
    $("#icons"+ day).html(htmlIcons);

    // <img width=\"20px\" src=\"imgs/icons/rain.svg\" /><img width=\"20px\" src=\"imgs/icons/wind.svg\" />
}

function setValues(lat, lon, spotId=null)
{
    htmlContent = '';
    for (d=0; d<10; d++)
    {
        var momentDate = moment().add(d, 'days');
        var strDate = momentDate.format("YYYY-MM-DD");

        htmlDate = "<table>\
                        <tr>\
                            <td class=\"dateDayOfWeek\">"+ displayDate(momentDate, false) +"</td>\
                        </tr>\
                        <tr>\
                            <td class=\"dateFull\">"+ momentDate.format('DD/MM/YYYY') +"</td>\
                        </tr>\
                    </table>";


        htmlContent += '<div id="day-'+ strDate +'" class="day" onclick="dayClick(\''+ strDate +'\')" >';
        htmlContent +=   '<div class="color colorMap" id="color'+ d +'"><div id="pattern'+ d +'" class="pattern"></div></div>';
        htmlContent +=   '<div style="flex: 4;">'+ htmlDate +'</div>';
        htmlContent +=   '<div id="vals'+ d +'" style="flex: 3;"></div>';
        htmlContent +=   '<div class="icons" id="icons'+ d +'"></div>';
        htmlContent += '</div>';

        if (spotId)
            strSpot = "&spot="+ spotId.toString();
        else
            strSpot = ""

        $.ajax({  url: "apps/api/get.php?lat="+ lat +"&lon="+ lon +"&date="+ strDate + strSpot,
                  success: (function(strDate, day) {
                            return function(data) {
                                setDayValue(strDate, day, data);
                            }
                           })(strDate, d)
                });
    }

    $('#week').html(htmlContent);
    setSelectedDayColor(g_currentDate);

    // apply ColorBlind to newly created htmlContent
    if (typeof(applyColorBlind) !== "undefined") { 
        applyColorBlind("colorMap");
    }
}


function setSelectedDayColor(strDate)
{
    $('#dropdown').removeClass('active');
    $('#dropdown2').removeClass('active');

    // unselect all
    $(".day").attr('class', 'day day-unselected');

    // select one
    $("#day-"+ strDate).attr('class', 'day day-selected');
}

function downloadSpotsPredictions()
{
    updateTakeoffFlyability(-1); // waiting

    $.getJSON("data/tiles/"+ g_currentDate +"/spots.json", function(data){loadSpots(data)});
}

function dayClick(strDate)
{
    g_currentDate = strDate;

    if (paraglidableTiles == null) {
        $(".basetiles").css("-webkit-filter", "grayscale(100%)");
        $(".basetiles").css("filter",         "grayscale(100%)");
        paraglidableTiles = createMyTilesLayers(strDate, 'mytiles colorMap', L.Browser.retina);
        paraglidableTiles.addTo(map);
        addMyLeafletTransparencyBugFix(map, 'mytiles');
    } else {
        paraglidableTiles.setUrl(tilesUrl(strDate));
    }

    setSelectedDayColor(strDate);
    downloadSpotsPredictions();
}





//=============================================
// Ocean


$.ajax({
    type: "GET",
    url: 'imgs/oceans.json',
    dataType: "text",
    success: function(data){displayOceans(data)}
});


function displayOceans(Text)
{
    oceanLayer = L.geoJson(JSON.parse(Text), {
                                    style: function(feature) {
                                    return {"fillOpacity": 1.0, fillColor: '#0071cb', color:'#000', weight:1};
                                }
            }).addTo(map);
}

//=========================================
// Autocomplete
//=========================================

var autocomplete = new kt.OsmNamesAutocomplete('searchInput', 'apps/search.php?q=', '');
autocomplete.registerCallback(function(item) {
    setPositionMobile(item['lat'], item['lon'], -1);
});



//=========================================
// map controls
//=========================================

function gpsLocationFound(e)
{
    setPositionMobile(e.latlng.lat, e.latlng.lng, -1);

    $("#mapControlButtonGpsIcon").removeClass('searching');
    $("#mapControlButtonGpsIcon").attr('src','imgs/icons/gps.svg');
    $("#mapControlButtonGps").removeClass('disabled');
}
function gpsLocationError(e)
{
    $("#mapControlButtonGpsIcon").removeClass('searching');
    $("#mapControlButtonGpsIcon").attr('src','imgs/icons/gps-disabled.svg');
    $("#mapControlButtonGps").addClass('disabled');
}

map.on('locationfound', gpsLocationFound)
   .on('locationerror', gpsLocationError);

function mapZoom(direction)
{
    $('#dropdown').removeClass('active');
    $('#dropdown2').removeClass('active');

    map.setZoom(Math.max(map.getZoom() + direction, 0));
}

function mapGps()
{
    $('#dropdown').removeClass('active');
    $('#dropdown2').removeClass('active');

    $("#mapControlButtonGpsIcon").addClass('searching');

    map.locate({ enableHighAccuracy: true,
                 watch: false,
                 setView: false  }); 
}


// Color-blind mode ===================================

function applyColorBlind(className)
{
    if (g_arrColorBlindAngles[colorBlindValue%g_arrColorBlindAngles.length] == 0)
    {
        $("."+className).css('filter', '');
    }
    else
    {
        $("."+className).css('filter', 'hue-rotate('+ (g_arrColorBlindAngles[colorBlindValue%g_arrColorBlindAngles.length]) +'deg)');
    }
}

function updateColorBlindLinkText()
{
    var arrStrMode = ["off", "1/2", "2/2"];
    $("#colorBlindModeStrValLink").html(arrStrMode[colorBlindValue%arrStrMode.length]);
}

function updateColorBlind()
{
    applyColorBlind("colorMap");
    updateColorBlindLinkText();
}

function switchColorBlind()
{
    colorBlindValue++;
    setCookie("colorBlindValue", colorBlindValue.toString());

    updateColorBlind();
}



// show/hide layers ===================================


var cookieShowHideColorsVal = getCookie("showHideColorsVal");
var cookieShowHideSpotsVal  = getCookie("showHideSpotsVal");
var cookieColorBlindValue   = getCookie("colorBlindValue");
var showHideColorsVal = 0;
var showHideSpotsVal  = 0;

function applyShowHideMapColors(show)
{
    if (show)
    {
        $(".basetiles").css("-webkit-filter", "grayscale(100%)");
        $(".basetiles").css("filter", "grayscale(100%)");

        // my tiles
        $(".mytiles").css("visibility", "visible");
    }
    else
    {
        $(".basetiles").css("-webkit-filter", "grayscale(0%)");
        $(".basetiles").css("filter", "grayscale(0%)");

        // my tiles
        $(".mytiles").css("visibility", "hidden");
    }
}

function applyShowHideSpots(show)
{
    if (show)
    {
        $('html > head').append($('<style>.takeoffIcon {display:block;}</style>'));
    }
    else
    {
        $('html > head').append($('<style>.takeoffIcon {display:none;}</style>'));
    }
}

function updateShowHideColors()
{
    if (showHideColorsVal == 1)
    {
        applyShowHideMapColors(true);
        $("#checkboxShowHideMapColors").css("background-image", "url('imgs/icons/check.svg')");
    }
    else
    {
        applyShowHideMapColors(false);
        $("#checkboxShowHideMapColors").css("background-image", "none");
    }
}

function updateShowHideSpots()
{
    if (showHideSpotsVal == 1)
    {
        applyShowHideSpots(true);
        $("#checkboxShowHideSpots").css("background-image", "url('imgs/icons/check.svg')");
    }
    else
    {
        applyShowHideSpots(false);
        $("#checkboxShowHideSpots").css("background-image", "none");
    }
}

function showHideColors() {
    showHideColorsVal = (++showHideColorsVal)%2;
    setCookie("showHideColorsVal", showHideColorsVal.toString());
    updateShowHideColors();
}

function showHideSpots()
{
    showHideSpotsVal = (++showHideSpotsVal)%2;
    setCookie("showHideSpotsVal", showHideSpotsVal.toString());
    updateShowHideSpots();
}

function switchLayersVisibility(layer)
{
    $('#dropdown').removeClass('active');

    if (layer==0)
    {
        showHideColors();
    }
    else if (layer==1)
    {
        showHideSpots();
    }
}

function applyLayersPreference()
{
    if (cookieShowHideColorsVal != "")
    {
        showHideColorsVal = parseInt(cookieShowHideColorsVal);
        updateShowHideColors();
    }
    else
    {
        $("#checkboxShowHideMapColors").css("background-image", "url('imgs/icons/check.svg')");
    }


    if (cookieShowHideSpotsVal != "")
    {
        showHideSpotsVal = parseInt(cookieShowHideSpotsVal);
        updateShowHideSpots();
    }
    else
    {
        $("#checkboxShowHideSpots").css("background-image", "url('imgs/icons/check.svg')");
    }

    // color blind mode

    if (cookieColorBlindValue != "")
    {
        colorBlindValue = parseInt(cookieColorBlindValue);
        updateColorBlind();
    }
    else
    {
        updateColorBlindLinkText();
    }
}

//=============================================================

    