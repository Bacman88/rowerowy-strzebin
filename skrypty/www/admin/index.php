<?php
// Panel administratora: zatwierdzanie zgłoszeń stanu dróg. Hasło: 'admin_haslo' w /var/www/<witryna>/hub_config.php
require dirname(__DIR__) . '/api/_db.php';
header('X-Frame-Options: DENY');
header('Cache-Control: no-store, no-cache, must-revalidate, private, max-age=0');
header('Pragma: no-cache'); header('Expires: 0');
header('X-LiteSpeed-Cache-Control: no-cache');   // Joton/LiteSpeed: panel nigdy z pamięci podręcznej serwera
header('X-Robots-Tag: noindex');
session_set_cookie_params(['httponly' => true, 'samesite' => 'Strict', 'secure' => !empty($_SERVER['HTTPS']), 'path' => '/admin/']);
session_name('hub_admin');
session_start();

$cfg = hub_cfg();
// diagnostyka dla zalogowanego administratora: błąd PHP pokazany zamiast pustej strony
if ($_SESSION['ok'] ?? false) {
    ini_set('display_errors', '0');
    register_shutdown_function(function () {
        $e = error_get_last();
        if ($e && in_array($e['type'], [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR], true))
            echo '<pre style="white-space:pre-wrap;padding:16px;background:#fde8e8">Błąd PHP: ' . htmlspecialchars($e['message'] . ' (' . basename($e['file']) . ':' . $e['line'] . ')') . "\nPHP " . PHP_VERSION . '</pre>';
    });
    set_exception_handler(function (Throwable $e) {
        echo '<pre style="white-space:pre-wrap;padding:16px;background:#fde8e8">Wyjątek: ' . htmlspecialchars($e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')') . "\nPHP " . PHP_VERSION . '</pre>';
    });
}
$h = fn($s) => htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8');
$blad = '';

if (isset($_GET['wyloguj'])) { session_destroy(); header('Location: ./'); exit; }

if (!($_SESSION['ok'] ?? false)) {
    if ($cfg['admin_haslo'] !== '' && isset($_POST['haslo'])) {
        if (hash_equals((string)$cfg['admin_haslo'], (string)$_POST['haslo'])) {
            session_regenerate_id(true);
            $_SESSION['ok'] = true; $_SESSION['csrf'] = bin2hex(random_bytes(16));
            header('Location: ./'); exit;
        }
        sleep(2); $blad = 'Złe hasło';
    }
    ?><!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Panel – stan dróg</title>
    <style>body{font:16px/1.5 system-ui,sans-serif;background:#f7f4ec;color:#1d2a23;display:grid;place-items:center;min-height:100vh;margin:0}
    form{background:#fffdf8;border:1px solid #e3dccb;border-radius:12px;padding:24px;width:min(340px,90vw)}
    input,button{font:inherit;width:100%;padding:9px 11px;border-radius:8px;border:1px solid #cfc6b2;margin-top:8px;box-sizing:border-box}
    button{background:#1d3b30;color:#fff;border:0;cursor:pointer}.e{color:#b00020}code{background:#eee6d4;padding:1px 4px;border-radius:4px}</style>
    <form method="post"><h2 style="margin:0 0 6px">Panel – stan dróg</h2>
    <?php if ($cfg['admin_haslo'] === ''): ?>
      <p>Panel jest wyłączony: brak hasła. Utwórz plik <code>hub_config.php</code> obok katalogu <code>public_html</code> (instrukcja w README repozytorium).</p>
    <?php else: ?>
      <?= $blad ? '<p class="e">' . $h($blad) . '</p>' : '' ?>
      <input type="password" name="haslo" placeholder="Hasło" autofocus required><button>Zaloguj</button>
    <?php endif ?></form></html><?php
    exit;
}

try { $db = hub_db(); } catch (Throwable $e) {
    // zalogowany administrator widzi przyczynę (zwykle: brak sterownika SQLite albo prawa zapisu do katalogu danych)
    http_response_code(500);
    echo '<!doctype html><meta charset="utf-8"><body style="font:16px/1.5 system-ui;padding:24px;max-width:760px">'
       . '<h2>Baza danych niedostępna</h2><p>' . $h($e->getMessage()) . '</p>'
       . '<p>Katalog danych: <code>' . $h($cfg['dane']) . '</code><br>Sterowniki PDO: <code>' . $h(implode(', ', PDO::getAvailableDrivers())) . '</code>'
       . '<br>PHP: <code>' . PHP_VERSION . '</code> · open_basedir: <code>' . $h((string)ini_get('open_basedir')) . '</code></p>'
       . '<p><a href="?wyloguj=1">wyloguj</a></p>';
    exit;
}

// korekta miejsca z mapy panelu (fetch): zapisz / ukryj / pokaż / cofnij – odpowiedź JSON
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['akcja'] ?? '') === 'korekta') {
    if (!hash_equals($_SESSION['csrf'] ?? '', (string)($_POST['csrf'] ?? ''))) hub_json(['blad' => 'Błędny token – odśwież stronę'], 400);
    $kl = mb_substr((string)($_POST['klucz'] ?? ''), 0, 80);
    if (!preg_match('/^(db|poi|stacja|stale|osm):.+$/u', $kl)) hub_json(['blad' => 'Nieznane miejsce'], 400);
    $op = (string)($_POST['op'] ?? '');
    $jest = $db->prepare('SELECT * FROM korekty_miejsc WHERE klucz = ?'); $jest->execute([$kl]); $jest = $jest->fetch();
    $zapisz = function (array $w) use ($db, $kl, $jest) {
        $w['zmieniono'] = hub_teraz();
        if ($jest) { $db->prepare('UPDATE korekty_miejsc SET ' . implode(', ', array_map(fn($c) => "$c = ?", array_keys($w))) . ' WHERE klucz = ?')->execute([...array_values($w), $kl]); }
        else { $w['klucz'] = $kl; $db->prepare('INSERT INTO korekty_miejsc (' . implode(', ', array_keys($w)) . ') VALUES (' . implode(',', array_fill(0, count($w), '?')) . ')')->execute(array_values($w)); }
    };
    if ($op === 'cofnij') $db->prepare('DELETE FROM korekty_miejsc WHERE klucz = ?')->execute([$kl]);
    elseif ($op === 'ukryj') $zapisz(['ukryj' => 1]);
    elseif ($op === 'pokaz') {
        if ($jest && $jest['typ'] === null && $jest['lat'] === null && $jest['nazwa'] === null && $jest['opis'] === null) $db->prepare('DELETE FROM korekty_miejsc WHERE klucz = ?')->execute([$kl]);
        elseif ($jest) $zapisz(['ukryj' => 0]);
    } elseif ($op === 'zapisz') {
        $typ = (string)($_POST['typ'] ?? ''); $lat = (float)($_POST['lat'] ?? 0); $lon = (float)($_POST['lon'] ?? 0);
        if (!in_array($typ, TYPY_MIEJSC, true) && $typ !== 'stacja') hub_json(['blad' => 'Nieznany rodzaj miejsca'], 400);
        if ($lat < 50.40 || $lat > 50.85 || $lon < 18.55 || $lon > 19.25) hub_json(['blad' => 'Położenie poza mapą'], 400);
        $zapisz(['ukryj' => 0, 'typ' => $typ, 'nazwa' => hub_txt($_POST, 'nazwa', 80), 'opis' => hub_txt($_POST, 'opis', 1000), 'lat' => round($lat, 6), 'lon' => round($lon, 6)]);
    } else hub_json(['blad' => 'Nieznana operacja'], 400);
    hub_json(['ok' => true, 'korekty' => hub_korekty($db)]);
}
if (isset($_GET['test_maila'])) {   // próbna wiadomość – sprawdzenie, czy powiadomienia dochodzą
    $ok = hub_powiadom('Test powiadomień', "To jest próbna wiadomość z panelu mapy wspólnej (" . hub_teraz() . ").\nJeśli ją widzisz, powiadomienia o nowych zgłoszeniach działają.", '', true);
    $do = hub_cfg()['powiadom'];
    header('Content-Type: text/html; charset=utf-8');
    echo '<p style="font:16px system-ui;margin:30px">' . ($do === '' ? 'Brak adresu: dopisz w hub_config.php <code>\'powiadom\' => \'twój@adres\'</code>.'
        : ($ok ? 'Wysłano próbną wiadomość na <b>' . htmlspecialchars($do) . '</b>. Sprawdź skrzynkę (także SPAM).' : 'Serwer nie przyjął wiadomości – funkcja mail() jest wyłączona albo źle skonfigurowana na hostingu.'))
        . '</p><p style="font:16px system-ui;margin:30px"><a href="./">← wróć do panelu</a></p>'; exit;
}
if (($_GET['eksport'] ?? '') === 'miejsca') {   // korekty miejsc – do przeniesienia do projektu (cele lokalne na tabliczkach i mapach PDF)
    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="korekty_miejsc_' . date('Y-m-d') . '.json"');
    echo json_encode($db->query('SELECT * FROM korekty_miejsc ORDER BY klucz')->fetchAll(), JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT); exit;
}
if (isset($_GET['eksport'])) {   // zatwierdzone zmiany węzłów – do wdrożenia w projekcie (dane/wezly_zatwierdzone.json w repozytorium)
    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="wezly_zatwierdzone_' . date('Y-m-d') . '.json"');
    $r = $db->query("SELECT id, utworzono, moderowano, wezel, lat, lon, slupek, zmiany, komentarz, nick FROM wezly WHERE moderacja = 'zatwierdzone' ORDER BY id")->fetchAll();
    foreach ($r as &$w) { $w['zmiany'] = json_decode($w['zmiany'], true); $w['wezel'] = $w['wezel'] === null ? null : (int)$w['wezel']; }
    echo json_encode($r, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT); exit;
}
if (isset($_GET['foto'])) {   // zdjęcie zgłoszenia – tylko dla zalogowanego administratora
    $p = basename((string)$_GET['foto']);
    $f = $cfg['dane'] . '/zdjecia/' . $p;
    if (!preg_match('/^(zgloszenia|miejsca)_\d+\.jpg$/', $p) || !is_file($f)) { http_response_code(404); exit('Brak zdjęcia'); }
    header('Content-Type: image/jpeg'); header('Content-Length: ' . filesize($f)); readfile($f); exit;
}
if (isset($_GET['kopia'])) {
    header('Content-Type: application/json; charset=utf-8');
    header('Content-Disposition: attachment; filename="stan_drog_' . date('Y-m-d') . '.json"');
    echo json_encode(hub_zrzut(), JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT); exit;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!hash_equals($_SESSION['csrf'] ?? '', (string)($_POST['csrf'] ?? ''))) { http_response_code(400); exit('Błędny token – odśwież stronę.'); }
    $nowy = ['zatwierdz' => 'zatwierdzone', 'odrzuc' => 'odrzucone', 'wycofaj' => 'wycofane', 'przywroc' => 'oczekuje'][$_POST['akcja'] ?? ''] ?? null;
    $ids = array_filter(array_map('intval', (array)($_POST['id'] ?? [])));
    if ($nowy && $ids) {
        $tab = ['miejsca' => 'miejsca', 'wezly' => 'wezly', 'trasy' => 'trasy'][$_POST['t'] ?? ''] ?? 'zgloszenia';
        $u = $db->prepare("UPDATE $tab SET moderacja = ?, moderowano = ? WHERE id = ?");
        foreach ($ids as $i) {
            $u->execute([$nowy, hub_teraz(), $i]);
            // zdjęcie służy tylko do sprawdzenia zgłoszenia – po decyzji (zatwierdź/odrzuć) usuwamy je z serwera
            if (in_array($nowy, ['zatwierdzone', 'odrzucone'], true)) hub_foto_usun($db, $tab, $i);
        }
    }
    header('Location: ./?t=' . urlencode($_POST['t'] ?? 'drogi') . '&k=' . urlencode($_POST['k'] ?? 'oczekuje')); exit;
}

$k = in_array($_GET['k'] ?? '', ['oczekuje', 'zatwierdzone', 'odrzucone', 'wycofane'], true) ? $_GET['k'] : 'oczekuje';
$tryb = in_array($_GET['t'] ?? '', ['miejsca', 'wezly', 'trasy', 'mapa'], true) ? $_GET['t'] : 'drogi';
$tab = ['miejsca' => 'miejsca', 'wezly' => 'wezly', 'trasy' => 'trasy'][$tryb] ?? 'zgloszenia';
$licz = []; $czeka = [];
foreach ($db->query("SELECT moderacja, COUNT(*) n FROM $tab GROUP BY moderacja") as $r) $licz[$r['moderacja']] = (int)$r['n'];
foreach (['drogi' => 'zgloszenia', 'miejsca' => 'miejsca', 'wezly' => 'wezly', 'trasy' => 'trasy'] as $tt => $tb) $czeka[$tt] = (int)$db->query("SELECT COUNT(*) FROM $tb WHERE moderacja = 'oczekuje'")->fetchColumn();
$q = $db->prepare("SELECT * FROM $tab WHERE moderacja = ? ORDER BY utworzono " . ($k === 'oczekuje' ? 'ASC' : 'DESC') . ' LIMIT 200');
$q->execute([$k]); $lista = $q->fetchAll();
$odc = [];
if ($lista && $tryb === 'drogi') {
    $in = implode(',', array_map(fn($r) => (int)$r['id'], $lista));
    foreach ($db->query("SELECT zgloszenie, odcinek FROM zgloszenia_odcinki WHERE zgloszenie IN ($in)") as $r) $odc[$r['zgloszenie']][] = $r['odcinek'];
}
$TYPY = ['lawka' => 'ławka', 'wiata' => 'wiata', 'piknik' => 'piknik / ognisko', 'widok' => 'punkt widokowy', 'zabawa' => 'plac zabaw', 'woda' => 'woda pitna',
    'serwis' => 'serwis rowerowy', 'stojak' => 'stojak na rowery', 'wypozycz' => 'wypożyczalnia', 'wc' => 'WC', 'parking' => 'parking', 'apteczka' => 'pierwsza pomoc / AED',
    'info' => 'tablica informacyjna', 'jedzenie' => 'restauracja', 'kawa' => 'kawiarnia', 'bar' => 'bar', 'nocleg' => 'nocleg', 'ciekawe' => 'ciekawe miejsce',
    'zabytek' => 'zabytek / pomnik', 'kosciol' => 'kościół / kapliczka', 'przyroda' => 'przyroda', 'sport' => 'sport i rekreacja'];
$NAZWY = ['dobra' => 'dobra', 'srednia' => 'średnia', 'trudna' => 'trudna', 'nieprzejezdna' => 'nieprzejezdna'];
$AKCJE = ['oczekuje' => [['zatwierdz', 'Zatwierdź', 'ok'], ['odrzuc', 'Odrzuć', 'no']],
          'zatwierdzone' => [['wycofaj', 'Wycofaj z mapy', 'no']],
          'odrzucone' => [['przywroc', 'Przywróć do oczekujących', '']],
          'wycofane' => [['przywroc', 'Przywróć do oczekujących', '']]];
$csrf = $h($_SESSION['csrf']);
?><!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel – mapa wspólna</title>
<link rel="icon" href="../favicon.svg" type="image/svg+xml"><link rel="icon" href="../favicon-32.png" type="image/png" sizes="32x32">
<link rel="stylesheet" href="../lib/leaflet.css">
<style>
:root{--bg:#f7f4ec;--card:#fffdf8;--ink:#1d2a23;--muted:#56665c;--line:#e3dccb;--green:#1d3b30}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,Inter,sans-serif}
header{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--line);background:var(--card)}
header h1{font-size:18px;margin:0}header a{color:var(--green)}
.tabs{display:flex;gap:6px;flex-wrap:wrap}.tabs a{padding:5px 10px;border-radius:8px;text-decoration:none;border:1px solid var(--line);color:var(--ink)}
.tabs a.on{background:var(--green);color:#fff;border-color:var(--green)}
.tryb a{font-weight:700}.tryb i{font-style:normal;background:#d62828;color:#fff;border-radius:9px;padding:0 6px;font-size:12px;margin-left:4px}
main{display:grid;grid-template-columns:minmax(320px,440px) 1fr;height:calc(100vh - 58px)}
.list{overflow:auto;padding:12px;border-right:1px solid var(--line)}
#map{height:100%}
.z{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:10px;cursor:pointer}
.z.on{border-color:var(--green);box-shadow:0 0 0 2px rgba(29,59,48,.25)}
.z .m{font-size:12.5px;color:var(--muted)}.z p{margin:6px 0;white-space:pre-wrap}
.chip{display:inline-block;padding:1px 8px;border-radius:6px;font-size:12px;font-weight:700;color:#fff}
.c-dobra{background:#2b9348}.c-srednia{background:#e0a800;color:#000}.c-trudna{background:#d62828}.c-nieprzejezdna{background:repeating-linear-gradient(45deg,#111 0 3px,#fff 3px 6px) left/13px 100% no-repeat,#111;color:#fff;padding-left:17px}
.priv{background:#fff4d6;border-radius:6px;padding:2px 6px;font-size:12.5px}
form.a{display:flex;gap:6px;margin-top:6px}
button{font:inherit;font-size:13px;padding:5px 11px;border-radius:7px;border:1px solid var(--line);background:#fff;cursor:pointer}
button.ok{background:#2b9348;color:#fff;border-color:#2b9348}button.no{background:#fff;color:#b00020;border-color:#e2b4ba}
.empty{color:var(--muted);padding:20px 4px}
@media (max-width:800px){main{grid-template-columns:1fr;height:auto}#map{height:50vh;order:-1}.list{border-right:0}}
[hidden]{display:none!important}
.edbox{background:var(--card);border:1px solid var(--green);box-shadow:0 0 0 2px rgba(29,59,48,.25);border-radius:10px;padding:10px 12px;margin:10px 0}
.fl{display:block;font-size:13px;color:var(--muted);margin-top:8px}.fl input,.fl select,.fl textarea{display:block;width:100%;font:inherit;font-size:14.5px;color:var(--ink);padding:6px 9px;border:1px solid var(--line);border-radius:7px;margin-top:3px;background:#fff}
#wyniki a{display:block;padding:5px 2px;border-bottom:1px dashed var(--line);cursor:pointer;color:var(--ink);text-decoration:none}#wyniki a:hover{background:#efe9da}
#lista-k a{cursor:pointer;color:var(--green)}
.foto img{display:block;max-width:100%;max-height:260px;border-radius:8px;margin:6px 0 2px;border:1px solid var(--line)}
.wzp svg{width:100%;height:auto;display:block;margin:4px 0}.wzp .m{margin-top:6px}
@font-face{font-family:'Fira Sans Condensed';font-weight:600;src:url(../lib/fonts/FiraSansCondensed-SemiBold.ttf) format('truetype')}
.wzm{width:22px;height:22px;border-radius:50%;display:grid;place-items:center;color:#fff;background:#00838F;font:700 10px system-ui;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.35)}
</style></head><body>
<header>
  <h1>Panel</h1>
  <nav class="tabs tryb">
    <?php foreach (['drogi' => 'Stan dróg', 'miejsca' => 'Miejsca', 'wezly' => 'Węzły i tabliczki', 'trasy' => 'Trasy', 'mapa' => 'Miejsca na mapie – edycja'] as $tt => $t): ?>
      <a href="?t=<?= $tt ?>" class="<?= $tryb === $tt ? 'on' : '' ?>"><?= $t ?><?= ($czeka[$tt] ?? 0) ? '<i>' . $czeka[$tt] . '</i>' : '' ?></a>
    <?php endforeach ?>
  </nav>
  <nav class="tabs"<?= $tryb === 'mapa' ? ' hidden' : '' ?>>
    <?php foreach (['oczekuje' => 'Oczekujące', 'zatwierdzone' => 'Zatwierdzone', 'odrzucone' => 'Odrzucone', 'wycofane' => 'Wycofane'] as $kk => $t): ?>
      <a href="?t=<?= $tryb ?>&k=<?= $kk ?>" class="<?= $k === $kk ? 'on' : '' ?>"><?= $t ?> (<?= $licz[$kk] ?? 0 ?>)</a>
    <?php endforeach ?>
  </nav>
  <span style="margin-left:auto"><a href="../#wspolna" target="_blank">mapa publiczna</a> · <a href="?kopia=1">pobierz kopię (JSON)</a> · <a href="?eksport=wezly" title="zatwierdzone zmiany węzłów do wdrożenia w projekcie">eksport węzłów</a> · <a href="?eksport=miejsca" title="poprawki miejsc z mapy">eksport poprawek miejsc</a> · <a href="?test_maila=1" title="wyślij próbną wiadomość na adres z hub_config.php">test powiadomień</a> · <a href="?wyloguj=1">wyloguj</a></span>
</header>
<main>
  <?php if ($tryb === 'mapa'): ?>
  <div class="list" id="ed">
    <p class="m" style="margin-top:0">Kliknij miejsce na mapie albo wyszukaj je po nazwie. <b>Przeciągnij znacznik</b>, żeby go przesunąć, popraw rodzaj, nazwę lub opis i zapisz. Zmiany widać od razu na stronie. Ukryte miejsca widzisz tu półprzezroczyste.</p>
    <input type="search" id="szukaj" placeholder="Szukaj: nazwa albo rodzaj (np. ławka, Zagroda)" style="width:100%;font:inherit;padding:7px 10px;border:1px solid var(--line);border-radius:8px">
    <div id="wyniki"></div>
    <div class="edbox" id="ed-form" hidden>
      <div class="m" id="ed-zrodlo"></div>
      <label class="fl">Rodzaj<select id="ed-typ"></select></label>
      <label class="fl">Nazwa<input id="ed-nazwa" maxlength="80"></label>
      <label class="fl">Opis<textarea id="ed-opis" maxlength="1000" rows="3"></textarea></label>
      <div class="m">Położenie: <span id="ed-poz"></span> <span id="ed-przes" style="color:#b45309"></span></div>
      <div class="m" id="ed-oryg"></div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">
        <button class="ok" id="ed-zapisz">Zapisz zmiany</button><button class="no" id="ed-ukryj">Usuń z mapy</button><button id="ed-cofnij">Przywróć oryginał</button>
      </div>
      <div class="m" id="ed-msg"></div>
    </div>
    <h3 style="font-size:15px;margin:16px 0 6px">Poprawione miejsca (<span id="ile-k">0</span>)</h3>
    <div id="lista-k" class="m"></div>
    <p class="m">Piktogramy celów lokalnych (kościoły, gastronomia, zabytki) są też na tabliczkach i mapach PDF – ich zmiany przenieś do projektu: „eksport poprawek miejsc”.</p>
  </div>
  <?php else: ?>
  <div class="list">
    <?php if (!$lista): ?><div class="empty">Brak zgłoszeń w tej zakładce.</div><?php endif ?>
    <?php foreach ($lista as $r): ?>
      <?php if ($tryb === 'wezly'): $zm = json_decode($r['zmiany'], true) ?: []; ?>
      <div class="z" data-id="<?= (int)$r['id'] ?>" data-lat="<?= (float)$r['lat'] ?>" data-lon="<?= (float)$r['lon'] ?>" data-wezel="<?= $r['wezel'] === null ? '' : (int)$r['wezel'] ?>" data-zm="<?= $h($r['zmiany']) ?>">
        <div><span class="chip" style="background:#00838F"><?= $r['wezel'] === null ? 'nowy węzeł' . ($r['slupek'] ? ' · słupek: ' . ($r['slupek'] === 'nowy' ? 'do postawienia' : 'jest') : '') : 'węzeł ' . (int)$r['wezel'] ?></span> <b><?= $h($r['nick']) ?></b></div>
        <div class="m">#<?= (int)$r['id'] ?> · zgłoszono <?= $h($r['utworzono']) ?><?= $r['moderowano'] ? ' · decyzja ' . $h($r['moderowano']) : '' ?></div>
        <p><?php foreach ($zm['usun'] ?? [] as $n): ?><span style="color:#b00020">− <?= $h($n) ?></span><br><?php endforeach ?>
           <?php foreach ($zm['dodaj'] ?? [] as $c): ?><span style="color:#1b5e20">+ <?= $h($c['n']) ?> <?= $h($c['km']) ?> <?= $c['d'] === 'left' ? '←' : '→' ?><?= $c['rts'] ? ' (trasy ' . $h(implode(', ', $c['rts'])) . ')' : '' ?></span><br><?php endforeach ?></p>
        <?php if ((string)$r['komentarz'] !== ''): ?><p><?= $h($r['komentarz']) ?></p><?php endif ?>
        <div class="wzp"></div>
      <?php elseif ($tryb === 'trasy'): ?>
      <div class="z" data-id="<?= (int)$r['id'] ?>" data-trasa="1">
        <div><span class="chip" style="background:#0f766e">trasa · <?= number_format((float)$r['km'], 1, ',', '') ?> km</span> <b><?= $h($r['nick']) ?></b></div>
        <div class="m">#<?= (int)$r['id'] ?> · zgłoszono <?= $h($r['utworzono']) ?><?= $r['moderowano'] ? ' · decyzja ' . $h($r['moderowano']) : '' ?></div>
        <p><b><?= $h($r['nazwa']) ?></b></p>
        <?php if ((string)$r['opis'] !== ''): ?><p><?= $h($r['opis']) ?></p><?php endif ?>
      <?php elseif ($tryb === 'miejsca'): ?>
      <div class="z" data-id="<?= (int)$r['id'] ?>" data-typ="<?= $h($r['typ']) ?>" data-lat="<?= (float)$r['lat'] ?>" data-lon="<?= (float)$r['lon'] ?>">
        <div><span class="chip" style="background:#237647"><?= $h($TYPY[$r['typ']] ?? $r['typ']) ?></span> <b><?= $h($r['nick']) ?></b></div>
        <div class="m">#<?= (int)$r['id'] ?> · zgłoszono <?= $h($r['utworzono']) ?><?= $r['moderowano'] ? ' · decyzja ' . $h($r['moderowano']) : '' ?></div>
        <?php if ($r['nazwa'] !== ''): ?><p><b><?= $h($r['nazwa']) ?></b></p><?php endif ?>
        <?php if ((string)$r['opis'] !== ''): ?><p><?= $h($r['opis']) ?></p><?php endif ?>
      <?php else: $n = count($odc[$r['id']] ?? []); ?>
      <div class="z" data-id="<?= (int)$r['id'] ?>" data-stan="<?= $h($r['stan']) ?>">
        <div><span class="chip c-<?= $h($r['stan']) ?>"><?= $h($NAZWY[$r['stan']] ?? $r['stan']) ?></span>
          <b><?= $h($r['nick']) ?></b> · <?= $n ?> odc.</div>
        <div class="m">#<?= (int)$r['id'] ?> · zgłoszono <?= $h($r['utworzono']) ?><?= $r['data_przejazdu'] ? ' · przejazd ' . $h($r['data_przejazdu']) : '' ?><?= $r['moderowano'] ? ' · decyzja ' . $h($r['moderowano']) : '' ?></div>
        <?php if ($r['komentarz'] !== '' && $r['komentarz'] !== null): ?><p><?= $h($r['komentarz']) ?></p><?php endif ?>
      <?php endif ?>
        <?php if (($r['foto'] ?? '') !== ''): ?><a href="?foto=<?= $h($r['foto']) ?>" target="_blank" class="foto"><img src="?foto=<?= $h($r['foto']) ?>" alt="zdjęcie do zgłoszenia" loading="lazy"></a>
          <div class="m">Zdjęcie zostanie usunięte z serwera po zatwierdzeniu albo odrzuceniu.</div><?php endif ?>
        <?php if ($r['kontakt'] !== ''): ?><div class="priv">kontakt (tylko dla Ciebie): <?= $h($r['kontakt']) ?></div><?php endif ?>
        <form class="a" method="post"><input type="hidden" name="csrf" value="<?= $csrf ?>"><input type="hidden" name="k" value="<?= $k ?>"><input type="hidden" name="t" value="<?= $tryb ?>">
          <input type="hidden" name="id[]" value="<?= (int)$r['id'] ?>">
          <?php foreach ($AKCJE[$k] as [$a, $t, $cl]): ?><button name="akcja" value="<?= $a ?>" class="<?= $cl ?>"><?= $t ?></button><?php endforeach ?>
        </form>
      </div>
    <?php endforeach ?>
  </div>
  <?php endif ?>
  <div id="map"></div>
</main>
<script src="../lib/leaflet.js"></script>
<script src="../stan/odcinki.js"></script>
<script>window.HUB_BASE = "../";</script>
<script src="../data.js"></script>
<script src="../lib/ikony.js"></script>
<script src="../lib/miejsca.js"></script>
<script src="../lib/tabliczka-dane.js"></script>
<script src="../lib/tabliczka.js"></script>
<script>
const ODC_Z = <?= json_encode($odc, JSON_UNESCAPED_UNICODE) ?>;
const TRASY_G = <?= json_encode($tryb === 'trasy' ? array_column(array_map(fn($r) => ['id' => (int)$r['id'], 'g' => json_decode($r['geom'], true), 'p' => json_decode($r['punkty'], true)], $lista), null, 'id') : new stdClass()) ?>;
const KOL = {dobra:'#2b9348', srednia:'#e0a800', trudna:'#d62828', nieprzejezdna:'#111'};
const map = L.map('map', {preferCanvas:true});
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19, attribution:'© OpenStreetMap'}).addTo(map);
const geo = {}; const all = [];
for (const s of window.ODC) { const c = s[7], ll = []; for (let i = 0; i < c.length; i += 2) ll.push([c[i], c[i+1]]); geo[s[0]] = ll; }
for (const [o, ns] of Object.entries(window.ODC_ALIASY || {})) geo[o] = ns.flatMap(n => geo[n] || []);
const tlo = L.layerGroup().addTo(map);
for (const id in geo) L.polyline(geo[id], {color:'#8a9399', weight:2, opacity:.45, interactive:false}).addTo(tlo);
const sel = L.layerGroup().addTo(map);
// istniejące miejsca – żeby od razu widzieć duplikaty
const ML = MIEJSCA.warstwy(map, (window.HUB && HUB.places) || []); Object.values(ML).forEach(l => l.addTo(map));
let first = true;
function pokaz(id, stan, fit) {
  sel.clearLayers(); const b = [];
  for (const o of (ODC_Z[id] || [])) if (geo[o]) {
    L.polyline(geo[o], {color:'#fff', weight:10, opacity:.9}).addTo(sel);
    L.polyline(geo[o], {color:KOL[stan] || '#1d4ed8', weight:6, dashArray: stan === 'nieprzejezdna' ? '6 6' : null}).addTo(sel);
    b.push(...geo[o]);
  }
  if (b.length && fit) map.fitBounds(b, {padding:[40,40], maxZoom:16});
}
document.querySelectorAll('.z').forEach(el => el.addEventListener('click', e => {
  if (e.target.closest('form')) return;
  document.querySelectorAll('.z.on').forEach(x => x.classList.remove('on')); el.classList.add('on');
  if (el.dataset.trasa) {
    sel.clearLayers(); const t = TRASY_G[el.dataset.id]; if (!t) return;
    L.polyline(t.g, {color:'#fff', weight:9, opacity:.9}).addTo(sel);
    const ln = L.polyline(t.g, {color:'#0f766e', weight:5}).addTo(sel);
    t.p.forEach((p, i) => L.circleMarker(p, {radius:6, color:'#fff', weight:2, fillColor: i ? (i === t.p.length - 1 ? '#b00020' : '#0f766e') : '#2b9348', fillOpacity:1}).addTo(sel));
    map.fitBounds(ln.getBounds(), {padding:[40, 40]});
  } else if (el.dataset.zm) {
    sel.clearLayers(); const ll = [+el.dataset.lat, +el.dataset.lon];
    L.circle(ll, {radius: 30, color: '#1d4ed8', weight: 3, fill: false}).addTo(sel); map.setView(ll, 16);
  } else if (el.dataset.typ) {
    sel.clearLayers(); const ll = [+el.dataset.lat, +el.dataset.lon];
    L.marker(ll, {icon: MIEJSCA.icon({typ: el.dataset.typ})}).addTo(sel);
    L.circle(ll, {radius: 25, color: '#1d4ed8', weight: 2, fill: false}).addTo(sel);
    map.setView(ll, 17);
  } else pokaz(el.dataset.id, el.dataset.stan, true);
}));
// węzły na mapie i podgląd tabliczek „po zmianie” (ten sam rysunek co na stronie)
if (window.HUB) for (const p of HUB.posts) L.marker([p.lat, p.lon], {icon: L.divIcon({className: '', html: `<div class="wzm">${p.nr}</div>`, iconSize: [22, 22], iconAnchor: [11, 11]}), interactive: false}).addTo(map);
document.querySelectorAll('.z[data-zm]').forEach(el => {
  const zm = JSON.parse(el.dataset.zm || '{}'), p = el.dataset.wezel ? HUB.posts.find(q => q.nr === +el.dataset.wezel) : null;
  const cele = [];
  if (p) for (const t of p.tab) t.e.forEach(([n, km, ico, rts]) => { if (!(zm.usun || []).includes(n)) cele.push({n, km, kmv: parseFloat(km.replace(',', '.')), ico, rts, d: t.d, cat: t.cat}); });
  (zm.dodaj || []).forEach(c => cele.push({...c, kmv: parseFloat(String(c.km).replace(',', '.'))}));
  el.querySelector('.wzp').innerHTML = '<div class="m">Tabliczki po zmianie:</div>' + TABLICZKA.tabliczki(cele).map(t => { const r = TABLICZKA.svg(t.d, 800, t.cat, t.e); return r.svg + (r.uwaga ? '<div class="m">⚠ ' + r.uwaga + '</div>' : ''); }).join('');
});
const pierwszy = document.querySelector('.z');
map.setView([50.62, 18.88], 12);
if (pierwszy) pierwszy.click();
<?php if ($tryb === 'mapa'): ?>
// ===== Edycja miejsc na mapie: korekty (przesunięcie, rodzaj, nazwa, opis, ukrycie) zapisywane w tabeli korekty_miejsc =====
(() => {
  Object.values(ML).forEach(l => map.removeLayer(l));
  const CSRF = <?= json_encode($_SESSION['csrf']) ?>, $ = id => document.getElementById(id), E = MIEJSCA.esc;
  let K = <?= json_encode(hub_korekty($db), JSON_UNESCAPED_UNICODE) ?: '{}' ?>;
  let P = (HUB.places || []).filter(m => m.k).map(m => ({...m}));
  const ZR = k => ({poi: 'cel lokalny projektu (też na tabliczkach)', stacja: 'planowana stacja napraw (projekt)', stale: 'miejsce dodane w projekcie', osm: 'z OpenStreetMap', db: 'zgłoszenie mieszkańca'})[k.split(':')[0]] || '';
  $('ed-typ').innerHTML = Object.entries(MIEJSCA.TYP).map(([t, v]) => `<option value="${t}">${v.n}</option>`).join('');
  const warstwa = L.layerGroup().addTo(map); let wyb = null, mk = {};
  const ukryte = k => !!(K[k] && K[k].u);
  // miejsce po korekcie, ale ukryte też pokazujemy (półprzezroczyste)
  const biez = m => { const k = K[m.k]; if (k && k.u) { const z = MIEJSCA.popraw(m, {}); return z; } return MIEJSCA.popraw(m, K); };
  function rysuj() {
    warstwa.clearLayers(); mk = {};
    for (const m of P) {
      const z = biez(m); if (!MIEJSCA.TYP[z.typ]) continue;
      const mm = L.marker([z.lat, z.lon], {icon: MIEJSCA.icon(z), draggable: true, opacity: ukryte(m.k) ? .35 : 1, title: z.nazwa || MIEJSCA.TYP[z.typ].n, zIndexOffset: wyb === m ? 1000 : 0})
        .on('click', () => wybierz(m)).on('dragend', e => { wybierz(m, false); const q = e.target.getLatLng(); poz = [q.lat, q.lng]; pokazPoz(); }).addTo(warstwa);
      mk[m.k] = mm;
    }
    if (wyb && mk[wyb.k]) L.circle(mk[wyb.k].getLatLng(), {radius: 18, color: '#1d4ed8', weight: 3, fill: false, interactive: false}).addTo(warstwa);
    const kk = Object.keys(K).filter(k => P.some(m => m.k === k));
    $('ile-k').textContent = kk.length;
    $('lista-k').innerHTML = kk.map(k => { const m = P.find(x => x.k === k), z = biez(m);
      return `<div><a data-k="${E(k)}">${E(z.nazwa || MIEJSCA.TYP[z.typ]?.n || k)}</a> – ${K[k].u ? 'usunięte z mapy' : 'poprawione'}</div>`; }).join('') || 'brak';
    $('lista-k').querySelectorAll('a').forEach(a => a.onclick = () => { const m = P.find(x => x.k === a.dataset.k); wybierz(m); map.setView([biez(m).lat, biez(m).lon], 17); });
  }
  let poz = null;
  const pokazPoz = () => { const z = biez(wyb); $('ed-poz').textContent = poz[0].toFixed(5) + ', ' + poz[1].toFixed(5);
    const d = map.distance(poz, [z.lat, z.lon]); $('ed-przes').textContent = d > 1 ? `(przesunięte o ${Math.round(d)} m – zapisz)` : ''; };
  function wybierz(m, centruj) {
    wyb = m; const z = biez(m); poz = [z.lat, z.lon];
    $('ed-form').hidden = false; $('ed-msg').textContent = '';
    $('ed-zrodlo').innerHTML = `<b>${E(ZR(m.k))}</b>${ukryte(m.k) ? ' · <span style="color:#b00020">usunięte z mapy</span>' : ''}`;
    $('ed-typ').value = z.typ; $('ed-nazwa').value = z.nazwa || ''; $('ed-opis').value = z.opis || '';
    $('ed-oryg').innerHTML = K[m.k] && !K[m.k].u ? `Oryginał: ${E(MIEJSCA.TYP[m.typ]?.n || m.typ)}${m.nazwa ? ' · ' + E(m.nazwa) : ''} · ${m.lat.toFixed(5)}, ${m.lon.toFixed(5)}` : '';
    $('ed-ukryj').textContent = ukryte(m.k) ? 'Pokaż z powrotem' : 'Usuń z mapy';
    $('ed-cofnij').hidden = !K[m.k];
    pokazPoz(); rysuj();
    if (centruj) map.setView(poz, Math.max(map.getZoom(), 16));
  }
  async function wyslij(op, pola = {}) {
    const fd = new FormData(); fd.append('akcja', 'korekta'); fd.append('csrf', CSRF); fd.append('klucz', wyb.k); fd.append('op', op);
    for (const [k, v] of Object.entries(pola)) fd.append(k, v);
    try {
      const r = await fetch('./', {method: 'POST', body: fd, headers: {'Accept': 'application/json'}}); const j = await r.json();
      if (!j.ok) throw new Error(j.blad || 'Nie udało się zapisać');
      K = j.korekty || {}; wybierz(wyb); $('ed-msg').textContent = 'Zapisano – zmiana jest już na stronie.';
    } catch (e) { $('ed-msg').textContent = '⚠ ' + e.message; }
  }
  $('ed-zapisz').onclick = () => wyslij('zapisz', {typ: $('ed-typ').value, nazwa: $('ed-nazwa').value, opis: $('ed-opis').value, lat: poz[0], lon: poz[1]});
  $('ed-ukryj').onclick = () => { if (ukryte(wyb.k)) wyslij('pokaz'); else if (confirm('Usunąć to miejsce z mapy na stronie? Można je potem przywrócić.')) wyslij('ukryj'); };
  $('ed-cofnij').onclick = () => { if (confirm('Przywrócić oryginalne położenie i opis?')) wyslij('cofnij'); };
  $('szukaj').oninput = e => {
    const q = e.target.value.trim().toLowerCase(); if (q.length < 2) { $('wyniki').innerHTML = ''; return; }
    const w = P.filter(m => { const z = biez(m); return (z.nazwa || '').toLowerCase().includes(q) || (MIEJSCA.TYP[z.typ]?.n || '').toLowerCase().includes(q); }).slice(0, 25);
    $('wyniki').innerHTML = w.map((m, i) => { const z = biez(m), t = MIEJSCA.TYP[z.typ]?.n || '';
      return `<a data-i="${i}">${E(z.nazwa || t)} <span class="m">· ${z.nazwa ? E(t) + ' · ' : ''}${E(ZR(m.k))} · ${z.lat.toFixed(4)}, ${z.lon.toFixed(4)}</span></a>`; }).join('') || '<div class="m">Nic nie znaleziono.</div>';
    $('wyniki').querySelectorAll('a').forEach(a => a.onclick = () => { $('wyniki').innerHTML = ''; wybierz(w[+a.dataset.i], true); });
  };
  fetch('../api/miejsca.php', {cache: 'no-store'}).then(r => r.json()).then(j => { P = P.concat((j.miejsca || []).map(m => ({...m}))); rysuj(); }).catch(() => rysuj());
  rysuj(); map.setView([50.617, 18.895], 14);
})();
<?php endif ?>
</script>
</body></html>
