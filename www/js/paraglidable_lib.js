
var g_latLngBoundingBox = L.latLngBounds([[66.5-0.01,  -10.55+0.01], [31.952+0.01, 33.75-0.01]]);

var g_userLang = navigator.language || navigator.userLanguage; 
moment.locale(g_userLang);

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

function flyabilityColor(val)
{
    color = valToColorLst(val, [0.0,0.5,1.0], ["A00000", "A07000", "00A000"]);
    return "#"+ ("00" + color[0].toString(16)).substr(-2) +
                ("00" + color[1].toString(16)).substr(-2) +
                ("00" + color[2].toString(16)).substr(-2);
}


function rotateHue(color, rotation)
{
    var color1 = tinycolor(color);
    color_hsv = color1.toHsv();
    color_hsv.h = (color_hsv.h + rotation) % 360;
    color1 = tinycolor({h: color_hsv.h, s: color_hsv.s, v: color_hsv.v});
    return color1.toHexString();
}

function flyabilityColor_with_colorblind(flyability)
{
    var color = flyabilityColor(flyability);
    var rotation = g_arrColorBlindAngles[colorBlindValue%g_arrColorBlindAngles.length];
    if (rotation != 0)
        color = rotateHue(color, rotation);
    return color;
}

function popupContent(name, value, id, nbFlights)
{
    var arNamesTitleLst = name.split(/,,,/g);
    var titleName = name;

    if (arNamesTitleLst.length > 1) {
        titleName = arNamesTitleLst[0];
        name      = arNamesTitleLst[1];
    }

    var arNames = name.split(/,,/g);

    var takeoffsList = "";
    if (arNames.length > 1)
    {
        var lst = "";
        for (l=0; l<arNames.length; l++)
            lst += "<span style=\"font-weight:bold;margin: 0px 5px 0px 5px\">&#x25cf;</span>"+ arNames[l] +"<br>";
        takeoffsList = "<div class=\"takeoffPopupList\">"+
                            "Merged takeoffs:<br>"+ lst +
                       "</div>";
    }

    var valTxt = "<div class=\"popupValbox\" id=\"takeoffFlyability\" style=\"background-color:"+ flyabilityColor_with_colorblind(value) +"\">"+ Math.round(100*value) +"%</div>";

    var windSvg = "";
    if (false) {
      windSvg = "<div class=\"takeoffPopupContent\" style=\"text-align:center\">"+
                    '<img style="width:100%;max-width:70px" src="data/wind_'+ id +'.svg">' +
                  "</div><br>"+ nbFlights;
    }

    return "<div class=\"takeoffPopupContainer\">"+
                "<div class=\"takeoffPopupTitle\">"+
                    titleName +
                "</div>"+
                "<div class=\"takeoffPopupContent\">"+
                    valTxt +
                "</div>"+
                takeoffsList + 
                windSvg +
            "</div>"
}

function getStrDateDiffDays(strDate)
{
    var inputMomentDate = moment(strDate, "YYYY-MM-DD");
    var diffDays = inputMomentDate.diff(moment().startOf('day'), 'days', true);
    
    return Math.round(diffDays);
}

function displayDate(momentDate, showNums=true, long=false, showYear=false, showDow=true)
{
    var strYear = showYear ? '/YYYY' : '';
    var strDow  = showDow  ? 'dddd ' : '';

    if (Math.abs(getStrDateDiffDays(momentDate.format("YYYY-MM-DD"))) > 1) {
        if (showNums)
          return moment(momentDate).format(strDow +'DD/MM'+ strYear);
        else
          return moment(momentDate).format('dddd');
    } else {
        if (!long)
          return momentDate.calendar().split(' ')[0] + momentDate.format(' (ddd)');
        else
          return momentDate.calendar().split(' ')[0] + momentDate.format(', '+ strDow +'DD/MM'+ strYear);
    }
}

function setCookie(cname, cvalue, exdays=200) {
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    document.cookie = cname + "=" + cvalue + ";" + expires + ";path=/";
}

function getCookie(cname) {
    var name = cname + "=";
    var decodedCookie = decodeURIComponent(document.cookie);
    var ca = decodedCookie.split(';');
    for(var i = 0; i <ca.length; i++) {
        var c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}

function getQueryVariable(variable)
{
   var query = window.location.search.substring(1);
   var vars = query.split("&");
   for (var i=0;i<vars.length;i++) {
           var pair = vars[i].split("=");
           if(pair[0] == variable){return pair[1];}
   }
   return(false);
}

//==================================================================
// Leaflet
//==================================================================

var g_marker = null;

function moveMarker(lat, lon, theMap)
{
    if (g_marker == null) {
        var targetIcon = L.icon({
            iconUrl: 'imgs/icons/target.svg',
            iconSize:     [31, 31],
            iconAnchor:   [15, 15]
        });

        g_marker = L.marker([lat, lon], {icon: targetIcon, zIndexOffset: -2000}).addTo(theMap);
        $(g_marker._icon).addClass('myMarker');
    } else {
        g_marker.setLatLng(new L.LatLng(lat, lon)); 
    }
}


var g_timerMyLeafletTransparencyBugFix = {};

// used in mobile version only
function addMyLeafletTransparencyBugFix(map, className)
{
    map.on('zoomend', 
        (function(theClassName) {
                    return function(e) {

                        if ((theClassName in g_timerMyLeafletTransparencyBugFix)) {
                            window.clearTimeout(g_timerMyLeafletTransparencyBugFix[theClassName]);
                        }

                        g_timerMyLeafletTransparencyBugFix[theClassName] = setTimeout(function(){ 

                            var divs = $("div."+ theClassName +":first").find("div");
                            if (divs.length == 2) {
                                divs.first().html("");
                            }

                         }, 1500); // 1500ms after zoomend, if there is a resilient div, remove it
                    }
                })(className)
    );
}

