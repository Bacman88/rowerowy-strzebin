<?php
// Propozycje zmian węzłów i tabliczek. GET: zatwierdzone (bez kontaktów). POST (JSON): nowa propozycja – do moderacji.
require __DIR__ . '/_db.php';
const KATEGORIE = ['blue', 'brown', 'green', 'red', 'gray', 'orange'];
try {
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $r = hub_db()->query("SELECT id, wezel, lat, lon, slupek, zmiany, komentarz, nick, utworzono FROM wezly WHERE moderacja = 'zatwierdzone' ORDER BY id")->fetchAll();
        hub_json(['wezly' => array_map(fn($w) => ['id' => (int)$w['id'], 'wezel' => $w['wezel'] === null ? null : (int)$w['wezel'], 'lat' => (float)$w['lat'],
            'lon' => (float)$w['lon'], 'slupek' => $w['slupek'], 'zmiany' => json_decode($w['zmiany'], true), 'komentarz' => (string)$w['komentarz'],
            'nick' => $w['nick'], 'data' => substr($w['utworzono'], 0, 10)], $r)]);
    }
    $in = hub_wejscie();
    $wezel = isset($in['wezel']) && $in['wezel'] !== null ? (int)$in['wezel'] : null;
    $lat = (float)($in['lat'] ?? 0); $lon = (float)($in['lon'] ?? 0);
    $slupek = in_array($in['slupek'] ?? '', ['istniejacy', 'nowy'], true) ? $in['slupek'] : '';
    $nick = hub_txt($in, 'nick', 60); $kontakt = hub_txt($in, 'kontakt', 120); $kom = hub_txt($in, 'komentarz', 1000);
    if ($lat < 50.45 || $lat > 50.80 || $lon < 18.65 || $lon > 19.15) hub_json(['blad' => 'Wskaż węzeł na mapie'], 400);
    if ($wezel !== null && ($wezel < 1 || $wezel > 999)) hub_json(['blad' => 'Nieznany węzeł'], 400);
    if (mb_strlen($nick) < 2) hub_json(['blad' => 'Podaj imię lub nick (min. 2 znaki)'], 400);
    if ($kontakt !== '' && empty($in['zgoda'])) hub_json(['blad' => 'Zaznacz zgodę na kontakt albo zostaw pole kontaktu puste'], 400);
    // zmiany: usuń (nazwy celów) i dodaj (cele z odległością, strzałką, kategorią, piktogramem, numerami tras)
    $z = (array)($in['zmiany'] ?? []); $usun = []; $dodaj = [];
    foreach (array_slice((array)($z['usun'] ?? []), 0, 12) as $n) { $n = mb_substr(trim((string)$n), 0, 60); if ($n !== '') $usun[] = $n; }
    foreach (array_slice((array)($z['dodaj'] ?? []), 0, 12) as $c) {
        $c = (array)$c; $n = mb_substr(trim((string)($c['n'] ?? '')), 0, 60);
        if ($n === '') continue;
        $rts = array_values(array_filter(array_map('strval', array_slice((array)($c['rts'] ?? []), 0, 4)), fn($r) => preg_match('/^[1-9]$/', $r)));
        $dodaj[] = ['n' => $n, 'km' => mb_substr(trim((string)($c['km'] ?? '')), 0, 10), 'd' => ($c['d'] ?? '') === 'right' ? 'right' : 'left',
                    'cat' => in_array($c['cat'] ?? '', KATEGORIE, true) ? $c['cat'] : 'blue',
                    'ico' => preg_match('/^[a-z]{1,20}$/', (string)($c['ico'] ?? '')) ? $c['ico'] : '', 'rts' => $rts];
    }
    if (!$usun && !$dodaj && $kom === '') hub_json(['blad' => 'Dodaj albo usuń choć jeden kierunek, albo napisz komentarz'], 400);
    $db = hub_db(); $ip = hub_ip_limit($db);
    $db->prepare('INSERT INTO wezly (utworzono, wezel, lat, lon, slupek, zmiany, komentarz, nick, kontakt, ip) VALUES (?,?,?,?,?,?,?,?,?,?)')
       ->execute([hub_teraz(), $wezel, round($lat, 6), round($lon, 6), $slupek, json_encode(['usun' => $usun, 'dodaj' => $dodaj], JSON_UNESCAPED_UNICODE), $kom, $nick, $kontakt, $ip]);
    $id = (int)$db->lastInsertId();
    hub_powiadom("Propozycja zmiany węzła #$id", "Od: $nick\nWęzeł: " . ($wezel ?? 'nowy') . "\nUsuń: " . implode(', ', $usun) . "\nDodaj: " . implode(', ', array_column($dodaj, 'n')) . "\n\n$kom");
    hub_json(['ok' => true, 'id' => $id]);
} catch (Throwable $e) {
    error_log('wezly.php: ' . $e->getMessage());
    hub_json(['blad' => 'Nie udało się – spróbuj później'], 500);
}
