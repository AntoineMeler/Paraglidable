<?php

include("math.php");

header("Access-Control-Allow-Origin: *");

$verbose = false;


function getPrediction($date, $coords)
{
	//===========================================================================
	// Open tile data file
	//===========================================================================


	$filename = "../../data/tiles/". $date ."/256/". $coords['zoom'] ."/". $coords['tx'] ."/". $coords['ty'] .".data";

	$handle = @fopen($filename, "rb");

	if (!$handle) {
		return false;
	}


	//===========================================================================
	// Read tile data file
	//===========================================================================


	$contents = fread($handle, filesize($filename));
	fclose($handle);


	//===========================================================================
	// decode values
	//===========================================================================


	$nbVals = strlen($contents)/(256*256);
	$pos    = $nbVals*($coords['x']*256 + $coords['y']);
	$vals 	= array();
	for ($v=0; $v<$nbVals; $v++) {
		array_push($vals, round(ord(substr($contents, $pos + $v, 1))/255.0, 4));
	}

	return $vals;
}


function getSpotPrediction($date, $spotId)
{
	$filename = "../../data/tiles/". $date ."/spots.json";

	$handle = @fopen($filename, "r");
	if (!$handle) {
		return false;
	}

	//===========================================================================
	// Read tile data file
	//===========================================================================

	$contents = fread($handle, filesize($filename));
	fclose($handle);

	//===========================================================================
	// decode
	//===========================================================================

	$arJson = json_decode($contents);

	$arSpots = $arJson->features;

	$nbSpots = count($arSpots);
	for ($s=0; $s<$nbSpots; $s++)
	{
		if ($arSpots[$s]->properties->id == $spotId)
		{
			return array("flyability"=>$arSpots[$s]->properties->flyability);
		}
	}

	return false;
}


function getElevation($coords)
{

	//===========================================================================
	// Open tile data file
	//===========================================================================


	$filename = "../../data/elevation/". $coords['zoom'] ."/". $coords['tx'] ."/". $coords['ty'] .".elev";

	$handle = @fopen($filename, "rb");

	if (!$handle) {
		return false;
	}


	//===========================================================================
	// Read tile data file
	//===========================================================================


	$contents = fread($handle, filesize($filename));
	fclose($handle);


	//===========================================================================
	// Return elevation value at (x,y)
	//===========================================================================


	$strVal = substr($contents, 2*($coords['x']*256 + $coords['y']), 2);
	return (ord(substr($strVal, 0, 1)) << 8) + ord(substr($strVal, 1, 1));
}

//===========================================================================
// API output formats
//===========================================================================

function generateXML($data)
{
	$res = "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n";


	$res .= "<paraglidable>\n";
	foreach ($data as $date => $dataDay)
	{

		$res .= "\t<day date=\"$date\">\n";


		for ($i=0; $i<count($dataDay); $i++)
		{
			$dataSpot = $dataDay[$i];

			$res .= "\t\t<location name=\"". $dataSpot['name'] ."\" lat=\"". $dataSpot['lat'] ."\" lon=\"". $dataSpot['lon'] ."\">\n";
			$res .= "\t\t\t<forecast>\n";
			$res .= "\t\t\t\t<fly>". $dataSpot['forecast']['fly'] ."</fly>\n";
			$res .= "\t\t\t\t<XC>".  $dataSpot['forecast']['XC'] ."</XC>\n";
			if (array_key_exists('takeoff', $dataSpot['forecast']))
				$res .= "\t\t\t\t<takeoff>".  $dataSpot['forecast']['takeoff'] ."</takeoff>\n";
			$res .= "\t\t\t</forecast>\n";
			$res .= "\t\t</location>\n";
		}


		$res .= "\t</day>\n";

	}

	$res .= "</paraglidable>\n";
	return $res;
}

//===========================================================================
// check inputs
//===========================================================================

// log API calls for check
/*
if (rand()%20==0)
{
	$strlog = var_export($_SERVER, true);
	file_put_contents("/tmp/apiCalls.txt", "$strlog\n", FILE_APPEND);
}
*/

if ($_GET['key'] && !ctype_xdigit($_GET['key']))
	die("unknown key");

$_GET['tx']   = filter_var($_GET['tx'],   FILTER_VALIDATE_INT);
$_GET['ty']   = filter_var($_GET['ty'],   FILTER_VALIDATE_INT);
$_GET['x']    = filter_var($_GET['x'],    FILTER_VALIDATE_INT);
$_GET['y']    = filter_var($_GET['y'],    FILTER_VALIDATE_INT);
$_GET['zoom'] = filter_var($_GET['zoom'], FILTER_VALIDATE_INT);
$_GET['elev'] = filter_var($_GET['elev'], FILTER_VALIDATE_INT);
$_GET['lat']  = filter_var($_GET['lat'],  FILTER_VALIDATE_FLOAT);
$_GET['lon']  = filter_var($_GET['lon'],  FILTER_VALIDATE_FLOAT);
$_GET['spot'] = filter_var($_GET['spot'], FILTER_VALIDATE_INT);
$checkDate    = preg_match('/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/', $_GET['date']);

// 3 cas d'usage: key, tile pixel coord or lat/lon
if (  	!array_key_exists('key', $_GET)
	 &&
		 ($_GET['tx']   === false ||
		  $_GET['ty']   === false ||
		  $_GET['x']    === false ||
		  $_GET['y']    === false ||
		  $_GET['zoom'] === false ||
		  !$checkDate )
	 &&
	 	($_GET['lat'] === false ||
	 	 $_GET['lon'] === false ||
	 	 !$checkDate) )
{
	exit("");
}


//===========================================================================
// 
//===========================================================================


if (array_key_exists('key', $_GET))
{
	//===========================================================================
	// API
	//===========================================================================

	include 'bdd.php';

	$sql = "SELECT latLonName FROM ApiKeys WHERE apiKey='". $_GET['key'] ."'";
	$res = executeQuery($conn, $sql, $verbose);

	if (count($res) != 1)
		die("unknown key");

	$data = array();

	$nbDays = 10;
	for ($d=0; $d<$nbDays; $d++)
	{
		$datetime = new DateTime();
		$datetime->modify("+$d day");
		$date = $datetime->format('Y-m-d');

		$dataDays = array();

		foreach (unserialize($res[0]['latLonName']) as $spot)
		{
			$coords = LatLonToTileCoords($spot['lat'], $spot['lon']);

			$vals = getPrediction($date, $coords);
			$vals2 = array('fly'=>$vals[0], 'XC'=>$vals[1]);

			// Add takeoff flyability if it is a takeoff
			if (array_key_exists('spotId', $spot) && $spot['spotId']>=0) {
				$spotPrediction = getSpotPrediction($date, $spot['spotId']);
				if ($spotPrediction !== false) {
					$vals2['takeoff'] = $spotPrediction['flyability'];
				}
			}

			$spot['forecast'] = $vals2;

			if ($vals !== false) {
				$spotWithoutSpotIt = $spot; // remove the 'spotId' key from the exported result
				unset($spotWithoutSpotIt['spotId']);
				array_push($dataDays, $spotWithoutSpotIt);
			}
		}

		$data[$date] = $dataDays;

	}

	if (!$_GET['format'] || strtolower($_GET['format'])=="json")
	{
		if ($_GET['htmlentities'])
		{
			echo htmlentities(json_encode($data, JSON_PRETTY_PRINT));
		}
		else
		{
			header('Content-Type: application/json; charset=utf-8');
			echo json_encode($data, JSON_PRETTY_PRINT);
		}
	}
	else
	{
		if ($_GET['htmlentities'])
		{
			echo htmlentities(generateXML($data));
		}
		else
		{
			header('Content-Type: text/xml; charset=utf-8');
			echo generateXML($data);
		}
	}
}
else
{
	//===========================================================================
	// Web-site
	//===========================================================================

	if ($_GET['lat'] || $_GET['lon'])
	{
		$coords = LatLonToTileCoords($_GET['lat'], $_GET['lon']);
	}
	else
	{
		$coords = array('tx' 	=> $_GET['tx'],
						'ty' 	=> $_GET['ty'],
						'x'  	=> $_GET['x'],
						'y'  	=> $_GET['y'],
						'zoom' 	=> $_GET['zoom'] );
	}

	$date = $_GET['date'];

	$vals = getPrediction($date, $coords);

	$elev = false;
	if ($_GET['elev'] == 1) {
		$elev = getElevation($coords);
	}

	if ($_GET['spot'] !== false && $_GET['spot'] >= 0) {
		$spotPrediction = getSpotPrediction($date, $_GET['spot']);
		if ($spotPrediction !== false) {
			// Add takeoff flyability
			array_push($vals, $spotPrediction['flyability']);
		}
	}

	if ($vals !== false) {
		// print predictions
		print(implode(",", $vals));

		// print elevation
		if ($elev !== false) {
			print(";$elev");
		}
	} else {
		die("");
	}
}

?>
