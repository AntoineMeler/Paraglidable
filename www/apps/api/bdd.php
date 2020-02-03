<?php

//=============================================================
// Functions
//=============================================================

function connect($servername, $username, $password, $db, $verbose)
{
	// Create connection
	$conn = new mysqli($servername, $username, $password, $db);

	// Check connection
	if ($conn->connect_error) {
		if ($verbose) {
	    	die("[MySQL][ERROR]: connection failed: " . $conn->connect_error);
		} else {
	    	die("");
	    }
	}
	if ($verbose) {
		echo "[MySQL][OK   ]: connected successfully\n";
	}

	return $conn;
}

function executeQuery($conn, $sql, $verbose)
{
	$result = $conn->query($sql);

    if (gettype($result) == "boolean")
    {
    	if ($verbose)
    	{
    		if ($result)
    			printf("[MySQL][OK   ]\n");
    		else {
    			printf("[MySQL][ERROR]: ". $conn->error ."\n");
    		}
    	}
    }
    else
    {
    	$res = array();
    	if ($verbose) {
    		printf("[MySQL][OK   ]: %d results\n", $result->num_rows);
    	}

		while ($row = $result->fetch_assoc())
		{
			if ($verbose) {
				print_r($row);
			}
			array_push($res, $row);
		}
		$result->close();

		return $res;
    }
}

//=============================================================
// Connection to bdd
//=============================================================

$servername = "localhost";
$username   = "root";
$password   = "paraglidable";
$db         = "paraglidable";
$verbose    = false;

$conn = connect($servername, $username, $password, $db, $verbose);

?>
