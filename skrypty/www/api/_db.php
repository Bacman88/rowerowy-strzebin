<?php
// Wspólne: konfiguracja, baza, kopia dobowa. Plik nie jest wywoływany bezpośrednio.
// Konfiguracja leży POZA public_html: /var/www/<witryna>/hub_config.php (wdrożenie jej nie nadpisuje).
declare(strict_types=1);
date_default_timezone_set('Europe/Warsaw');

const STANY = ['dobra', 'srednia', 'trudna', 'nieprzejezdna'];

function hub_cfg(): array {
    static $c = null;
    if ($c !== null) return $c;
    $root = dirname(__DIR__, 2);                       // katalog witryny (nad public_html)
    $f = $root . '/hub_config.php';
    $c = is_file($f) ? (array)(require $f) : [];
    $c += [
        'dane' => $root . '/hub_dane',                 // baza SQLite i kopie – poza public_html
        'dsn' => '', 'db_user' => null, 'db_pass' => null,   // puste = SQLite; MySQL: 'mysql:host=localhost;dbname=...;charset=utf8mb4'
        'admin_haslo' => '',                           // hasło do panelu /admin/
        'sol' => 'hub-strzebin',                       // sól do skrótu adresu IP
        'powiadom' => '',                              // e-mail do powiadomień o nowych zgłoszeniach (opcjonalnie)
    ];
    return $c;
}

function hub_db(): PDO {
    static $db = null;
    if ($db) return $db;
    $c = hub_cfg();
    if (!is_dir($c['dane'])) @mkdir($c['dane'], 0700, true);
    $dsn = $c['dsn'] ?: 'sqlite:' . $c['dane'] . '/stan_drog.sqlite';
    $db = new PDO($dsn, $c['db_user'], $c['db_pass'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
    $my = $db->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql';
    $ai = $my ? 'INT AUTO_INCREMENT PRIMARY KEY' : 'INTEGER PRIMARY KEY AUTOINCREMENT';
    $db->exec("CREATE TABLE IF NOT EXISTS zgloszenia (
        id $ai, utworzono VARCHAR(19) NOT NULL, nick VARCHAR(60) NOT NULL, kontakt VARCHAR(120) NOT NULL DEFAULT '',
        komentarz TEXT, stan VARCHAR(16) NOT NULL, data_przejazdu VARCHAR(10) NOT NULL DEFAULT '',
        moderacja VARCHAR(12) NOT NULL DEFAULT 'oczekuje', moderowano VARCHAR(19), ip VARCHAR(64) NOT NULL DEFAULT '')");
    $db->exec("CREATE TABLE IF NOT EXISTS zgloszenia_odcinki (
        zgloszenie INT NOT NULL, odcinek VARCHAR(12) NOT NULL, PRIMARY KEY (zgloszenie, odcinek))");
    if (!$my) $db->exec('PRAGMA busy_timeout=3000');
    return $db;
}

function hub_teraz(): string { return date('Y-m-d H:i:s'); }

function hub_json($data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

// Pełny zrzut obu tabel (z kontaktami – tylko do kopii i dla administratora).
function hub_zrzut(): array {
    $db = hub_db();
    return [
        'utworzono' => hub_teraz(),
        'zgloszenia' => $db->query('SELECT * FROM zgloszenia ORDER BY id')->fetchAll(),
        'zgloszenia_odcinki' => $db->query('SELECT * FROM zgloszenia_odcinki ORDER BY zgloszenie, odcinek')->fetchAll(),
    ];
}

// Raz na dobę (przy pierwszym wejściu po upływie 24 h): kopia JSON poza public_html, ostatnie 60 kopii;
// przy okazji kasowanie kontaktów starszych niż rok i skrótów IP starszych niż 30 dni.
function hub_dobowo(): void {
    $dir = hub_cfg()['dane'] . '/kopie';
    if (!is_dir($dir)) @mkdir($dir, 0700, true);
    $znacznik = $dir . '/.ostatnia';
    if (is_file($znacznik) && time() - filemtime($znacznik) < 86400) return;
    @touch($znacznik);
    try {
        $db = hub_db();
        $db->prepare("UPDATE zgloszenia SET kontakt = '' WHERE kontakt <> '' AND utworzono < ?")
           ->execute([date('Y-m-d H:i:s', strtotime('-1 year'))]);
        $db->prepare("UPDATE zgloszenia SET ip = '' WHERE ip <> '' AND utworzono < ?")
           ->execute([date('Y-m-d H:i:s', strtotime('-30 days'))]);
        file_put_contents($dir . '/stan_drog_' . date('Y-m-d_His') . '.json',
            json_encode(hub_zrzut(), JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
        $pliki = glob($dir . '/stan_drog_*.json') ?: [];
        sort($pliki);
        foreach (array_slice($pliki, 0, max(0, count($pliki) - 60)) as $p) @unlink($p);
    } catch (Throwable $e) { error_log('hub_dobowo: ' . $e->getMessage()); }
}
