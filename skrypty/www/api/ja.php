<?php
// GET: czy przeglądarka należy do zalogowanego administratora (ciasteczko z panelu) – mapa pokazuje wtedy tryb „od razu zatwierdzone”.
require __DIR__ . '/_db.php';
hub_json(['admin' => hub_admin()]);
