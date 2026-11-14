<?php
// GET: aktualny stan odcinków z zatwierdzonych zgłoszeń (bez danych kontaktowych).
require __DIR__ . '/_db.php';
try {
    hub_dobowo();
    $db = hub_db();
    $rows = $db->query("SELECT z.id, z.utworzono, z.nick, z.komentarz, z.stan, z.data_przejazdu, o.odcinek
        FROM zgloszenia z JOIN zgloszenia_odcinki o ON o.zgloszenie = z.id
        WHERE z.moderacja = 'zatwierdzone' ORDER BY z.utworzono, z.id")->fetchAll();
    $stany = []; $wpisy = []; $zgl = [];
    foreach ($rows as $r) {
        $stany[$r['odcinek']] = $r['id'];                 // nowsze zgłoszenie wygrywa
        $wpisy[$r['odcinek']][] = $r['id'];
        $zgl[$r['id']] = [$r['stan'], $r['nick'], substr($r['utworzono'], 0, 10), $r['data_przejazdu'], (string)$r['komentarz']];
    }
    foreach ($wpisy as $k => $v) $wpisy[$k] = array_slice(array_reverse($v), 0, 5);
    $oczekuje = (int)$db->query("SELECT COUNT(*) FROM zgloszenia WHERE moderacja = 'oczekuje'")->fetchColumn();
    hub_json(['stany' => $stany, 'wpisy' => $wpisy, 'zgloszenia' => $zgl, 'oczekuje' => $oczekuje]);
} catch (Throwable $e) {
    error_log('stan.php: ' . $e->getMessage());
    hub_json(['blad' => 'Baza niedostępna'], 500);
}
