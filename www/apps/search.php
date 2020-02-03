<?php
// to get SSL encryption
error_reporting(0);

$allowed = false;
$allowed_referers = array("antoine.lol", "paraglidable.com");
foreach ($allowed_referers as $referer)
{
	if (strpos($_SERVER['HTTP_REFERER'], 'https://'.$referer) === 0)
	{
		$allowed = true;
	}
}
if ($allowed === true)
{
	$q = str_replace(array("q/", ".js", "/", "\\", ",", ";", "'", "\"", "."), "", $_GET['q']);
	print(file_get_contents("http://localhost:8001/q/$q.js"));
}
?>