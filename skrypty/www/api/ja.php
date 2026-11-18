<?php
// GET: czy przeglądarka należy do zalogowanego administratora (ciasteczko z panelu) – mapa pokazuje wtedy tryb „od razu zatwierdzone”.
// POST z niepowtarzalnym adresem (18.11.2026): odpowiedź nigdy z pamięci podręcznej serwera ani pośredników
require __DIR__ . '/_db.php';
header('Vary: Cookie');
hub_json(['admin' => hub_admin()]);
