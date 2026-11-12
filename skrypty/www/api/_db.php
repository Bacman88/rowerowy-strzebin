<?php
// Wspólne: konfiguracja, baza, kopia dobowa. Plik nie jest wywoływany bezpośrednio.
// Konfiguracja leży POZA public_html: /var/www/<witryna>/hub_config.php (wdrożenie jej nie nadpisuje).
declare(strict_types=1);
date_default_timezone_set('Europe/Warsaw');

const STANY = ['dobra', 'srednia', 'trudna', 'nieprzejezdna'];
const TYPY_MIEJSC = ['lawka', 'wiata', 'piknik', 'widok', 'zabawa', 'woda', 'serwis', 'stojak', 'wypozycz', 'wc', 'parking', 'apteczka', 'info',
    'jedzenie', 'kawa', 'bar', 'nocleg', 'ciekawe', 'zabytek', 'kosciol', 'przyroda', 'sport'];

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
    $db->exec("CREATE TABLE IF NOT EXISTS miejsca (
        id $ai, utworzono VARCHAR(19) NOT NULL, typ VARCHAR(12) NOT NULL, nazwa VARCHAR(80) NOT NULL DEFAULT '', opis TEXT,
        lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL, nick VARCHAR(60) NOT NULL, kontakt VARCHAR(120) NOT NULL DEFAULT '',
        moderacja VARCHAR(12) NOT NULL DEFAULT 'oczekuje', moderowano VARCHAR(19), ip VARCHAR(64) NOT NULL DEFAULT '')");
    $db->exec("CREATE TABLE IF NOT EXISTS wezly (
        id $ai, utworzono VARCHAR(19) NOT NULL, wezel INT, lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL,
        slupek VARCHAR(12) NOT NULL DEFAULT '', zmiany TEXT NOT NULL, komentarz TEXT, nick VARCHAR(60) NOT NULL, kontakt VARCHAR(120) NOT NULL DEFAULT '',
        moderacja VARCHAR(12) NOT NULL DEFAULT 'oczekuje', moderowano VARCHAR(19), ip VARCHAR(64) NOT NULL DEFAULT '')");
    // trasy zaproponowane w kreatorze: punkty (kliknięte) + przebieg po drogach (uproszczony), długość liczona na serwerze
    $db->exec("CREATE TABLE IF NOT EXISTS trasy (
        id $ai, utworzono VARCHAR(19) NOT NULL, nazwa VARCHAR(80) NOT NULL, opis TEXT, punkty TEXT NOT NULL, geom TEXT NOT NULL,
        km DOUBLE PRECISION NOT NULL DEFAULT 0, nick VARCHAR(60) NOT NULL, kontakt VARCHAR(120) NOT NULL DEFAULT '',
        moderacja VARCHAR(12) NOT NULL DEFAULT 'oczekuje', moderowano VARCHAR(19), ip VARCHAR(64) NOT NULL DEFAULT '')");
    // korekty miejsc z panelu (12.11.2026): przesunięcie, zmiana rodzaju/nazwy/opisu albo ukrycie dowolnego miejsca na mapie
    $db->exec("CREATE TABLE IF NOT EXISTS korekty_miejsc (
        klucz VARCHAR(80) NOT NULL PRIMARY KEY, ukryj INT NOT NULL DEFAULT 0, typ VARCHAR(12), nazwa VARCHAR(80), opis TEXT,
        lat DOUBLE PRECISION, lon DOUBLE PRECISION, zmieniono VARCHAR(19) NOT NULL)");
    // zdjęcie do zgłoszenia (12.11.2026): nazwa pliku w <dane>/zdjecia, kasowane po decyzji administratora
    foreach (['zgloszenia', 'miejsca'] as $t) {
        $kol = $my ? array_column($db->query("SHOW COLUMNS FROM $t")->fetchAll(), 'Field')
                   : array_column($db->query("PRAGMA table_info($t)")->fetchAll(), 'name');
        if (!in_array('foto', $kol, true)) $db->exec("ALTER TABLE $t ADD COLUMN foto VARCHAR(60) NOT NULL DEFAULT ''");
    }
    if (!$my) $db->exec('PRAGMA busy_timeout=3000');
    return $db;
}

function hub_teraz(): string { return date('Y-m-d H:i:s'); }

function hub_json($data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, private, max-age=0');
    header('X-LiteSpeed-Cache-Control: no-cache');
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
        'miejsca' => $db->query('SELECT * FROM miejsca ORDER BY id')->fetchAll(),
        'wezly' => $db->query('SELECT * FROM wezly ORDER BY id')->fetchAll(),
        'trasy' => $db->query('SELECT * FROM trasy ORDER BY id')->fetchAll(),
        'korekty_miejsc' => $db->query('SELECT * FROM korekty_miejsc ORDER BY klucz')->fetchAll(),
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
        foreach (['zgloszenia', 'miejsca', 'wezly', 'trasy'] as $t) {
            $db->prepare("UPDATE $t SET kontakt = '' WHERE kontakt <> '' AND utworzono < ?")->execute([date('Y-m-d H:i:s', strtotime('-1 year'))]);
            $db->prepare("UPDATE $t SET ip = '' WHERE ip <> '' AND utworzono < ?")->execute([date('Y-m-d H:i:s', strtotime('-30 days'))]);
        }
        file_put_contents($dir . '/stan_drog_' . date('Y-m-d_His') . '.json',
            json_encode(hub_zrzut(), JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT), LOCK_EX);
        $pliki = glob($dir . '/stan_drog_*.json') ?: [];
        sort($pliki);
        foreach (array_slice($pliki, 0, max(0, count($pliki) - 60)) as $p) @unlink($p);
        // zdjęcia zgłoszeń już rozpatrzonych (np. gdy decyzję zapisano inaczej niż przez panel) – sprzątanie
        foreach (glob(hub_cfg()['dane'] . '/zdjecia/*.jpg') ?: [] as $p) {
            if (!preg_match('/^(zgloszenia|miejsca)_(\d+)\.jpg$/', basename($p), $m)) continue;
            $q = $db->prepare("SELECT moderacja FROM {$m[1]} WHERE id = ?"); $q->execute([(int)$m[2]]);
            $st = $q->fetchColumn();
            if ($st !== 'oczekuje') { @unlink($p); $db->prepare("UPDATE {$m[1]} SET foto = '' WHERE id = ?")->execute([(int)$m[2]]); }
        }
    } catch (Throwable $e) { error_log('hub_dobowo: ' . $e->getMessage()); }
}

// Wspólne dla zgłoszeń: odczyt JSON, czyszczenie tekstu, limit zgłoszeń z jednego adresu.
function hub_wejscie(): array {
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') hub_json(['blad' => 'Tylko POST'], 405);
    $in = json_decode(file_get_contents('php://input') ?: '', true);
    if (!is_array($in)) hub_json(['blad' => 'Nieprawidłowe dane'], 400);
    if (trim((string)($in['www'] ?? '')) !== '') hub_json(['ok' => true]);   // pułapka na boty
    return $in;
}
function hub_txt(array $in, string $k, int $max): string {
    return mb_substr(trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', (string)($in[$k] ?? ''))), 0, $max);
}
function hub_ip_limit(PDO $db): string {
    $ip = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . hub_cfg()['sol']);
    $od = date('Y-m-d H:i:s', time() - 3600); $n = 0;
    foreach (['zgloszenia', 'miejsca', 'wezly', 'trasy'] as $t) { $q = $db->prepare("SELECT COUNT(*) FROM $t WHERE ip = ? AND utworzono > ?"); $q->execute([$ip, $od]); $n += (int)$q->fetchColumn(); }
    if ($n >= 20) hub_json(['blad' => 'Za dużo zgłoszeń w ciągu godziny – spróbuj później'], 429);
    return $ip;
}
// E-mail do administratora przy każdym nowym zgłoszeniu (hub_config.php: 'powiadom' => 'adres', opcjonalnie 'nadawca').
// Kontaktów zgłaszających nie wysyłamy mailem – są tylko w panelu. Zwraca true, gdy serwer przyjął wiadomość.
function hub_powiadom(string $temat, string $tresc, string $zakladka = ''): bool {
    $c = hub_cfg(); $do = trim((string)$c['powiadom']);
    if ($do === '') return false;
    $host = preg_replace('/^www\./', '', preg_replace('/[^a-z0-9.\-]/i', '', (string)($_SERVER['HTTP_HOST'] ?? 'rowerowy-strzebin.smart-ant.pl')));
    $od = trim((string)($c['nadawca'] ?? '')) ?: "info@$host";
    $link = "https://$host/admin/" . ($zakladka ? "?t=$zakladka" : '');
    $nag = implode("\r\n", ["From: =?UTF-8?B?" . base64_encode('HUB rowerowy Strzebiń') . "?= <$od>", "Reply-To: $od", 'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=utf-8', 'Content-Transfer-Encoding: 8bit', 'X-Mailer: HUB rowerowy Strzebin']);
    return @mail($do, '=?UTF-8?B?' . base64_encode('[HUB rowerowy] ' . $temat) . '?=',
        $tresc . "\n\nSprawdź i zatwierdź w panelu: $link\n", $nag, '-f' . $od);
}

// Zdjęcie (JPEG, już zmniejszone w przeglądarce) przesłane jako data URL w polu 'foto'. Zapis poza public_html.
// Zwraca nazwę pliku albo '' (brak zdjęcia). Błędne zdjęcie nie blokuje zgłoszenia – po prostu go nie zapisujemy.
function hub_foto_zapisz(PDO $db, array $in, string $tab, int $id): string {
    $d = (string)($in['foto'] ?? '');
    if ($d === '' || !preg_match('#^data:image/jpeg;base64,([A-Za-z0-9+/=]+)$#', $d, $m)) return '';
    $bin = base64_decode($m[1], true);
    if ($bin === false || strlen($bin) < 2000 || strlen($bin) > 900000 || substr($bin, 0, 3) !== "\xFF\xD8\xFF") return '';
    if (function_exists('getimagesizefromstring')) { $g = @getimagesizefromstring($bin); if (!$g || $g[2] !== IMAGETYPE_JPEG || $g[0] > 2600 || $g[1] > 2600) return ''; }
    $dir = hub_cfg()['dane'] . '/zdjecia';
    if (!is_dir($dir)) @mkdir($dir, 0700, true);
    $plik = $tab . '_' . $id . '.jpg';
    if (@file_put_contents($dir . '/' . $plik, $bin, LOCK_EX) === false) return '';
    @chmod($dir . '/' . $plik, 0600);
    $db->prepare("UPDATE $tab SET foto = ? WHERE id = ?")->execute([$plik, $id]);
    return $plik;
}
// korekty miejsc w postaci dla mapy: {klucz: {u:1} | {t, n, o, lat, lon}}
function hub_korekty(PDO $db): array {
    $out = [];
    foreach ($db->query('SELECT * FROM korekty_miejsc') as $k)
        $out[$k['klucz']] = $k['ukryj'] ? ['u' => 1] : array_filter(['t' => $k['typ'], 'n' => $k['nazwa'], 'o' => $k['opis'],
            'lat' => $k['lat'] === null ? null : (float)$k['lat'], 'lon' => $k['lon'] === null ? null : (float)$k['lon']], fn($v) => $v !== null);
    return $out;
}
function hub_foto_usun(PDO $db, string $tab, int $id): void {
    if (!in_array($tab, ['zgloszenia', 'miejsca'], true)) return;
    @unlink(hub_cfg()['dane'] . '/zdjecia/' . $tab . '_' . $id . '.jpg');
    $db->prepare("UPDATE $tab SET foto = '' WHERE id = ?")->execute([$id]);
}
