<?php
// GET: zatwierdzone miejsca (bez kontaktów). POST (JSON): propozycja nowego miejsca – trafia do moderacji.
require __DIR__ . '/_db.php';
try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $r = hub_db()->query("SELECT typ, nazwa, opis, lat, lon, nick, utworzono FROM miejsca WHERE moderacja = 'zatwierdzone' ORDER BY id")->fetchAll();
        hub_json(['miejsca' => array_map(fn($m) => ['typ' => $m['typ'], 'nazwa' => $m['nazwa'], 'opis' => (string)$m['opis'],
            'lat' => (float)$m['lat'], 'lon' => (float)$m['lon'], 'nick' => $m['nick'], 'data' => substr($m['utworzono'], 0, 10)], $r)]);
    }
    $in = hub_wejscie();
    $typ = (string)($in['typ'] ?? ''); $lat = (float)($in['lat'] ?? 0); $lon = (float)($in['lon'] ?? 0);
    $nazwa = hub_txt($in, 'nazwa', 80); $opis = hub_txt($in, 'opis', 1000); $nick = hub_txt($in, 'nick', 60); $kontakt = hub_txt($in, 'kontakt', 120);
    if (!in_array($typ, TYPY_MIEJSC, true)) hub_json(['blad' => 'Wybierz rodzaj miejsca'], 400);
    if ($lat < 50.45 || $lat > 50.80 || $lon < 18.65 || $lon > 19.15) hub_json(['blad' => 'Wskaż miejsce na mapie (w okolicy Strzebinia)'], 400);
    if (mb_strlen($nick) < 2) hub_json(['blad' => 'Podaj imię lub nick (min. 2 znaki)'], 400);
    if ($kontakt !== '' && empty($in['zgoda'])) hub_json(['blad' => 'Zaznacz zgodę na kontakt albo zostaw pole kontaktu puste'], 400);
    $db = hub_db(); $ip = hub_ip_limit($db);
    $db->prepare('INSERT INTO miejsca (utworzono, typ, nazwa, opis, lat, lon, nick, kontakt, ip) VALUES (?,?,?,?,?,?,?,?,?)')
       ->execute([hub_teraz(), $typ, $nazwa, $opis, round($lat, 6), round($lon, 6), $nick, $kontakt, $ip]);
    $id = (int)$db->lastInsertId();
    $foto = hub_foto_zapisz($db, $in, 'miejsca', $id);
    hub_powiadom("Nowe miejsce do zatwierdzenia #$id", "Od: $nick\nRodzaj: $typ\n$nazwa\n$opis" . ($foto ? "\n(ze zdjęciem)" : ''));
    hub_json(['ok' => true, 'id' => $id]);
} catch (Throwable $e) {
    error_log('miejsca.php: ' . $e->getMessage());
    hub_json(['blad' => 'Nie udało się – spróbuj później'], 500);
}
