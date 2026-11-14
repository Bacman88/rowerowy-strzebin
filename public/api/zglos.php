<?php
// POST (JSON): nowe zgłoszenie stanu odcinków. Trafia do moderacji (panel /admin/).
require __DIR__ . '/_db.php';
if ($_SERVER['REQUEST_METHOD'] !== 'POST') hub_json(['blad' => 'Tylko POST'], 405);

$in = json_decode(file_get_contents('php://input') ?: '', true);
if (!is_array($in)) hub_json(['blad' => 'Nieprawidłowe dane'], 400);
$txt = fn($k, $max) => mb_substr(trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', (string)($in[$k] ?? ''))), 0, $max);

// pułapka na boty: ukryte pole musi zostać puste (botowi udajemy sukces)
if ($txt('www', 50) !== '') hub_json(['ok' => true]);

$stan = (string)($in['stan'] ?? '');
$nick = $txt('nick', 60); $kontakt = $txt('kontakt', 120); $kom = $txt('komentarz', 1000);
$data = (string)($in['data'] ?? '');
$odc = array_values(array_unique(array_map('strval', (array)($in['odcinki'] ?? []))));

if (!in_array($stan, STANY, true)) hub_json(['blad' => 'Wybierz stan drogi'], 400);
if (mb_strlen($nick) < 2) hub_json(['blad' => 'Podaj imię lub nick (min. 2 znaki)'], 400);
if ($kontakt !== '' && empty($in['zgoda'])) hub_json(['blad' => 'Zaznacz zgodę na kontakt albo zostaw pole kontaktu puste'], 400);
if ($data !== '' && (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $data) || $data > date('Y-m-d') || $data < '2020-01-01'))
    hub_json(['blad' => 'Nieprawidłowa data przejazdu'], 400);
if (!$odc || count($odc) > 300) hub_json(['blad' => 'Zaznacz od 1 do 300 odcinków'], 400);
$znane = array_flip(json_decode((string)@file_get_contents(__DIR__ . '/_odcinki.json'), true) ?: []);
foreach ($odc as $o) if (!isset($znane[$o])) hub_json(['blad' => 'Nieznany odcinek – odśwież stronę'], 400);

try {
    $db = hub_db();
    $ip = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . hub_cfg()['sol']);

    // to samo zgłoszenie wysłane ponownie (np. ktoś kliknął jeszcze raz, bo nie zobaczył potwierdzenia):
    // zamiast duplikatu uzupełniamy poprzednie, wciąż oczekujące – nowy kontakt, komentarz, data, zdjęcie
    $klucz = $odc; sort($klucz);
    $q = $db->prepare("SELECT id, kontakt, komentarz, data_przejazdu FROM zgloszenia WHERE ip = ? AND stan = ? AND moderacja = 'oczekuje' AND utworzono > ? ORDER BY id DESC");
    $q->execute([$ip, $stan, date('Y-m-d H:i:s', time() - 6 * 3600)]);
    $qo = $db->prepare('SELECT odcinek FROM zgloszenia_odcinki WHERE zgloszenie = ?');
    foreach ($q->fetchAll(PDO::FETCH_ASSOC) as $w) {
        $qo->execute([$w['id']]); $byly = array_map('strval', $qo->fetchAll(PDO::FETCH_COLUMN)); sort($byly);
        if ($byly !== $klucz) continue;
        $db->prepare('UPDATE zgloszenia SET nick = ?, kontakt = ?, komentarz = ?, data_przejazdu = ? WHERE id = ?')
           ->execute([$nick, $kontakt !== '' ? $kontakt : $w['kontakt'], $kom !== '' ? $kom : (string)$w['komentarz'], $data !== '' ? $data : $w['data_przejazdu'], $w['id']]);
        hub_foto_zapisz($db, $in, 'zgloszenia', (int)$w['id']);
        hub_json(['ok' => true, 'id' => (int)$w['id'], 'ponownie' => true]);
    }
    $q = $db->prepare('SELECT COUNT(*) FROM zgloszenia WHERE ip = ? AND utworzono > ?');
    $q->execute([$ip, date('Y-m-d H:i:s', time() - 3600)]);
    if ((int)$q->fetchColumn() >= 15) hub_json(['blad' => 'Za dużo zgłoszeń w ciągu godziny – spróbuj później'], 429);

    $db->beginTransaction();
    $db->prepare('INSERT INTO zgloszenia (utworzono, nick, kontakt, komentarz, stan, data_przejazdu, ip) VALUES (?,?,?,?,?,?,?)')
       ->execute([hub_teraz(), $nick, $kontakt, $kom, $stan, $data, $ip]);
    $id = (int)$db->lastInsertId();
    $ins = $db->prepare('INSERT INTO zgloszenia_odcinki (zgloszenie, odcinek) VALUES (?,?)');
    foreach ($odc as $o) $ins->execute([$id, $o]);
    $db->commit();
    $foto = hub_foto_zapisz($db, $in, 'zgloszenia', $id);
} catch (Throwable $e) {
    if (isset($db) && $db->inTransaction()) $db->rollBack();
    error_log('zglos.php: ' . $e->getMessage());
    hub_json(['blad' => 'Nie udało się zapisać – spróbuj później'], 500);
}

hub_powiadom("Nowa ocena drogi #$id", "Od: $nick\nStan: $stan\nOdcinków: " . count($odc) . ($foto ? "\nZe zdjęciem" : '')
    . ($kontakt !== '' ? "\n(podano kontakt – widoczny w panelu)" : '') . ($kom !== '' ? "\n\n$kom" : ''), 'drogi');
hub_json(['ok' => true, 'id' => $id]);
