<?php

if (strpos($_SERVER['HTTP_USER_AGENT'], 'Googlebot') === false)
{
	//=============================================================
	// Send email with the message
	//=============================================================

	$fromEmail = "antoine@paraglidable.com";
	$to        = "antoine.meler@gmail.com";

	$subject = 	"Paraglidable: direct message";
	$message = 	"Name: ". $_POST['name'] ."\nE-mail: ". $_POST['email'] ."\n--------------------------------\nText: ". $_POST['text'] ."\n--------------------------------\n". json_encode($_SERVER, JSON_PRETTY_PRINT);
	$headers = 	"From: $fromEmail" . "\r\n" .
				"Reply-To: $fromEmail" . "\r\n" .
				"X-Mailer: PHP/" . phpversion();

	print(mail($to, $subject, $message, $headers));
}

?>