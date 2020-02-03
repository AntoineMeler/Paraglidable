<?php

/*
ini_set('display_errors', 1);
error_reporting(E_ALL);
print_r($_SERVER);
*/


//#########################################################################################
//#########################################################################################
// Banned IPs db
//#########################################################################################
//#########################################################################################


$bannedIPsFile = "banned.txt.php";

function isBannedIP($ip, $bannedIPsFile)
{
	$ips = loadBannedIPs($bannedIPsFile);
	return in_array($ip, $ips);
}

function loadBannedIPs($bannedIPsFile)
{
	if (!file_exists($bannedIPsFile))
	{
		return array();
	}
	else
	{
		$content = file_get_contents($bannedIPsFile);
		return explode("\n", $content);
	}
}

function saveBannedIPs($ips, $bannedIPsFile)
{
	$content = implode("\n", $ips);
	file_put_contents($bannedIPsFile, $content);
}

function bandIP($IP, $bannedIPsFile)
{
	$ips = loadBannedIPs($bannedIPsFile);

	if (!in_array($IP, $ips))
	{
		array_push($ips, $IP);
		saveBannedIPs($ips, $bannedIPsFile);
	}
}


//#########################################################################################
//#########################################################################################
// Result
//#########################################################################################
//#########################################################################################


function fakeResult($date)
{
	srand(hexdec(substr(md5($date),0,8)));

	// TODO redirect random ?
	//header('Location: ../../data/data_2013-01-01');

	// meteo
	$meteoData = file_get_contents("../../data/data_2013-01-01");
	// flights
	$flightsData = file_get_contents("../../data/flights_2010-07-07");

	print("$meteoData\n$flightsData");
}

function result($date)
{
	header('Location: ../../data/data_2013-01-01'); 
}


//#########################################################################################
//#########################################################################################
// MAIN
//#########################################################################################
//#########################################################################################


$date = "";
if (array_key_exists('date', $_GET))
	$date = $_GET['date'];

//=========================================================
// Banned IP
//=========================================================

if (isBannedIP($_SERVER['REMOTE_ADDR'], $bannedIPsFile))
{
	print(fakeResult($date));
}

//=========================================================
// Not banned IP
//=========================================================

else
{
	if (
		  (strpos($_SERVER['HTTP_HOST'],    "paraglidable.com") === false && strpos($_SERVER['HTTP_HOST'],    "fufu-map.com") === false) ||
		  (strpos($_SERVER['HTTP_REFERER'], "paraglidable.com") === false && strpos($_SERVER['HTTP_REFERER'], "fufu-map.com") === false) ||
		   strpos($_SERVER['HTTP_COOKIE'],  "view=") === false ||
		   $date == ""
	   )
	{
		// Activité suspecte repérée, on retient l'IP, elle est grillée à vie mdr !
		bandIP($_SERVER['REMOTE_ADDR'], $bannedIPsFile);

		print(fakeResult($date));
	}
	else
	{
		print(result($date));
	}
}

?>