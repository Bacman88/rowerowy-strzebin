<?php
// Busy gminy Koszęcin – mapa wspólna (strona busy-koszecin.smart-ant.pl/wspolna/, inny origin – CORS ustawia _db.php).
// GET: zatwierdzone propozycje (bez kontaktów) z liczbą głosów.
// POST {akcja:'dodaj', ...}: nowa propozycja – trafia do moderacji (panel /admin/?t=busy) i mailem do administratora.
// POST {akcja:'glos', id, urz}: „też tego potrzebuję” – jeden głos na urządzenie, tylko dla zatwierdzonych.
require __DIR__ . '/_db.php';

const BUSY_RODZAJE = ['dojazd', 'przystanek', 'linia', 'godzina', 'uwaga'];
const BUSY_DNI = ['robocze', 'sobota', 'niedziela', 'codziennie', ''];
const BUSY_CZESTOSC = ['codziennie', 'kilka', 'czasem', ''];
const BUSY_CEL = ['szkola', 'praca', 'lekarz', 'urzad', 'zakupy', 'kolej', 'inne', ''];
const BUSY_LINIE = ['1', '2', '3', '4', '5', '1L', '4S', '4P', 'nowa', ''];

try {
    $db = hub_db();
    if ($_SERVER['REQUEST_METHOD'] === 'GET') {
        $gl = [];
        foreach ($db->query('SELECT zgloszenie, COUNT(*) n FROM busy_glosy GROUP BY zgloszenie') as $g) $gl[(int)$g['zgloszenie']] = (int)$g['n'];
        $r = $db->query("SELECT id, utworzono, rodzaj, skad, dokad, godzina, kierunek, dni, czestosc, cel, linia, tresc, lat, lon, nick
            FROM busy_zgloszenia WHERE moderacja = 'zatwierdzone' ORDER BY id DESC")->fetchAll();
        hub_json(['propozycje' => array_map(fn($p) => [
            'id' => (int)$p['id'], 'data' => substr($p['utworzono'], 0, 10), 'rodzaj' => $p['rodzaj'], 'skad' => $p['skad'], 'dokad' => $p['dokad'],
            'godzina' => $p['godzina'], 'kierunek' => $p['kierunek'], 'dni' => $p['dni'], 'czestosc' => $p['czestosc'], 'cel' => $p['cel'],
            'linia' => $p['linia'], 'tresc' => (string)$p['tresc'], 'nick' => $p['nick'],
            'lat' => $p['lat'] === null ? null : (float)$p['lat'], 'lon' => $p['lon'] === null ? null : (float)$p['lon'],
            'glosy' => $gl[(int)$p['id']] ?? 0], $r)]);
    }

    $in = hub_wejscie();
    $ip = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . hub_cfg()['sol']);

    if (($in['akcja'] ?? '') === 'glos') {
        $id = (int)($in['id'] ?? 0); $urz = hub_urz();
        if ($urz === '') hub_json(['blad' => 'Brak identyfikatora urządzenia'], 400);
        $q = $db->prepare("SELECT COUNT(*) FROM busy_zgloszenia WHERE id = ? AND moderacja = 'zatwierdzone'"); $q->execute([$id]);
        if (!(int)$q->fetchColumn()) hub_json(['blad' => 'Nie ma takiej propozycji'], 404);
        $q = $db->prepare('SELECT COUNT(*) FROM busy_glosy WHERE zgloszenie = ? AND urz = ?'); $q->execute([$id, $urz]);
        if (!(int)$q->fetchColumn()) $db->prepare('INSERT INTO busy_glosy (zgloszenie, urz, utworzono) VALUES (?,?,?)')->execute([$id, $urz, hub_teraz()]);
        $q = $db->prepare('SELECT COUNT(*) FROM busy_glosy WHERE zgloszenie = ?'); $q->execute([$id]);
        hub_json(['ok' => true, 'glosy' => (int)$q->fetchColumn()]);
    }

    $rodzaj = (string)($in['rodzaj'] ?? '');
    if (!in_array($rodzaj, BUSY_RODZAJE, true)) hub_json(['blad' => 'Wybierz rodzaj propozycji'], 400);
    $wyb = fn(string $k, array $dozw) => in_array((string)($in[$k] ?? ''), $dozw, true) ? (string)$in[$k] : '';
    $skad = hub_txt($in, 'skad', 80); $dokad = hub_txt($in, 'dokad', 80); $tresc = hub_txt($in, 'tresc', 2000);
    $nick = hub_txt($in, 'nick', 60); $kontakt = hub_txt($in, 'kontakt', 120);
    $godz = preg_match('/^([01]?\d|2[0-3]):[0-5]\d$/', (string)($in['godzina'] ?? '')) ? sprintf('%05s', (string)$in['godzina']) : '';
    $kier = in_array($in['kierunek'] ?? '', ['przyjazd', 'odjazd'], true) ? (string)$in['kierunek'] : '';
    $dni = $wyb('dni', BUSY_DNI); $czest = $wyb('czestosc', BUSY_CZESTOSC); $cel = $wyb('cel', BUSY_CEL); $linia = $wyb('linia', BUSY_LINIE);
    $lat = isset($in['lat']) && $in['lat'] !== null ? (float)$in['lat'] : null; $lon = isset($in['lon']) && $in['lon'] !== null ? (float)$in['lon'] : null;
    if ($lat !== null && ($lat < 50.40 || $lat > 50.85 || $lon < 18.55 || $lon > 19.25)) { $lat = null; $lon = null; }

    if (mb_strlen($nick) < 2) hub_json(['blad' => 'Podaj imię lub nick (min. 2 znaki)'], 400);
    if ($kontakt !== '' && empty($in['zgoda'])) hub_json(['blad' => 'Zaznacz zgodę na kontakt albo zostaw pole kontaktu puste'], 400);
    if ($rodzaj === 'dojazd' && ($skad === '' || $dokad === '')) hub_json(['blad' => 'Podaj, skąd i dokąd chcesz dojechać'], 400);
    if ($rodzaj === 'przystanek' && $lat === null) hub_json(['blad' => 'Wskaż miejsce przystanku na mapie'], 400);
    if (in_array($rodzaj, ['linia', 'godzina', 'uwaga'], true) && mb_strlen($tresc) < 5) hub_json(['blad' => 'Opisz krótko swoją propozycję (min. 5 znaków)'], 400);

    if (!hub_admin()) {
        hub_ban_sprawdz($db, $ip);
        $q = $db->prepare('SELECT COUNT(*) FROM busy_zgloszenia WHERE ip = ? AND utworzono > ?'); $q->execute([$ip, date('Y-m-d H:i:s', time() - 3600)]);
        if ((int)$q->fetchColumn() >= 15) hub_json(['blad' => 'Za dużo zgłoszeń w ciągu godziny – spróbuj później'], 429);
    }
    $db->prepare('INSERT INTO busy_zgloszenia (utworzono, rodzaj, skad, dokad, godzina, kierunek, dni, czestosc, cel, linia, tresc, lat, lon, nick, kontakt, ip, urz)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)')
       ->execute([hub_teraz(), $rodzaj, $skad, $dokad, $godz, $kier, $dni, $czest, $cel, $linia, $tresc,
           $lat === null ? null : round($lat, 6), $lon === null ? null : round($lon, 6), $nick, $kontakt, hub_admin() ? '' : $ip, hub_urz()]);
    $id = (int)$db->lastInsertId();
    if (hub_admin_zatwierdz($db, 'busy_zgloszenia', $id)) hub_json(['ok' => true, 'id' => $id, 'zatwierdzone' => true]);
    $opis = ['dojazd' => "Potrzebny dojazd: $skad → $dokad" . ($godz ? " ($kier $godz)" : ''), 'przystanek' => 'Propozycja przystanku',
        'linia' => 'Uwaga do linii ' . $linia, 'godzina' => 'Godziny kursu, linia ' . $linia, 'uwaga' => 'Uwaga ogólna'][$rodzaj];
    hub_powiadom("Busy Koszęcin: nowa propozycja #$id", "Od: $nick\n$opis\n$tresc" . ($kontakt !== '' ? "\n(podano kontakt – widoczny w panelu)" : ''), 'busy');
    hub_json(['ok' => true, 'id' => $id]);
} catch (Throwable $e) {
    error_log('busy.php: ' . $e->getMessage());
    hub_json(['blad' => 'Nie udało się – spróbuj później'], 500);
}
