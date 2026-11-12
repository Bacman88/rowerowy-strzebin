<?php
// GET: zatwierdzone trasy mieszkańców (bez kontaktów). POST (JSON): propozycja trasy z kreatora – trafia do moderacji.
require __DIR__ . '/_db.php';

// odległość w metrach (wzór haversine)
function hub_m(array $a, array $b): float {
    $r = M_PI / 180; $dl = ($b[0] - $a[0]) * $r; $dn = ($b[1] - $a[1]) * $r;
    $h = sin($dl / 2) ** 2 + cos($a[0] * $r) * cos($b[0] * $r) * sin($dn / 2) ** 2;
    return 2 * 6371000 * asin(min(1, sqrt($h)));
}
// lista punktów [[lat, lon], …] w okolicy Strzebinia, zaokrąglona; null gdy nieprawidłowa
function hub_punkty($v, int $min, int $max): ?array {
    if (!is_array($v) || count($v) < $min || count($v) > $max) return null;
    $out = [];
    foreach ($v as $p) {
        if (!is_array($p) || count($p) < 2 || !is_numeric($p[0]) || !is_numeric($p[1])) return null;
        $lat = round((float)$p[0], 5); $lon = round((float)$p[1], 5);
        if ($lat < 50.40 || $lat > 50.85 || $lon < 18.55 || $lon > 19.25) return null;
        $out[] = [$lat, $lon];
    }
    return $out;
}

try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $r = hub_db()->query("SELECT id, nazwa, opis, punkty, geom, km, nick, utworzono FROM trasy WHERE moderacja = 'zatwierdzone' ORDER BY id")->fetchAll();
        hub_json(['trasy' => array_map(fn($t) => ['id' => (int)$t['id'], 'nazwa' => $t['nazwa'], 'opis' => (string)$t['opis'],
            'punkty' => json_decode($t['punkty'], true), 'geom' => json_decode($t['geom'], true), 'km' => round((float)$t['km'], 1),
            'nick' => $t['nick'], 'data' => substr($t['utworzono'], 0, 10)], $r)]);
    }
    $in = hub_wejscie();
    $nazwa = hub_txt($in, 'nazwa', 80); $opis = hub_txt($in, 'opis', 1000); $nick = hub_txt($in, 'nick', 60); $kontakt = hub_txt($in, 'kontakt', 120);
    $punkty = hub_punkty($in['punkty'] ?? null, 2, 60);
    $geom = hub_punkty($in['geom'] ?? null, 2, 6000);
    if (mb_strlen($nazwa) < 3) hub_json(['blad' => 'Nazwij trasę (min. 3 znaki)'], 400);
    if (!$punkty || !$geom) hub_json(['blad' => 'Wyznacz trasę na mapie (od 2 do 60 punktów, w okolicy Strzebinia)'], 400);
    if (mb_strlen($nick) < 2) hub_json(['blad' => 'Podaj imię lub nick (min. 2 znaki)'], 400);
    if ($kontakt !== '' && empty($in['zgoda'])) hub_json(['blad' => 'Zaznacz zgodę na kontakt albo zostaw pole kontaktu puste'], 400);
    $m = 0; for ($i = 1; $i < count($geom); $i++) $m += hub_m($geom[$i - 1], $geom[$i]);
    if ($m < 200 || $m > 300000) hub_json(['blad' => 'Trasa musi mieć od 0,2 do 300 km'], 400);
    $db = hub_db(); $ip = hub_ip_limit($db);
    $db->prepare('INSERT INTO trasy (utworzono, nazwa, opis, punkty, geom, km, nick, kontakt, ip) VALUES (?,?,?,?,?,?,?,?,?)')
       ->execute([hub_teraz(), $nazwa, $opis, json_encode($punkty), json_encode($geom), round($m / 1000, 2), $nick, $kontakt, $ip]);
    $id = (int)$db->lastInsertId();
    hub_powiadom("Nowa trasa do zatwierdzenia #$id", "Od: $nick\n$nazwa (" . number_format($m / 1000, 1, ',', '') . " km)\n$opis");
    hub_json(['ok' => true, 'id' => $id, 'km' => round($m / 1000, 1)]);
} catch (Throwable $e) {
    error_log('trasy.php: ' . $e->getMessage());
    hub_json(['blad' => 'Nie udało się – spróbuj później'], 500);
}
