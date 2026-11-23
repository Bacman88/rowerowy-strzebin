<?php
// GET ?q=drogi:12,miejsce:5,wezly:3,trasa:2 – stan moderacji własnych propozycji (tylko stan, bez treści i kontaktów).
// Strona pyta o propozycje zapamiętane w przeglądarce, żeby po decyzji administratora zniknęły z „Twoje propozycje”.
require __DIR__ . '/_db.php';
try {
    $db = hub_db(); $out = [];
    $T = ['drogi' => 'zgloszenia', 'miejsce' => 'miejsca', 'wezly' => 'wezly', 'trasa' => 'trasy'];
    foreach (array_slice(explode(',', (string)($_GET['q'] ?? '')), 0, 60) as $k) {
        if (!preg_match('/^(drogi|miejsce|wezly|trasa):(\d{1,9})$/', $k, $m)) continue;
        $q = $db->prepare("SELECT moderacja FROM {$T[$m[1]]} WHERE id = ?"); $q->execute([(int)$m[2]]);
        $out[$k] = $q->fetchColumn() ?: 'brak';
    }
    hub_json(['status' => $out ?: new stdClass()]);
} catch (Throwable $e) {
    error_log('status.php: ' . $e->getMessage());
    hub_json(['blad' => 'Baza niedostępna'], 500);
}
