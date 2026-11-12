<?php
// Panel administratora: zatwierdzanie zgłoszeń stanu dróg. Hasło: 'admin_haslo' w /var/www/<witryna>/hub_config.php
require dirname(__DIR__) . '/api/_db.php';
header('X-Frame-Options: DENY');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');
session_set_cookie_params(['httponly' => true, 'samesite' => 'Strict', 'secure' => !empty($_SERVER['HTTPS']), 'path' => '/admin/']);
session_name('hub_admin');
session_start();

$cfg = hub_cfg();
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

$db = hub_db();

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
        $u = $db->prepare('UPDATE zgloszenia SET moderacja = ?, moderowano = ? WHERE id = ?');
        foreach ($ids as $i) $u->execute([$nowy, hub_teraz(), $i]);
    }
    header('Location: ./?k=' . urlencode($_POST['k'] ?? 'oczekuje')); exit;
}

$k = in_array($_GET['k'] ?? '', ['oczekuje', 'zatwierdzone', 'odrzucone', 'wycofane'], true) ? $_GET['k'] : 'oczekuje';
$licz = [];
foreach ($db->query('SELECT moderacja, COUNT(*) n FROM zgloszenia GROUP BY moderacja') as $r) $licz[$r['moderacja']] = (int)$r['n'];
$q = $db->prepare('SELECT * FROM zgloszenia WHERE moderacja = ? ORDER BY utworzono ' . ($k === 'oczekuje' ? 'ASC' : 'DESC') . ' LIMIT 200');
$q->execute([$k]); $lista = $q->fetchAll();
$odc = [];
if ($lista) {
    $in = implode(',', array_map(fn($r) => (int)$r['id'], $lista));
    foreach ($db->query("SELECT zgloszenie, odcinek FROM zgloszenia_odcinki WHERE zgloszenie IN ($in)") as $r) $odc[$r['zgloszenie']][] = $r['odcinek'];
}
$NAZWY = ['dobra' => 'dobra', 'srednia' => 'średnia', 'trudna' => 'trudna', 'nieprzejezdna' => 'nieprzejezdna'];
$AKCJE = ['oczekuje' => [['zatwierdz', 'Zatwierdź', 'ok'], ['odrzuc', 'Odrzuć', 'no']],
          'zatwierdzone' => [['wycofaj', 'Wycofaj z mapy', 'no']],
          'odrzucone' => [['przywroc', 'Przywróć do oczekujących', '']],
          'wycofane' => [['przywroc', 'Przywróć do oczekujących', '']]];
$csrf = $h($_SESSION['csrf']);
?><!doctype html>
<html lang="pl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panel – stan dróg</title>
<link rel="stylesheet" href="../lib/leaflet.css">
<style>
:root{--bg:#f7f4ec;--card:#fffdf8;--ink:#1d2a23;--muted:#56665c;--line:#e3dccb;--green:#1d3b30}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,Inter,sans-serif}
header{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--line);background:var(--card)}
header h1{font-size:18px;margin:0}header a{color:var(--green)}
.tabs{display:flex;gap:6px;flex-wrap:wrap}.tabs a{padding:5px 10px;border-radius:8px;text-decoration:none;border:1px solid var(--line);color:var(--ink)}
.tabs a.on{background:var(--green);color:#fff;border-color:var(--green)}
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
</style></head><body>
<header>
  <h1>Stan dróg – zgłoszenia</h1>
  <nav class="tabs">
    <?php foreach (['oczekuje' => 'Oczekujące', 'zatwierdzone' => 'Zatwierdzone', 'odrzucone' => 'Odrzucone', 'wycofane' => 'Wycofane'] as $kk => $t): ?>
      <a href="?k=<?= $kk ?>" class="<?= $k === $kk ? 'on' : '' ?>"><?= $t ?> (<?= $licz[$kk] ?? 0 ?>)</a>
    <?php endforeach ?>
  </nav>
  <span style="margin-left:auto"><a href="../stan.html" target="_blank">mapa publiczna</a> · <a href="?kopia=1">pobierz kopię (JSON)</a> · <a href="?wyloguj=1">wyloguj</a></span>
</header>
<main>
  <div class="list">
    <?php if (!$lista): ?><div class="empty">Brak zgłoszeń w tej zakładce.</div><?php endif ?>
    <?php foreach ($lista as $r): $n = count($odc[$r['id']] ?? []); ?>
      <div class="z" data-id="<?= (int)$r['id'] ?>" data-stan="<?= $h($r['stan']) ?>">
        <div><span class="chip c-<?= $h($r['stan']) ?>"><?= $h($NAZWY[$r['stan']] ?? $r['stan']) ?></span>
          <b><?= $h($r['nick']) ?></b> · <?= $n ?> odc.</div>
        <div class="m">#<?= (int)$r['id'] ?> · zgłoszono <?= $h($r['utworzono']) ?><?= $r['data_przejazdu'] ? ' · przejazd ' . $h($r['data_przejazdu']) : '' ?><?= $r['moderowano'] ? ' · decyzja ' . $h($r['moderowano']) : '' ?></div>
        <?php if ($r['komentarz'] !== '' && $r['komentarz'] !== null): ?><p><?= $h($r['komentarz']) ?></p><?php endif ?>
        <?php if ($r['kontakt'] !== ''): ?><div class="priv">kontakt (tylko dla Ciebie): <?= $h($r['kontakt']) ?></div><?php endif ?>
        <form class="a" method="post"><input type="hidden" name="csrf" value="<?= $csrf ?>"><input type="hidden" name="k" value="<?= $k ?>">
          <input type="hidden" name="id[]" value="<?= (int)$r['id'] ?>">
          <?php foreach ($AKCJE[$k] as [$a, $t, $cl]): ?><button name="akcja" value="<?= $a ?>" class="<?= $cl ?>"><?= $t ?></button><?php endforeach ?>
        </form>
      </div>
    <?php endforeach ?>
  </div>
  <div id="map"></div>
</main>
<script src="../lib/leaflet.js"></script>
<script src="../stan/odcinki.js"></script>
<script>
const ODC_Z = <?= json_encode($odc, JSON_UNESCAPED_UNICODE) ?>;
const KOL = {dobra:'#2b9348', srednia:'#e0a800', trudna:'#d62828', nieprzejezdna:'#111'};
const map = L.map('map', {preferCanvas:true});
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom:19, attribution:'© OpenStreetMap'}).addTo(map);
const geo = {}; const all = [];
for (const s of window.ODC) { const c = s[7], ll = []; for (let i = 0; i < c.length; i += 2) ll.push([c[i], c[i+1]]); geo[s[0]] = ll; }
const tlo = L.layerGroup().addTo(map);
for (const id in geo) L.polyline(geo[id], {color:'#8a9399', weight:2, opacity:.45, interactive:false}).addTo(tlo);
const sel = L.layerGroup().addTo(map);
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
  pokaz(el.dataset.id, el.dataset.stan, true);
}));
const pierwszy = document.querySelector('.z');
map.setView([50.62, 18.88], 12);
if (pierwszy) pierwszy.click();
</script>
</body></html>
