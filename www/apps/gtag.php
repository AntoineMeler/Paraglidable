<?php
error_reporting(0);
if (substr($_SERVER['HTTP_HOST'], 0, 9) != "localhost")
{
	$url = "https://www.googletagmanager.com/gtag/js?id=UA-127025208-1";
	print(file_get_contents($url));
}
?>
