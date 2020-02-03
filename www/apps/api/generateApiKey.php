<?php

include 'bdd.php';

//=============================================================
// Verbose mode
//=============================================================


$verbose = false;

if ($verbose) {
	ini_set('display_errors',1);
	error_reporting(E_ALL);
}


//=============================================================
// Functions
//=============================================================


function generateRandomKey()
{
	$rndHex = substr(md5(rand()), 0, 16);
	$xorHex = 'ddb5097051cd211d';

	return dechex(hexdec($rndHex) ^ hexdec($xorHex));
}

//=============================================================
// Read params
//=============================================================


if ($verbose) {
	print_r($_GET);
}

$lst = array();

$email = filter_var($_GET["email"],  FILTER_VALIDATE_EMAIL);

if (!$email)
	die("ERROR: invalide email");

for ($i=0; true; $i++)
{
	if (array_key_exists("lat_$i",  $_GET) && 
		array_key_exists("lon_$i",  $_GET) && 
		array_key_exists("name_$i", $_GET)   )
	{
		array_push($lst, array( "lat"    => filter_var($_GET["lat_$i"],  FILTER_VALIDATE_FLOAT),
		 						"lon"    => filter_var($_GET["lon_$i"],  FILTER_VALIDATE_FLOAT),
								"name"   => $_GET["name_$i"],
								"spotId" => filter_var($_GET["spotId_$i"],  FILTER_VALIDATE_INT)  ) );
	}
	else
	{
		break;
	}
}

if ($verbose) {
	print_r($lst);
}


//=============================================================
// Insert into bdd
//=============================================================


$escaped_email = mysqli_real_escape_string($conn, $_GET['email']);

// Create account with email if does not exists
$sql = "INSERT INTO Accounts (email) VALUES ('". $escaped_email ."');";
executeQuery($conn, $sql, $verbose);

// Add/replace API key with a new random one
$apiKey          = generateRandomKey();
$sqlAccountQuery = "SELECT id FROM Accounts WHERE email='". $escaped_email ."'";
$latLonName      = mysqli_real_escape_string($conn, serialize($lst));
$sql = "REPLACE INTO ApiKeys (account, apiKey, latLonName) VALUES (($sqlAccountQuery), '$apiKey', '$latLonName');";
executeQuery($conn, $sql, $verbose);

if ($verbose) {
	print("key: $apiKey\n");
}


//=============================================================
// Send email with key
//=============================================================

$exampleUrl = "<a href=\"https://api.paraglidable.com/?key=$apiKey&format=JSON&version=1\">https://api.paraglidable.com/?key=$apiKey&format=JSON&version=1</a><br>".
			  "<a href=\"https://api.paraglidable.com/?key=$apiKey&format=XML&version=1\">https://api.paraglidable.com/?key=$apiKey&format=XML&version=1</a>";

$fromEmail = 'antoine@paraglidable.com';

$to      = 	$email;
$subject = 	"Paraglidable: your API key";

//create a boundary for the email. This 
$boundary = uniqid('np');



//here is the content body
$message = "This is a MIME encoded message.";
$message .= "\r\n\r\n--" . $boundary . "\r\n";
$message .= "Content-type: text/plain;charset=utf-8\r\n\r\n";

//Plain text body
$message .= "Your API key is: $apiKey\n\nExamples:\n\nhttps://api.paraglidable.com/?key=$apiKey&format=JSON&version=1\nhttps://api.paraglidable.com/?key=$apiKey&format=XML&version=1\n\nBest,\nAntoine";

$message .= "\r\n\r\n--" . $boundary . "\r\n";
$message .= "Content-type: text/html;charset=utf-8\r\n\r\n";

//Html body
$message .= "<html>Your API key is: <span style=\"font-weight:bold\">$apiKey</span><br><br>Examples:<br><br>$exampleUrl<br><br>Best,<br>Antoine</html>";

$message .= "\r\n\r\n--" . $boundary . "--";



$headers  = "";
$headers .= "MIME-Version: 1.0\r\n"; 
$headers .= "Content-Type: multipart/alternative;boundary=" . $boundary . "\r\n";
$headers .= "From: $fromEmail" . "\r\n" .
			"Reply-To: $fromEmail" . "\r\n" .
			"X-Mailer: PHP/" . phpversion();

print(mail($to, $subject, $message, $headers, "-f". $fromEmail)); // le "-f" a amélioré mon SPAM score


?>