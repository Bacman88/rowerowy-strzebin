<?php
// Wspólne: konfiguracja, baza, kopia dobowa. Plik nie jest wywoływany bezpośrednio.
// Konfiguracja leży POZA public_html: /var/www/<witryna>/hub_config.php (wdrożenie jej nie nadpisuje).
declare(strict_types=1);
// 16.11.2026: API czyta i zapisuje też aplikacja „Jedź” na Androidzie (inny origin: https://localhost) – CORS dla wszystkich plików api/
// (dane publiczne bez kontaktów, zapisy przez moderację; bez ciasteczek – Allow-Credentials nie ustawiamy)
if (basename(dirname($_SERVER['SCRIPT_FILENAME'] ?? '')) === 'api') {
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type');
    if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') { http_response_code(204); exit; }
}
date_default_timezone_set('Europe/Warsaw');
ob_start();   // przypadkowe ostrzeżenia PHP nie mogą zepsuć odpowiedzi JSON (hub_json czyści bufor)

const STANY = ['dobra', 'srednia', 'trudna', 'nieprzejezdna'];
const TYPY_MIEJSC = ['lawka', 'wiata', 'piknik', 'widok', 'zabawa', 'woda', 'serwis', 'stojak', 'wypozycz', 'wc', 'parking', 'aed', 'apteczka', 'apteka', 'pkp', 'autobus', 'info',
    'jedzenie', 'kawa', 'bar', 'sklep', 'nocleg', 'ciekawe', 'zabytek', 'kosciol', 'przyroda', 'sport'];

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
    // uwagi, błędy i sugestie do strony i nawigacji „Jedź” (14.11.2026): rodzaj (blad/sugestia), gdzie (nawigacja/strona/aplikacja),
    // info – dane techniczne (urządzenie, przeglądarka, wersja) i – tylko gdy użytkownik zaznaczył – trasa (start, cel, tryb, rower)
    $db->exec("CREATE TABLE IF NOT EXISTS uwagi (
        id $ai, utworzono VARCHAR(19) NOT NULL, rodzaj VARCHAR(10) NOT NULL, gdzie VARCHAR(12) NOT NULL, tresc TEXT NOT NULL,
        nick VARCHAR(60) NOT NULL DEFAULT '', kontakt VARCHAR(120) NOT NULL DEFAULT '', info TEXT,
        moderacja VARCHAR(12) NOT NULL DEFAULT 'oczekuje', moderowano VARCHAR(19), ip VARCHAR(64) NOT NULL DEFAULT '')");
    // korekty miejsc z panelu (12.11.2026): przesunięcie, zmiana rodzaju/nazwy/opisu albo ukrycie dowolnego miejsca na mapie
    $db->exec("CREATE TABLE IF NOT EXISTS korekty_miejsc (
        klucz VARCHAR(80) NOT NULL PRIMARY KEY, ukryj INT NOT NULL DEFAULT 0, typ VARCHAR(12), nazwa VARCHAR(80), opis TEXT,
        lat DOUBLE PRECISION, lon DOUBLE PRECISION, zmieniono VARCHAR(19) NOT NULL)");
    // przesunięcia węzłów (słupków) z panelu (15.11.2026): nowe położenie słupka; strona i nawigacja nakładają je od razu
    $db->exec("CREATE TABLE IF NOT EXISTS korekty_wezlow (nr INT NOT NULL PRIMARY KEY, lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL, zmieniono VARCHAR(19) NOT NULL)");
    // zdjęcie do zgłoszenia (12.11.2026): nazwa pliku w <dane>/zdjecia, kasowane po decyzji administratora
    foreach (['zgloszenia', 'miejsca'] as $t) {
        $kol = $my ? array_column($db->query("SHOW COLUMNS FROM $t")->fetchAll(), 'Field')
                   : array_column($db->query("PRAGMA table_info($t)")->fetchAll(), 'name');
        if (!in_array('foto', $kol, true)) $db->exec("ALTER TABLE $t ADD COLUMN foto VARCHAR(60) NOT NULL DEFAULT ''");
    }
    // godziny otwarcia miejsc (15.11.2026): dla miejsc dodanych na mapie i jako poprawka administratora do dowolnego miejsca
    foreach (['miejsca' => "VARCHAR(200) NOT NULL DEFAULT ''", 'korekty_miejsc' => 'VARCHAR(200)'] as $t => $typ) {
        $kol = $my ? array_column($db->query("SHOW COLUMNS FROM $t")->fetchAll(), 'Field')
                   : array_column($db->query("PRAGMA table_info($t)")->fetchAll(), 'name');
        if (!in_array('godziny', $kol, true)) $db->exec("ALTER TABLE $t ADD COLUMN godziny $typ");
    }
    // anonimowy identyfikator urządzenia (17.11.2026): losowy, generowany raz w przeglądarce/aplikacji – pozwala w panelu
    // zobaczyć, że kilka zgłoszeń przyszło z tego samego telefonu; nie zawiera żadnych danych o osobie
    foreach (['zgloszenia', 'miejsca', 'wezly', 'trasy', 'uwagi'] as $t) {
        $kol = $my ? array_column($db->query("SHOW COLUMNS FROM $t")->fetchAll(), 'Field')
                   : array_column($db->query("PRAGMA table_info($t)")->fetchAll(), 'name');
        if (!in_array('urz', $kol, true)) $db->exec("ALTER TABLE $t ADD COLUMN urz VARCHAR(12) NOT NULL DEFAULT ''");
    }
    // krótkie blokady (17.11.2026): skrót IP albo identyfikator urządzenia do podanej daty; zablokowany widzi „dziękujemy”,
    // ale jego zgłoszenia nie są zapisywane (nie wie, że jest zablokowany, więc nie próbuje obejść blokady)
    $db->exec("CREATE TABLE IF NOT EXISTS bany (id $ai, rodzaj VARCHAR(4) NOT NULL, wartosc VARCHAR(64) NOT NULL,
        do_kiedy VARCHAR(19) NOT NULL, utworzono VARCHAR(19) NOT NULL, opis VARCHAR(120) NOT NULL DEFAULT '')");
    $kol = $my ? array_column($db->query("SHOW COLUMNS FROM bany")->fetchAll(), 'Field') : array_column($db->query("PRAGMA table_info(bany)")->fetchAll(), 'name');
    if (!in_array('jawny', $kol, true)) $db->exec("ALTER TABLE bany ADD COLUMN jawny INT NOT NULL DEFAULT 0");   // 1 = nadawca widzi komunikat o blokadzie
    // Busy gminy Koszęcin (20.11.2026, busy-koszecin.smart-ant.pl/wspolna/): propozycje mieszkańców – potrzebny dojazd, przystanek,
    // uwaga do linii, godziny kursu. Moderacja jak reszta mapy wspólnej. Głosy „też tego potrzebuję” – jeden na urządzenie.
    $db->exec("CREATE TABLE IF NOT EXISTS busy_zgloszenia (
        id $ai, utworzono VARCHAR(19) NOT NULL, rodzaj VARCHAR(12) NOT NULL, skad VARCHAR(80) NOT NULL DEFAULT '', dokad VARCHAR(80) NOT NULL DEFAULT '',
        godzina VARCHAR(5) NOT NULL DEFAULT '', kierunek VARCHAR(10) NOT NULL DEFAULT '', dni VARCHAR(12) NOT NULL DEFAULT '', czestosc VARCHAR(12) NOT NULL DEFAULT '',
        cel VARCHAR(12) NOT NULL DEFAULT '', linia VARCHAR(4) NOT NULL DEFAULT '', tresc TEXT, lat DOUBLE PRECISION, lon DOUBLE PRECISION,
        nick VARCHAR(60) NOT NULL, kontakt VARCHAR(120) NOT NULL DEFAULT '',
        moderacja VARCHAR(12) NOT NULL DEFAULT 'oczekuje', moderowano VARCHAR(19), ip VARCHAR(64) NOT NULL DEFAULT '', urz VARCHAR(12) NOT NULL DEFAULT '')");
    $db->exec("CREATE TABLE IF NOT EXISTS busy_glosy (zgloszenie INT NOT NULL, urz VARCHAR(12) NOT NULL, utworzono VARCHAR(19) NOT NULL, PRIMARY KEY (zgloszenie, urz))");
    if (!$my) $db->exec('PRAGMA busy_timeout=3000');
    return $db;
}

function hub_teraz(): string { return date('Y-m-d H:i:s'); }

function hub_json($data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate, private, max-age=0');
    header('X-LiteSpeed-Cache-Control: no-cache');
    while (ob_get_level()) ob_end_clean();
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    // odpowiedź idzie do przeglądarki od razu; powiadomienia e-mail wysyłamy dopiero potem (wolny serwer poczty nie może wyglądać jak błąd)
    if (function_exists('fastcgi_finish_request')) fastcgi_finish_request();
    elseif (function_exists('litespeed_finish_request')) litespeed_finish_request();
    else flush();
    foreach ($GLOBALS['hub_po_odp'] ?? [] as $f) { try { $f(); } catch (Throwable $e) { error_log('hub po odpowiedzi: ' . $e->getMessage()); } }
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
        'uwagi' => $db->query('SELECT * FROM uwagi ORDER BY id')->fetchAll(),
        'busy_zgloszenia' => $db->query('SELECT * FROM busy_zgloszenia ORDER BY id')->fetchAll(),
        'busy_glosy' => $db->query('SELECT * FROM busy_glosy ORDER BY zgloszenie')->fetchAll(),
        'korekty_wezlow' => $db->query('SELECT * FROM korekty_wezlow ORDER BY nr')->fetchAll(),
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
        foreach (['zgloszenia', 'miejsca', 'wezly', 'trasy', 'uwagi', 'busy_zgloszenia'] as $t) {
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
// identyfikator urządzenia z pola 'urz' (12 znaków hex) albo ''
function hub_urz(): string {
    static $u = null; if ($u !== null) return $u;
    $in = json_decode(file_get_contents('php://input') ?: '', true);
    $u = is_array($in) && preg_match('/^[0-9a-f]{12}$/', (string)($in['urz'] ?? '')) ? (string)$in['urz'] : '';
    return $u;
}
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
// Administrator zalogowany w panelu dostaje drugie ciasteczko „hub_adm” (ścieżka „/”, 8 h), dzięki któremu formularze mapy wspólnej
// zapisują jego dodatki od razu jako zatwierdzone, bez limitu zgłoszeń i bez maila. Na serwerze trzymamy tylko skrót tokenu.
function hub_adm_plik(string $t): string { return hub_cfg()['dane'] . '/sesje/adm_' . hash('sha256', $t); }
function hub_admin(): bool {
    static $ok = null; if ($ok !== null) return $ok;
    $t = (string)($_COOKIE['hub_adm'] ?? '');
    if (!preg_match('/^[a-f0-9]{48}$/', $t)) return $ok = false;
    $f = hub_adm_plik($t); return $ok = is_file($f) && filemtime($f) > time() - 8 * 3600;
}
function hub_adm_ciastko(string $t, int $do): void {
    setcookie('hub_adm', $t, ['expires' => $do, 'path' => '/', 'httponly' => true, 'samesite' => 'Strict', 'secure' => !empty($_SERVER['HTTPS'])]);
}
function hub_admin_odnow(): void {   // wołane z panelu przy każdym wejściu zalogowanego administratora
    $dir = hub_cfg()['dane'] . '/sesje'; if (!is_dir($dir)) @mkdir($dir, 0700, true);
    $t = (string)($_COOKIE['hub_adm'] ?? '');
    if (preg_match('/^[a-f0-9]{48}$/', $t) && is_file(hub_adm_plik($t))) { @touch(hub_adm_plik($t)); }
    else { $t = bin2hex(random_bytes(24)); @file_put_contents(hub_adm_plik($t), '1', LOCK_EX); }
    hub_adm_ciastko($t, time() + 8 * 3600);
    foreach (glob($dir . '/adm_*') ?: [] as $f) if (filemtime($f) < time() - 8 * 3600) @unlink($f);
}
function hub_admin_wyloguj(): void {
    $t = (string)($_COOKIE['hub_adm'] ?? ''); if (preg_match('/^[a-f0-9]{48}$/', $t)) @unlink(hub_adm_plik($t));
    hub_adm_ciastko('', time() - 3600);
}
// po zapisie zgłoszenia z mapy: od administratora – od razu zatwierdzone (zdjęcie niepotrzebne). Zwraca true, gdy zatwierdzono.
function hub_admin_zatwierdz(PDO $db, string $tab, int $id): bool {
    if (!hub_admin()) return false;
    $db->prepare("UPDATE $tab SET moderacja = 'zatwierdzone', moderowano = ? WHERE id = ?")->execute([hub_teraz(), $id]);
    hub_foto_usun($db, $tab, $id); return true;
}
// komunikat dla zablokowanego (blokada jawna) – na stronie, w aplikacji i w mailu
function hub_ban_tekst(string $do): string {
    return 'Twoje zgłoszenia są wstrzymane do ' . date('d.m.Y, H:i', strtotime($do)) . ' – dostaliśmy z tego urządzenia zbyt wiele zgłoszeń '
        . 'niezgodnych ze stanem dróg. Jeśli to pomyłka, napisz: info@rowerowy-strzebin.smart-ant.pl';
}
// zablokowany (skrót IP lub urządzenie): blokada cicha – udajemy sukces i niczego nie zapisujemy;
// blokada jawna – nadawca dostaje komunikat, do kiedy i dlaczego
function hub_ban_sprawdz(PDO $db, string $ip): void {
    if (hub_admin()) return;
    $q = $db->prepare("SELECT do_kiedy, jawny FROM bany WHERE do_kiedy > ? AND ((rodzaj = 'ip' AND wartosc = ?) OR (rodzaj = 'urz' AND wartosc <> '' AND wartosc = ?)) ORDER BY jawny DESC, do_kiedy DESC");
    $q->execute([hub_teraz(), $ip, hub_urz()]);
    $b = $q->fetch(); if (!$b) return;
    if ((int)$b['jawny']) hub_json(['blad' => hub_ban_tekst($b['do_kiedy']), 'ban' => $b['do_kiedy']], 403);
    hub_json(['ok' => true]);
}
function hub_ip_limit(PDO $db): string {
    if (hub_admin()) return '';   // administrator – bez limitu
    $ip = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? '') . hub_cfg()['sol']);
    hub_ban_sprawdz($db, $ip);
    $od = date('Y-m-d H:i:s', time() - 3600); $n = 0;
    foreach (['zgloszenia', 'miejsca', 'wezly', 'trasy'] as $t) { $q = $db->prepare("SELECT COUNT(*) FROM $t WHERE ip = ? AND utworzono > ?"); $q->execute([$ip, $od]); $n += (int)$q->fetchColumn(); }
    if ($n >= 20) hub_json(['blad' => 'Za dużo zgłoszeń w ciągu godziny – spróbuj później'], 429);
    return $ip;
}
// E-mail do administratora przy każdym nowym zgłoszeniu (hub_config.php: 'powiadom' => 'adres', opcjonalnie 'nadawca').
// Kontaktów zgłaszających nie wysyłamy mailem – są tylko w panelu. Zwraca true, gdy serwer przyjął wiadomość.
// Domyślnie wysyła dopiero po odesłaniu odpowiedzi JSON (zob. hub_json); $teraz = true – od razu (test z panelu).
function hub_powiadom(string $temat, string $tresc, string $zakladka = '', bool $teraz = false): bool {
    if (!$teraz) { $GLOBALS['hub_po_odp'][] = fn() => hub_powiadom($temat, $tresc, $zakladka, true); return true; }
    $c = hub_cfg(); $do = trim((string)$c['powiadom']);
    if ($do === '') return false;
    $host = preg_replace('/^www\./', '', preg_replace('/[^a-z0-9.\-]/i', '', (string)($_SERVER['HTTP_HOST'] ?? 'rowerowy-strzebin.smart-ant.pl')));
    $od = trim((string)($c['nadawca'] ?? '')) ?: "info@$host";
    $link = "https://$host/admin/" . ($zakladka ? "?t=$zakladka" : '');
    return hub_mail($do, '[HUB rowerowy] ' . $temat, $tresc . "\n\nSprawdź i zatwierdź w panelu: $link\n");
}
// wysyłka maila (SMTP z hub_config.php albo mail()); nadawca: 'nadawca' albo info@domena
function hub_mail(string $do, string $temat, string $tresc): bool {
    $c = hub_cfg();
    $host = preg_replace('/^www\./', '', preg_replace('/[^a-z0-9.\-]/i', '', (string)($_SERVER['HTTP_HOST'] ?? 'rowerowy-strzebin.smart-ant.pl')));
    $od = trim((string)($c['nadawca'] ?? '')) ?: "info@$host";
    $nag = implode("\r\n", ["From: =?UTF-8?B?" . base64_encode('HUB rowerowy Strzebiń') . "?= <$od>", "Reply-To: $od", 'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=utf-8', 'Content-Transfer-Encoding: 8bit', 'X-Mailer: HUB rowerowy Strzebin']);
    $tem = '=?UTF-8?B?' . base64_encode($temat) . '?=';
    $tr = $tresc;
    if (trim((string)($c['smtp_host'] ?? '')) !== '') return hub_smtp($c, $od, $do, $tem, $tr, $nag);
    if (!function_exists('mail')) { $GLOBALS['hub_mail_blad'] = 'funkcja mail() jest wyłączona na hostingu – dopisz dane SMTP w hub_config.php'; return false; }
    return @mail($do, $tem, $tr, $nag, '-f' . $od);
}
// Wysyłka przez SMTP (gdy hosting wyłączył mail()). hub_config.php: 'smtp_host' => 'mail.twojadomena.pl', 'smtp_port' => 465 (SSL) lub 587 (STARTTLS),
// 'smtp_user' => 'info@…', 'smtp_pass' => '…'. Hasło tylko w hub_config.php na serwerze – nigdy w repozytorium.
function hub_smtp(array $c, string $od, string $do, string $temat, string $tresc, string $nag): bool {
    $host = trim((string)$c['smtp_host']); $port = (int)($c['smtp_port'] ?? 465); $blad = '';
    $s = @stream_socket_client(($port === 465 ? 'ssl://' : 'tcp://') . "$host:$port", $en, $es, 15);
    if (!$s) { $GLOBALS['hub_mail_blad'] = "brak połączenia z $host:$port ($es)"; return false; }
    stream_set_timeout($s, 15);
    $czyt = function () use ($s) { $r = ''; while (($l = fgets($s, 1024)) !== false) { $r .= $l; if (strlen($l) < 4 || $l[3] === ' ') break; } return $r; };
    $kom = function (string $k, array $ok) use ($s, $czyt, &$blad) { if ($k !== '') fwrite($s, $k . "\r\n"); $r = $czyt();
        if (!in_array((int)substr($r, 0, 3), $ok, true)) { $blad = trim($r) ?: 'brak odpowiedzi serwera'; return false; } return true; };
    $ehlo = 'EHLO ' . (preg_replace('/[^a-z0-9.\-]/i', '', (string)($_SERVER['HTTP_HOST'] ?? '')) ?: 'localhost');
    $ok = $kom('', [220]) && $kom($ehlo, [250]);
    if ($ok && $port !== 465) $ok = $kom('STARTTLS', [220]) && @stream_socket_enable_crypto($s, true, STREAM_CRYPTO_METHOD_TLS_CLIENT) && $kom($ehlo, [250]);
    $u = (string)($c['smtp_user'] ?? '');
    if ($ok && $u !== '') $ok = $kom('AUTH LOGIN', [334]) && $kom(base64_encode($u), [334]) && $kom(base64_encode((string)($c['smtp_pass'] ?? '')), [235]);
    $tr = preg_replace('/^\./m', '..', str_replace(["\r\n", "\n"], ["\n", "\r\n"], $tresc));
    if ($ok) $ok = $kom("MAIL FROM:<$od>", [250]) && $kom("RCPT TO:<$do>", [250, 251]) && $kom('DATA', [354])
        && $kom("To: <$do>\r\nSubject: $temat\r\nDate: " . date('r') . "\r\n$nag\r\n\r\n$tr\r\n.", [250]);
    @fwrite($s, "QUIT\r\n"); fclose($s);
    if (!$ok) $GLOBALS['hub_mail_blad'] = 'SMTP: ' . ($blad ?: 'błąd szyfrowania');
    return $ok;
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
        $out[$k['klucz']] = $k['ukryj'] ? ['u' => 1] : array_filter(['t' => $k['typ'], 'n' => $k['nazwa'], 'o' => $k['opis'], 'g' => $k['godziny'] ?? null,
            'lat' => $k['lat'] === null ? null : (float)$k['lat'], 'lon' => $k['lon'] === null ? null : (float)$k['lon']], fn($v) => $v !== null);
    return $out;
}
// przesunięte węzły: {nr: [lat, lon]}
function hub_korekty_wezlow(PDO $db): array {
    $out = [];
    foreach ($db->query('SELECT nr, lat, lon FROM korekty_wezlow') as $k) $out[(string)$k['nr']] = [round((float)$k['lat'], 6), round((float)$k['lon'], 6)];
    return $out;
}
function hub_foto_usun(PDO $db, string $tab, int $id): void {
    if (!in_array($tab, ['zgloszenia', 'miejsca'], true)) return;
    @unlink(hub_cfg()['dane'] . '/zdjecia/' . $tab . '_' . $id . '.jpg');
    $db->prepare("UPDATE $tab SET foto = '' WHERE id = ?")->execute([$id]);
}
