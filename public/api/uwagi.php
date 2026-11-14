<?php
// POST (JSON): uwaga, błąd albo sugestia do strony / nawigacji „Jedź”. Trafia do panelu (/admin/?t=uwagi) i mailem do administratora.
// Wywoływane także z aplikacji na Androida (inne pochodzenie – stąd nagłówki CORS).
require __DIR__ . '/_db.php';
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(204); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') hub_json(['blad' => 'Tylko POST'], 405);

$in = json_decode(file_get_contents('php://input') ?: '', true);
if (!is_array($in)) hub_json(['blad' => 'Nieprawidłowe dane'], 400);
$txt = fn($k, $max) => mb_substr(trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', (string)($in[$k] ?? ''))), 0, $max);
if ($txt('www', 50) !== '') hub_json(['ok' => true]);                       // pułapka na boty

$rodzaj = ($in['rodzaj'] ?? '') === 'sugestia' ? 'sugestia' : 'blad';
$gdzie = in_array($in['gdzie'] ?? '', ['nawigacja', 'strona', 'aplikacja'], true) ? $in['gdzie'] : 'strona';
$tresc = $txt('tresc', 3000); $nick = $txt('nick', 60); $kontakt = $txt('kontakt', 120);
if (mb_strlen($tresc) < 5) hub_json(['blad' => 'Opisz krótko, o co chodzi (min. 5 znaków)'], 400);
if ($kontakt !== '' && empty($in['zgoda'])) hub_json(['blad' => 'Zaznacz zgodę na kontakt albo zostaw pole kontaktu puste'], 400);
// dane techniczne: tylko znane pola, przycięte; trasa – tylko gdy użytkownik zaznaczył „dołącz trasę”
$i = is_array($in['info'] ?? null) ? $in['info'] : [];
$info = [];
foreach (['urzadzenie' => 300, 'ekran' => 30, 'adres' => 200, 'wersja' => 40] as $k => $max) if (isset($i[$k])) $info[$k] = mb_substr((string)$i[$k], 0, $max);
if (!empty($i['trasa']) && is_array($i['trasa'])) {
    $t = $i['trasa']; $pkt = fn($p) => is_array($p) && count($p) === 2 ? [round((float)$p[0], 5), round((float)$p[1], 5)] : null;
    $info['trasa'] = ['start' => $pkt($t['start'] ?? null), 'cel' => $pkt($t['cel'] ?? null), 'celN' => mb_substr((string)($t['celN'] ?? ''), 0, 80),
        'tryb' => mb_substr((string)($t['tryb'] ?? ''), 0, 12), 'rower' => mb_substr((string)($t['rower'] ?? ''), 0, 12), 'km' => round((float)($t['km'] ?? 0), 2)];
}

try {
    $db = hub_db();
    $ip = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . hub_cfg()['sol']);
    $q = $db->prepare('SELECT COUNT(*) FROM uwagi WHERE ip = ? AND utworzono > ?');
    $q->execute([$ip, date('Y-m-d H:i:s', time() - 3600)]);
    if ((int)$q->fetchColumn() >= 10) hub_json(['blad' => 'Za dużo zgłoszeń w ciągu godziny – spróbuj później'], 429);
    // to samo wysłane drugi raz (np. podwójne kliknięcie) – bez duplikatu
    $q = $db->prepare("SELECT id FROM uwagi WHERE ip = ? AND tresc = ? AND utworzono > ?");
    $q->execute([$ip, $tresc, date('Y-m-d H:i:s', time() - 6 * 3600)]);
    if ($id = $q->fetchColumn()) hub_json(['ok' => true, 'id' => (int)$id, 'ponownie' => true]);
    $db->prepare('INSERT INTO uwagi (utworzono, rodzaj, gdzie, tresc, nick, kontakt, info, ip) VALUES (?,?,?,?,?,?,?,?)')
       ->execute([hub_teraz(), $rodzaj, $gdzie, $tresc, $nick, $kontakt, json_encode($info, JSON_UNESCAPED_UNICODE), $ip]);
    $id = (int)$db->lastInsertId();
} catch (Throwable $e) {
    error_log('uwagi.php: ' . $e->getMessage());
    hub_json(['blad' => 'Nie udało się zapisać – spróbuj później'], 500);
}
$GDZ = ['nawigacja' => 'nawigacja Jedź', 'strona' => 'strona', 'aplikacja' => 'aplikacja na Androida'];
hub_powiadom(($rodzaj === 'sugestia' ? 'Sugestia' : 'Zgłoszony błąd') . " #$id – " . $GDZ[$gdzie],
    ($nick !== '' ? "Od: $nick\n" : '') . ($info['wersja'] ?? '') . (isset($info['urzadzenie']) ? ' · ' . $info['urzadzenie'] : '') . "\n\n$tresc"
    . (isset($info['trasa']) ? "\n\n(dołączono trasę – w panelu)" : '') . ($kontakt !== '' ? "\n(podano kontakt – widoczny w panelu)" : ''), 'uwagi');
hub_json(['ok' => true, 'id' => $id]);
