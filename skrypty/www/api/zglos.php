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
} catch (Throwable $e) {
    if (isset($db) && $db->inTransaction()) $db->rollBack();
    error_log('zglos.php: ' . $e->getMessage());
    hub_json(['blad' => 'Nie udało się zapisać – spróbuj później'], 500);
}

$mail = hub_cfg()['powiadom'];
if ($mail) @mail($mail, "=?UTF-8?B?" . base64_encode("Nowe zgłoszenie stanu drogi #$id") . "?=",
    "Od: $nick\nStan: $stan\nOdcinków: " . count($odc) . "\n\n$kom\n\nPanel: https://" . ($_SERVER['HTTP_HOST'] ?? '') . "/admin/",
    "Content-Type: text/plain; charset=utf-8");
hub_json(['ok' => true, 'id' => $id]);
