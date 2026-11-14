// „Jedź” – nawigacja rowerowa HUB Strzebiń (beta).
// Trasa liczona w telefonie po drogach z mapy wspólnej (stan/odcinki.js). Prowadzenie kierunkami z drogowskazów:
// przy każdym słupku na trasie apka pokazuje tabliczkę, za której kierunkiem jechać (tak, jak widzi ją rowerzysta),
// poza słupkami – skręty z nazwami ulic.
// Ten plik: interfejs (wyszukiwanie celu, mapa, podgląd trasy, jazda, głos). Logika w lib/jedz/*.js.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {H, ODC, $, rad, RZ, dist, brg, kat, esc, kmTxt, czasTxt, godz, norm, LS, TRASY, ROWER, P, DW, koszt, najblizszy, trasuj, wDal, stOdc, ROWERY, ST, KOLST, NAZST, profil, czasDo, wykresSVG, strzalkaSVG, kierunek, kierTxt, manewry, mTekst, tabSVG} = JZ;
  // aplikacja na Androida (Capacitor): GPS z usługą w tle (jazda na zgaszonym ekranie) i głos z syntezatora telefonu
  const CAP = window.Capacitor;
  const NAT = !!(CAP && CAP.isNativePlatform && CAP.isNativePlatform());
  // BAZA musi być przed wszystkim, co z niej korzysta (zgłoszenia w aplikacji)
  const BAZA = NAT ? 'https://rowerowy-strzebin.smart-ant.pl/' : './';
  const wtyczka = n => { try { return (CAP.Plugins && CAP.Plugins[n]) || (window.capacitorExports && window.capacitorExports.registerPlugin(n)) || (CAP.registerPlugin && CAP.registerPlugin(n)) || null; } catch (e) { return null; } };
  const PL = NAT ? {BackgroundGeolocation: wtyczka('BackgroundGeolocation'), TextToSpeech: wtyczka('TextToSpeech'), LocalNotifications: wtyczka('LocalNotifications')} : {};
  const diag = {};
  const pokazDiag = () => { if (!NAT) return; const el = document.querySelector('#s-cel .stopka'); if (!el) return; let d = document.getElementById('diag'); if (!d) { d = document.createElement('div'); d.id = 'diag'; d.style.cssText = 'margin-top:6px;font-size:11px;opacity:.7'; el.appendChild(d); }
    d.textContent = 'Aplikacja · GPS w tle: ' + (PL.BackgroundGeolocation ? (diag.bg || 'gotowy') : 'brak') + ' · głos: ' + (PL.TextToSpeech ? 'tak' : 'brak') + ' · powiadomienia: ' + (PL.LocalNotifications ? 'tak' : 'brak'); };
  setTimeout(pokazDiag, 500);
  // zgłoszenia błędów i sugestii (lib/uwagi.js) – w aplikacji pod pełny adres strony
  if (NAT) { window.UWAGI_API = BAZA + 'api/uwagi.php'; window.UWAGI_BAZA = BAZA; }
  const zglos = zTrasa => window.UWAGI && UWAGI.otworz({gdzie: NAT ? 'aplikacja' : 'nawigacja', wersja: NAT ? 'aplikacja Android' : 'Jedź w przeglądarce',
    trasa: zTrasa && stan.T ? {start: stan.T.ll[0], cel: stan.T.ll[stan.T.ll.length - 1], celN: stan.celN, tryb: stan.tryb, rower: ST.RT, km: stan.T.m / 1000} : null});
  if ($('b-uwagi')) $('b-uwagi').onclick = e => { e.preventDefault(); zglos(false); };
  // mapa offline: informacja i przełącznik „zawsze offline” (oszczędza internet; w lesie bez zasięgu przełącza się sama)
  setTimeout(() => {
    const el = document.querySelector('#s-cel .stopka'); if (!el || !JZ.podklad) return;
    const d = document.createElement('div'); d.className = 'moff-w'; el.prepend(d); mapaOfflinePanel();
  }, 0);
  // ===================== wyszukiwanie celu =====================
  const CELE = (H.cele || []).map(c => ({n: c.n, s: c.cat === 'blue' ? 'Miejscowość' : 'Cel z drogowskazów', lat: c.lat, lon: c.lon, typ: 'm'}));
  const MIEJSCOWOSCI = (H.cele || []).filter(c => c.cat === 'blue');
  const najblizszaMiejscowosc = p => { let b = null, bd = Infinity; for (const c of MIEJSCOWOSCI) { const d = dist(p, [c.lat, c.lon]); if (d < bd) { bd = d; b = c.n; } } return b; };
  const ULICE = (() => {
    const m = new Map();
    for (const s of ODC) {
      if (!s[2] || /^\d+$/.test(s[2]) || /pożarowy/i.test(s[2]) || !['ulica', 'droga powiatowa/gminna', 'droga lokalna', 'droga dojazdowa', 'droga wojewódzka'].includes(s[1])) continue;
      const c = s[7], mid = [c[Math.floor(c.length / 4) * 2], c[Math.floor(c.length / 4) * 2 + 1]], miej = najblizszaMiejscowosc(mid), k = s[2] + '|' + miej;
      const e = m.get(k); if (!e || s[6] > e.len) m.set(k, {n: 'ul. ' + s[2], s: 'Ulica · ' + miej, lat: mid[0], lon: mid[1], len: s[6], typ: 'u'});
    }
    return [...m.values()];
  })();
  const TYPM = {stacja: 'Stacja napraw rowerów', serwis: 'Serwis rowerowy', wiata: 'Wiata', lawka: 'Ławka', piknik: 'Piknik / ognisko', widok: 'Punkt widokowy', woda: 'Woda', jedzenie: 'Jedzenie', kawa: 'Kawiarnia', bar: 'Bar', nocleg: 'Nocleg', kosciol: 'Kościół / kapliczka', zabytek: 'Zabytek', przyroda: 'Przyroda', sport: 'Sport', zabawa: 'Plac zabaw', wc: 'WC', parking: 'Parking', ciekawe: 'Ciekawe miejsce'};
  const MIEJSCA = (H.places || []).filter(p => p.nazwa && p.typ !== 'lawka').map(p => ({n: p.nazwa, s: (TYPM[p.typ] || 'Miejsce') + (najblizszaMiejscowosc([p.lat, p.lon]) ? ' · ' + najblizszaMiejscowosc([p.lat, p.lon]) : ''), lat: p.lat, lon: p.lon, typ: 'p'}));
  const WSZYSTKO = [...CELE, ...MIEJSCA, ...ULICE].map(x => ({...x, q: norm(x.n + ' ' + x.s)}));
  function szukaj(q) {
    q = norm(q.trim()); if (q.length < 2) return [];
    const sl = q.split(/\s+/);
    return WSZYSTKO.map(x => {
      if (!sl.every(w => x.q.includes(w))) return null;
      const n = norm(x.n).replace(/^ul\. /, ''); let sc = n.startsWith(q) ? 0 : n.includes(' ' + q) ? 1 : 2;
      sc += {m: 0, p: .3, u: .6}[x.typ];
      return [sc, x];
    }).filter(Boolean).sort((a, b) => a[0] - b[0] || a[1].n.length - b[1].n.length).slice(0, 12).map(a => a[1]);
  }
  const IKW = {m: ['#e7eef8', '#0759A7', 'M3 21h18M5 21V10l7-5 7 5v11M10 21v-6h4v6'], u: ['#dfe9e4', '#1d3b30', 'M4 20 10 4M20 20 14 4M12 6v2M12 11v2M12 16v2'], p: ['#f3e9dc', '#81552F', 'M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12zM12 11.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5'], g: ['#e5e7eb', '#1d2a23', 'M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z']};
  function pokazWyniki(lista) {
    const el = $('wyniki');
    el.classList.toggle('hide', !lista.length); $('szybkie').classList.toggle('hide', !!lista.length);
    el.innerHTML = lista.map((x, i) => { const [bg, kol, d] = IKW[x.typ] || IKW.g;
      return `<button type="button" role="option" data-i="${i}"><span class="ik" style="background:${bg}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${kol}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg></span><span><span class="t">${esc(x.n)}</span><br><span class="s">${esc(x.s)}</span></span></button>`; }).join('');
    el.querySelectorAll('button').forEach(b => b.onclick = () => { const x = lista[+b.dataset.i]; ustawCel([x.lat, x.lon], x.n, x.s); });
  }
  $('szukaj').addEventListener('input', e => pokazWyniki(szukaj(e.target.value)));
  $('szukaj').addEventListener('keydown', e => { if (e.key === 'Enter') { const w = szukaj(e.target.value); if (w[0]) ustawCel([w[0].lat, w[0].lon], w[0].n, w[0].s); } });
  const SZYBKIE = [['Strzebiń', ''], ['Bukowiec', ''], ['Koszęcin', ''], ['Kalety', ''], ['Boronów', ''], ['Leśno Rajza', 'g'], ['Stacja napraw', 's']];
  $('chipy').innerHTML = SZYBKIE.map(([n, c]) => `<button type="button" class="${c}">${n}</button>`).join('');
  $('chipy').querySelectorAll('button').forEach(b => b.onclick = () => {
    const n = b.textContent;
    if (n === 'Stacja napraw') { const s = (H.places || []).filter(p => p.typ === 'stacja'); const ja = stan.start || [50.616, 18.897]; s.sort((a, c) => dist(ja, [a.lat, a.lon]) - dist(ja, [c.lat, c.lon])); if (s[0]) ustawCel([s[0].lat, s[0].lon], 'Stacja napraw rowerów', s[0].opis || ''); return; }
    if (n === 'Leśno Rajza') { const best = najblizszyPunktTrasy('7'); if (best) ustawCel(best, 'Leśno Rajza', 'najbliższy punkt szlaku'); return; }
    const c = (H.cele || []).find(c => c.n === n); if (c) ustawCel([c.lat, c.lon], c.n, 'Miejscowość');
  });
  function najblizszyPunktTrasy(id) {
    const r = H.routes.find(r => String(r.id) === id); if (!r) return null;
    const ja = stan.start || [50.616, 18.897]; let b = null, bd = Infinity;
    for (const pt of r.parts.flatMap(p => p.c)) { const d = dist(ja, pt); if (d < bd) { bd = d; b = pt; } }
    return b;
  }

  // ===================== stan i mapa =====================
  const stan = {start: null, startN: 'Twoja lokalizacja', startGPS: true, cel: null, celN: '', celS: '', tryb: ['krotko', 'szosa'].includes(LS.get('tryb', 'bezp')) ? LS.get('tryb', 'bezp') : 'bezp',
                T: null, M: [], wybor: null, jazda: false, glos: LS.get('glos', true)};
  JZ.stan = stan;
  let map = null, warstwa = null, jaM = null, celM = null, sledz = true;
  let mapaOffline = LS.get('mapaOffline', false) && LS.get('mapaPobrana', false), mapaUstaw = null;
  // mapa offline na życzenie: przycisk „Pobierz” (2,8 MB), po pobraniu – „używaj zawsze” i „usuń”
  function mapaOfflinePanel() {
    const box = document.querySelector('.moff-w'); if (!box) return;
    if (!JZ.podklad.pobrana()) {
      box.innerHTML = `<div class="moff"><span><b>Mapa offline</b> – lasy, wody, budynki i nazwy także bez zasięgu. <button type="button" class="moff-b" id="moff-p">Pobierz mapę offline (2,8 MB)</button></span></div>`;
      $('moff-p').onclick = () => { $('moff-p').disabled = true; $('moff-p').textContent = 'Pobieram…';
        JZ.podklad.pobierz(() => { mapaOfflinePanel(); podpowiedzOffline(); }, () => { const b = $('moff-p'); if (b) { b.disabled = false; b.textContent = 'Nie udało się – spróbuj ponownie'; } }); };
    } else {
      box.innerHTML = `<label class="moff"><input type="checkbox" id="moff"${mapaOffline ? ' checked' : ''}> <span><b>Mapa offline pobrana ✓</b> – włącza się sama bez zasięgu. Zaznacz, żeby używać jej zawsze (bez pobierania mapy z internetu). <a href="#" id="moff-u">Usuń</a></span></label>`;
      $('moff').onchange = e => { mapaOffline = e.target.checked; LS.set('mapaOffline', mapaOffline); if (mapaUstaw) mapaUstaw(mapaOffline); };
      $('moff-u').onclick = e => { e.preventDefault(); JZ.podklad.usun(); mapaOffline = false; LS.set('mapaOffline', false); if (mapaUstaw) mapaUstaw(false); mapaOfflinePanel(); };
    }
  }
  // podpowiedź w podglądzie trasy, gdy mapa offline nie jest pobrana
  function podpowiedzOffline() { const p = $('p-offline'); if (p) p.hidden = JZ.podklad.pobrana(); }
  function mapa() {
    if (map) return map;
    map = L.map('mapa', {zoomControl: false, attributionControl: false, preferCanvas: true}).setView([50.615, 18.9], 13);
    // mapa offline (lib/jedz/podklad.js) zawsze pod spodem; kafelki OSM na wierzchu, chyba że wybrano „zawsze offline”.
    // Bez zasięgu kafelki się nie wczytają (zostają niewidoczne) i widać podkład offline – wtedy dokładamy też nazwy miejscowości.
    map.createPane('nazwy').style.zIndex = 390;
    JZ.podklad.warstwa(L).addTo(map);
    const nazwy = JZ.podklad.nazwy(L, map);
    let bledyK = 0, ostOk = 0;
    const kafelki = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '© OpenStreetMap'})
      .on('tileerror', () => { if (++bledyK >= 3 && Date.now() - ostOk > 4000) nazwy.addTo(map); })
      .on('tileload', () => { ostOk = Date.now(); bledyK = 0; if (!mapaOffline) nazwy.remove(); });
    mapaUstaw = off => { mapaOffline = off; if (off) { kafelki.remove(); nazwy.addTo(map); } else { kafelki.addTo(map); nazwy.remove(); } };
    mapaUstaw(mapaOffline);
    warstwa = L.layerGroup().addTo(map);
    map.on('dragstart', () => { if (stan.jazda) { sledz = false; $('b-srodek').classList.remove('hide'); } });
    // obrót „zablokowany” kompasem: mapy nie da się przesunąć, ale da się ją przybliżać/oddalać (wokół Twojej pozycji);
    // odblokowanie – tylko przyciskiem kompasu
    window.addEventListener('resize', () => { if (obrocona) obroc(true); });
    map.on('click', e => { if (stan.wybor) stan.wybor([e.latlng.lat, e.latlng.lng]); });
    return map;
  }
  function ekran(id) { document.querySelectorAll('.ekran').forEach(e => e.classList.toggle('on', e.id === id)); if (id === 's-mapa' && map) { map.invalidateSize({pan: false}); setTimeout(() => map && map.invalidateSize({pan: false}), 60); } }
  $('wstecz').onclick = () => { if (stan.jazda) return; stan.wybor = null; ekran('s-cel'); };

  // --- start: GPS albo punkt na mapie
  // GEO.sledz(cb, blad) → funkcja zatrzymująca; w aplikacji przez usługę w tle (powiadomienie „nawigacja aktywna”)
  const GEO = {
    sledz(cb, blad, opis, stara) {
      if (NAT && PL.BackgroundGeolocation) {
        let id = null, stop = false;
        // Android 13+: bez zgody na powiadomienia usługa nie pokaże „nawigacja aktywna”
        const zgodaPow = !stara && PL.LocalNotifications ? PL.LocalNotifications.requestPermissions().catch(() => {}) : Promise.resolve();
        zgodaPow.then(() => stop ? null : PL.BackgroundGeolocation.addWatcher({backgroundTitle: 'Jedź – nawigacja aktywna', backgroundMessage: opis || 'Prowadzimy Cię trasą rowerową', requestPermissions: true, stale: !!stara, distanceFilter: 0},
          (loc, err) => { if (err) { if (err.code === 'NOT_AUTHORIZED') blad('zgoda'); else blad(); return; } if (loc) cb([loc.latitude, loc.longitude], loc.accuracy, loc.bearing); })
          .then(w => { id = w; if (stop) PL.BackgroundGeolocation.removeWatcher({id}); }))
          .catch(e => { diag.bg = 'błąd: ' + (e && e.message || e); pokazDiag(); });
        // równolegle lokalizacja z WebView (GPS + Wi-Fi + sieć – lepsza przy słabym GPS, działa przy włączonym ekranie)
        let w2 = null;
        if (!stara && navigator.geolocation) w2 = navigator.geolocation.watchPosition(e => cb([e.coords.latitude, e.coords.longitude], e.coords.accuracy, e.coords.heading), () => {}, {enableHighAccuracy: true, maximumAge: 1000, timeout: 20000});
        return () => { stop = true; if (id != null) PL.BackgroundGeolocation.removeWatcher({id}); if (w2 != null) navigator.geolocation.clearWatch(w2); };
      }
      if (!navigator.geolocation) { blad('brak'); return () => {}; }
      const w = navigator.geolocation.watchPosition(e => cb([e.coords.latitude, e.coords.longitude], e.coords.accuracy, e.coords.heading), e => blad(e.code === 1 ? 'zgoda' : ''), {enableHighAccuracy: true, maximumAge: 1000, timeout: 20000});
      return () => navigator.geolocation.clearWatch(w);
    }
  };
  function gps(ok, zle) {
    if (NAT) {
      // pierwsza pozycja: wystarczy ostatnia znana (stale) – w domu świeży GPS potrafi nie przyjść wcale; limit 15 s
      let gotowe = false, stop = () => {};
      const koniec = (p, e) => { if (gotowe) return; gotowe = true; clearTimeout(t); stop(); if (p) ok(p); else zle(e); };
      const t = setTimeout(() => koniec(null, 'Nie udało się ustalić lokalizacji (słaby sygnał GPS) – wskaż start na mapie albo spróbuj na zewnątrz.'), 15000);
      const wtyczka = () => { if (gotowe) return; stop = GEO.sledz(p => koniec(p), e => koniec(null, e === 'zgoda' ? 'Brak zgody na lokalizację – zezwól w ustawieniach telefonu albo wskaż start na mapie.' : 'Nie udało się ustalić lokalizacji.'), 'Ustalam Twoją lokalizację', true); if (gotowe) stop(); };
      if (navigator.geolocation) navigator.geolocation.getCurrentPosition(p => koniec([p.coords.latitude, p.coords.longitude]), wtyczka, {enableHighAccuracy: true, timeout: 8000, maximumAge: 30000});
      else wtyczka();
      return;
    }
    if (!navigator.geolocation) return zle('Ten telefon nie udostępnia lokalizacji.');
    navigator.geolocation.getCurrentPosition(p => ok([p.coords.latitude, p.coords.longitude]), e => zle(e.code === 1 ? 'Brak zgody na lokalizację – zezwól w ustawieniach przeglądarki albo wskaż start na mapie.' : 'Nie udało się ustalić lokalizacji.'), {enableHighAccuracy: true, timeout: 15000, maximumAge: 10000});
  }
  function opiszStart() { $('skad-t').textContent = stan.startGPS ? 'Twoja lokalizacja' + (stan.start ? ' · ' + (najblizszaMiejscowosc(stan.start) || '') : '') : stan.startN; }
  gps(p => { stan.start = p; opiszStart(); }, () => {});
  $('skad-zmien').onclick = () => wybierzNaMapie('Stuknij w mapę, skąd startujesz', p => { stan.start = p; stan.startGPS = false; stan.startN = 'Punkt na mapie · ' + (najblizszaMiejscowosc(p) || ''); opiszStart(); ekran('s-cel'); }, true);
  $('cel-mapa').onclick = () => wybierzNaMapie('Stuknij w mapę, dokąd jedziesz', p => ustawCel(p, 'Punkt na mapie', najblizszaMiejscowosc(p) || ''));
  function wybierzNaMapie(tytul, cb, start) {
    ekran('s-mapa'); mapa(); warstwa.clearLayers(); panele('wybor');   // najpierw pokaż ekran – mapa tworzona na widocznym kontenerze
    $('gora').innerHTML = `<div class="pasek" style="padding-left:70px"><div class="co">${esc(tytul)}</div><div class="lab">Działa na obszarze mapy HUB (Koszęcin i okolice)</div></div>`;
    $('dol').innerHTML = start ? `<button type="button" class="btn2" id="b-gps">${strzalkaSVG('prosto', '#1d2a23', 18)}Użyj mojej lokalizacji (GPS)</button><p class="msg" id="msg-w"></p>` : '<p class="msg" id="msg-w"></p>';
    if (start) $('b-gps').onclick = () => gps(p => { stan.start = p; stan.startGPS = true; opiszStart(); stan.wybor = null; ekran('s-cel'); }, e => { $('msg-w').textContent = e; });
    map.setView(stan.cel || stan.start || [50.615, 18.9], 13);
    stan.wybor = p => { if (najblizszy(p)[1] > 600) { $('msg-w').textContent = 'Za daleko od dróg z mapy HUB – wybierz punkt bliżej Koszęcina i okolic.'; $('msg-w').className = 'msg err'; return; } stan.wybor = null; cb(p); };
  }
  function ustawCel(p, n, s) {
    stan.cel = p; stan.celN = n; stan.celS = s || ''; $('szukaj').value = ''; pokazWyniki([]);
    if (!stan.start) {
      $('msg-cel').textContent = 'Ustalam Twoją lokalizację…'; $('msg-cel').className = 'msg';
      gps(q => { stan.start = q; stan.startGPS = true; opiszStart(); $('msg-cel').textContent = ''; podglad(); },
          e => { $('msg-cel').textContent = e; $('msg-cel').className = 'msg err'; wybierzNaMapie('Nie mamy Twojej lokalizacji – stuknij w mapę, skąd startujesz', q => { stan.start = q; stan.startGPS = false; stan.startN = 'Punkt na mapie'; opiszStart(); podglad(); }, true); });
      return;
    }
    podglad();
  }

  // --- rysowanie trasy
  function rysuj(T, M) {
    warstwa.clearLayers();
    L.polyline(T.ll, {color: '#fff', weight: 10, opacity: .95, interactive: false}).addTo(warstwa);
    L.polyline(T.ll, {color: '#0f766e', weight: 6, opacity: .95, interactive: false}).addTo(warstwa);
    for (const m of M) if (m.typ === 'tab') L.marker(wDal(T, m.c), {interactive: false, icon: L.divIcon({className: '', html: '<div class="km-m"></div>', iconSize: [22, 22], iconAnchor: [11, 11]})}).addTo(warstwa);
    L.circleMarker(T.ll[0], {radius: 8, color: '#fff', weight: 3, fillColor: '#1d4ed8', fillOpacity: 1, interactive: false}).addTo(warstwa);
    L.marker(T.ll[T.ll.length - 1], {interactive: false, icon: L.divIcon({className: '', html: '<div class="cel-m"><svg width="11" height="13" viewBox="0 0 14 18"><path d="M2 17V1l10 4-10 4" fill="none" stroke="#fff" stroke-width="2.6" stroke-linejoin="round"/></svg></div>', iconSize: [26, 26], iconAnchor: [13, 13]})}).addTo(warstwa);
  }
  const atryb = () => setTimeout(() => { const d = $('dol'); $('atryb').style.bottom = (d && d.offsetHeight ? d.offsetHeight + 4 : 4) + 'px'; }, 50);
  function panele(tryb) {
    atryb();
    $('wstecz').classList.toggle('hide', tryb === 'jazda');
    $('b-glos').classList.toggle('hide', tryb !== 'jazda'); $('b-srodek').classList.add('hide');
    $('status').classList.toggle('hide', tryb !== 'jazda'); $('b-sym').classList.toggle('hide', !(tryb === 'jazda' && sym));
  }

  // ===================== 2. podgląd trasy =====================
  function policz() {
    const opc = {tryb: stan.tryb};
    const T = trasuj(stan.start, stan.cel, opc);
    if (T.blad) return T;
    T.km = {dw: 0, trasy: 0}; for (let i = 0; i < T.seg.length; i++) { const s = T.seg[i]; if (!s) continue; const d = T.cum[i + 1] - T.cum[i]; if (DW(s) && !ROWER.has(s[0])) T.km.dw += d; if (TRASY.has(s[0])) T.km.trasy += d; }
    T.prof = profil(T);
    return T;
  }
  // ile metrów trasy po drogach nieutwardzonych / bez oceny / trudnych (do ostrzeżeń dla roweru)
  function nieutw(T) {
    const o = {nu: 0, tr: 0}; if (!T || T.blad) return o;
    for (let i = 0; i < T.seg.length; i++) { const st = stOdc(T.seg[i]); if (!st) continue; const d = T.cum[i + 1] - T.cum[i];
      if (st === 'srednia' || st === 'trudna' || st === 'brak') o.nu += d; if (st === 'trudna') o.tr += d; }
    return o;
  }
  const TRYBY = {bezp: 'Bezpieczna', krotko: 'Najkrótsza', szosa: 'Szosowa'};
  function ostrzezenie(T, inne) {
    const a = nieutw(T); let alt = null;
    for (const [k, X] of Object.entries(inne || {})) { const b = nieutw(X); if (X && !X.blad && b.nu < a.nu - 200 && (!alt || b.nu < alt.nu)) alt = {k, nu: b.nu}; }
    const lepiej = alt ? ` Trasa „${TRYBY[alt.k]}” ma ich mniej (${kmTxt(alt.nu)}).` : '';
    if (ST.RT === 'szosa' && a.nu > 300) return `⚠ Szosówką może być ciężko: ${kmTxt(a.nu)} trasy to drogi nieutwardzone, leśne albo bez oceny.${lepiej}`;
    if (ST.RT !== 'gorski' && ST.RT !== 'gravel' && a.tr > 200) return `⚠ Na trasie ${kmTxt(a.tr)} dróg ocenionych jako trudne (piach, korzenie, dziury).${lepiej}`;
    return '';
  }
  const tempoNazwa = v => v < 13 ? 'spacerowo' : v < 20 ? 'rekreacyjnie' : v < 27 ? 'sportowo' : 'wyczynowo';
  function tempoSuwak(T) {
    const r = $('p-tempo'); if (!r) return;
    r.oninput = () => {
      ST.VU = +r.value; LS.set('vplaska', ST.VU); T.prof = profil(T);
      $('p-v').textContent = ST.VU + ' km/h · ' + tempoNazwa(ST.VU); $('p-czas').textContent = czasTxt(T.prof.czas);
      clearTimeout(tempoSuwak.t); tempoSuwak.t = setTimeout(() => wykresInterakcja(T), 150);   // podpowiedzi wykresu z nowym czasem
    };
  }
  function wykresBlok(T) {
    const P = T.prof, ile = {};
    for (let i = 1; i < P.d.length; i++) ile[P.st[i]] = (ile[P.st[i]] || 0) + P.d[i] - P.d[i - 1];
    const leg = ['osm', 'dobra', 'srednia', 'trudna', 'brak', 'nieprzejezdna'].filter(k => ile[k] > 30)
      .map(k => `<span><i style="background:${KOLST[k]}"></i>${NAZST[k]} ${kmTxt(ile[k])}</span>`).join('');
    return `<div class="wykres"><div class="wnag"><span class="sek">Profil i nawierzchnia</span>${P.wys ? `<span class="wg">↑ ${Math.round(P.up)} m · ↓ ${Math.round(P.down)} m</span>` : ''}</div>
      <div id="wyk">${wykresSVG(P)}</div><div class="wpod" id="wpod">${P.wys ? 'Przesuń palcem po wykresie, żeby zobaczyć miejsce na mapie.' : 'Brak danych o wysokości – pokazujemy samą nawierzchnię.'}</div>
      <div class="leg">${leg}</div></div>`;
  }
  let kursorM = null;
  function wykresInterakcja(T) {
    const box = $('wyk'); if (!box) return; box.innerHTML = wykresSVG(T.prof, Math.max(200, Math.round(box.clientWidth))); const svg = box.querySelector('svg'), kur = svg.querySelector('.kursor'), P = T.prof, M = P.d[P.d.length - 1];
    const pokaz = e => {
      const r = svg.getBoundingClientRect(), x = Math.max(0, Math.min(1, ((e.touches ? e.touches[0].clientX : e.clientX) - r.left) / r.width)), w = x * M;
      let i = 0; while (i < P.d.length - 1 && P.d[i + 1] < w) i++;
      const vb = svg.viewBox.baseVal.width; kur.setAttribute('x1', x * vb); kur.setAttribute('x2', x * vb); kur.style.display = '';
      const p = wDal(T, w);
      if (!kursorM) kursorM = L.circleMarker(p, {radius: 7, color: '#fff', weight: 3, fillColor: '#1d4ed8', fillOpacity: 1, interactive: false}).addTo(map); else kursorM.setLatLng(p);
      $('wpod').textContent = `${kmTxt(w)} od startu${P.wys ? ' · ' + Math.round(P.z[i]) + ' m n.p.m.' : ''} · ${NAZST[P.st[i]]} · ${czasTxt(P.tc[i])}`;
    };
    const ukryj = () => { kur.style.display = 'none'; if (kursorM) { kursorM.remove(); kursorM = null; } };
    svg.addEventListener('pointermove', pokaz); svg.addEventListener('pointerdown', pokaz);
    svg.addEventListener('touchmove', e => { pokaz(e); e.preventDefault(); }, {passive: false});
    svg.addEventListener('pointerleave', ukryj);
  }
  function podglad() {
    if (stan.tryb === 'szosa' && ST.RT !== 'szosa') stan.tryb = 'bezp';
    ekran('s-mapa'); mapa(); panele('podglad'); stan.wybor = null;
    $('gora').innerHTML = '';
    const T = policz();
    if (T.blad) {
      warstwa.clearLayers();
      $('dol').innerHTML = `<div class="uchwyt"></div><p class="msg err">${T.blad === 'start' ? 'Jesteś poza obszarem mapy HUB (Koszęcin i okolice). Zmień start – możesz go wskazać na mapie.' : T.blad === 'cel' ? 'Cel jest poza obszarem mapy HUB.' : 'Nie znalazłem drogi między tymi punktami.'}</p><button type="button" class="btn2" id="b-wroc">Wróć</button>`;
      $('b-wroc').onclick = () => ekran('s-cel'); return;
    }
    stan.T = T; stan.M = manewry(T); rysuj(T, stan.M);
    // porównanie z drugim trybem (do przełącznika)
    // pozostałe tryby (do przełącznika i podpowiedzi w ostrzeżeniu); „Szosowa” tylko przy rowerze szosowym
    const tryby = ST.RT === 'szosa' ? ['bezp', 'krotko', 'szosa'] : ['bezp', 'krotko'];
    const inne = {}; for (const k of tryby) if (k !== stan.tryb) inne[k] = trasuj(stan.start, stan.cel, {tryb: k});
    const km = k => k === stan.tryb ? T.m : inne[k].m;
    const opisT = {bezp: ' · omija DW i DK', krotko: '', szosa: ' · asfalt, główne drogi'};
    const nTab = stan.M.filter(m => m.typ === 'tab').length;
    const lista = stan.M.slice(0, 40).map(m => `<div>${strzalkaSVG(m.k, m.typ === 'tab' ? '#0759A7' : m.typ === 'cel' ? '#1d3b30' : '#1d2a23', 22)}<span>${esc(mTekst(m))}</span><span class="km">${kmTxt(m.c)}</span></div>`).join('');
    $('dol').innerHTML = `<div class="uchwyt"></div>
      <div><div class="msg">${esc(stan.startGPS ? 'Z Twojej lokalizacji' : stan.startN)} →</div><div style="font-size:21px;font-weight:800">${esc(stan.celN)}</div>${stan.celS ? `<div class="msg">${esc(stan.celS)}</div>` : ''}</div>
      <div class="tryb${tryby.length > 2 ? ' t3' : ''}" role="radiogroup" aria-label="Rodzaj trasy">
        ${tryby.map(k => `<button type="button" role="radio" data-t="${k}" aria-checked="${stan.tryb === k}"><b>${TRYBY[k]}</b><span>${kmTxt(km(k))}${opisT[k]}</span></button>`).join('')}
      </div>
      <div class="staty"><div><b>${kmTxt(T.m)}</b><span>długość</span></div><div><b id="p-czas">${czasTxt(T.prof.czas)}</b><span>czasu jazdy</span></div><div><b>${nTab}</b><span>drogowskazów</span></div></div>
      <div class="rower" role="radiogroup" aria-label="Rodzaj roweru">${Object.entries(ROWERY).map(([k, r]) => `<button type="button" role="radio" data-r="${k}" aria-checked="${k === ST.RT}">${r.n}</button>`).join('')}</div>
      <div class="msg ostrz" id="p-ostrz"${ostrzezenie(T, inne) ? '' : ' hidden'}>${esc(ostrzezenie(T, inne))}</div>
      <div class="tempo"><div class="tnag"><span>Twoje tempo na płaskim</span><b id="p-v">${ST.VU} km/h · ${tempoNazwa(ST.VU)}</b></div>
        <input type="range" id="p-tempo" min="8" max="40" step="1" value="${ST.VU}" aria-label="Twoja średnia prędkość na płaskim (km/h)">
        <div class="tskala"><span>spacerowo</span><span>rekreacyjnie</span><span>sportowo</span><span>wyczynowo</span></div></div>
      ${wykresBlok(T)}
      <div class="msg">${T.km.trasy > 100 ? `Trasami HUB: ${kmTxt(T.km.trasy)}. ` : ''}${T.km.dw > 50 ? `Po drogach wojewódzkich i krajowych: ${kmTxt(T.km.dw)}.` : 'Bez dróg wojewódzkich i krajowych.'}</div>
      <button type="button" class="btn" id="b-jedz">${strzalkaSVG('prosto', '#fff', 22)}Jedź</button>
      <div class="rzad"><a class="btn2" id="b-google" target="_blank" rel="noopener" style="text-decoration:none;color:inherit">Mapy Google</a>${NAT ? '' : '<button type="button" class="btn2" id="b-gpx">GPX</button>'}</div>
      <button type="button" class="btn2" id="b-symstart" style="border-style:dashed">Symulacja przejazdu (test w domu)</button>
      <div class="sek">Po drodze</div><div class="manew">${lista}</div>
      <div class="moff p-off" id="p-offline"${JZ.podklad.pobrana() ? ' hidden' : ''}><span>Jedziesz przez las albo tam, gdzie słaby zasięg? <button type="button" class="moff-b" id="p-offline-b">Pobierz mapę offline (2,8 MB)</button></span></div>
      <button type="button" class="btn2" id="b-zglos" style="border-style:dashed">Coś nie tak z tą trasą? Zgłoś błąd / sugestię</button>`;
    $('dol').querySelectorAll('.tryb button').forEach(b => b.onclick = () => { stan.tryb = b.dataset.t; LS.set('tryb', stan.tryb); podglad(); });
    // zmiana roweru: tylko czas jazdy (prędkości na nawierzchniach, podjazdy, vmax) – trasa i suwak tempa bez zmian
    $('dol').querySelectorAll('.rower button').forEach(b => b.onclick = () => {
      const zSzosy = ST.RT === 'szosa'; ST.RT = b.dataset.r; ST.R = ROWERY[ST.RT]; LS.set('rower', ST.RT);
      // szosówka: od razu tryb „Szosowa”; przesiadka z szosówki – z trybu szosowego wracamy do „Bezpieczna”
      if (ST.RT === 'szosa' || (zSzosy && stan.tryb === 'szosa')) { stan.tryb = ST.RT === 'szosa' ? 'szosa' : 'bezp'; LS.set('tryb', stan.tryb); const y = $('dol').scrollTop; podglad(); $('dol').scrollTop = y; return; }
      if (zSzosy) { const y = $('dol').scrollTop; podglad(); $('dol').scrollTop = y; return; }   // znika trzeci przycisk trybu
      T.prof = profil(T);
      $('dol').querySelectorAll('.rower button').forEach(x => x.setAttribute('aria-checked', x === b));
      $('p-czas').textContent = czasTxt(T.prof.czas); wykresInterakcja(T);
      const o = ostrzezenie(T, inne); $('p-ostrz').textContent = o; $('p-ostrz').hidden = !o;
    });
    $('b-jedz').onclick = () => startJazdy(false);
    $('b-zglos').onclick = () => zglos(true);
    $('p-offline-b').onclick = () => { const b = $('p-offline-b'); b.disabled = true; b.textContent = 'Pobieram…';
      JZ.podklad.pobierz(() => { podpowiedzOffline(); mapaOfflinePanel(); }, () => { b.disabled = false; b.textContent = 'Nie udało się – spróbuj ponownie'; }); };
    $('b-symstart').onclick = () => startJazdy(true);
    if ($('b-gpx')) $('b-gpx').onclick = () => gpx(T);
    $('b-google').href = linkGoogle(T);
    if (kursorM) { kursorM.remove(); kursorM = null; } wykresInterakcja(T); tempoSuwak(T);
    atryb();
    // mapa mogła powstać na ukrytym ekranie (rozmiar 0) – najpierw przelicz rozmiar, potem dopasuj widok; drugi raz po ułożeniu panelu
    const dopasuj = () => { if (stan.jazda || stan.T !== T) return; map.invalidateSize({pan: false});
      map.fitBounds(L.polyline(T.ll).getBounds(), {paddingTopLeft: [20, 70], paddingBottomRight: [20, Math.min(($('dol').offsetHeight || window.innerHeight * .55) + 10, window.innerHeight * .7)]}); };
    dopasuj(); setTimeout(dopasuj, 120); setTimeout(dopasuj, 600);
  }
  function linkGoogle(T) {
    const f = p => p[0].toFixed(5) + ',' + p[1].toFixed(5);
    const wp = [.25, .5, .75].map(x => f(wDal(T, T.m * x))).join('|');
    return `https://www.google.com/maps/dir/?api=1&origin=${f(T.ll[0])}&destination=${f(T.ll[T.ll.length - 1])}&waypoints=${encodeURIComponent(wp)}&travelmode=bicycling`;
  }
  function gpx(T) {
    const x = s => String(s).replace(/[<>&"]/g, c => ({'<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;'}[c]));
    const n = 'Do: ' + stan.celN;
    const t = `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="HUB rowerowy Strzebiń – Jedź" xmlns="http://www.topografix.com/GPX/1/1">\n<trk><name>${x(n)}</name><trkseg>\n` + T.ll.map(p => `<trkpt lat="${p[0].toFixed(6)}" lon="${p[1].toFixed(6)}"/>`).join('\n') + '\n</trkseg></trk>\n</gpx>\n';
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([t], {type: 'application/gpx+xml'}));
    a.download = 'trasa_' + norm(stan.celN).replace(/[^\w]+/g, '_').slice(0, 40) + '.gpx'; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  // ===================== 3. jazda =====================
  let watch = null, sym = null, symV = 1, wake = null, poza = 0, ostPrzel = 0, idx = 0, wzdluz = 0, ostPoz = null, zapowiedz = new Set(), kierPokaz = null;
  async function budzik() { try { if ('wakeLock' in navigator) { wake = await navigator.wakeLock.request('screen'); } } catch (e) {} }
  document.addEventListener('visibilitychange', () => { if (stan.jazda && document.visibilityState === 'visible') budzik(); });
  // ---- mapa obrócona „kierunkiem jazdy do góry”: kontener mapy to kwadrat o boku = przekątnej ekranu,
  //      środek kwadratu (= Twoja pozycja) w 62% wysokości ekranu, obrót CSS wokół środka
  let obrocona = false, B = 0, kurs = LS.get('kurs', true), tilt = LS.get('tilt', false);
  // 3D: obrócona mapa dodatkowo pochylona jak kartka na stole (perspektywa CSS); kontener większy, żeby pokryć „dal”
  const tr = () => tilt && obrocona ? `perspective(${Math.round($('s-mapa').clientHeight * 1.1)}px) rotateX(48deg) rotate(${-B}deg)` : `rotate(${-B}deg)`;
  function obroc(on) {
    const el = $('mapa'), box = $('s-mapa'), w = box.clientWidth, h = box.clientHeight;
    obrocona = on;
    map.options.touchZoom = map.options.doubleClickZoom = map.options.scrollWheelZoom = on ? 'center' : true;
    if (on) { const D = Math.ceil(Math.hypot(w, h) * (tilt ? 2.3 : 1)) + 4, ay = Math.round(h * (tilt ? .7 : .62)); el.style.cssText = `inset:auto;left:${Math.round((w - D) / 2)}px;top:${ay - Math.round(D / 2)}px;width:${D}px;height:${D}px;transition:transform .6s linear`; el.style.transform = tr(); map.dragging.disable(); }
    else { el.style.cssText = ''; map.dragging.enable(); }
    map.invalidateSize({pan: false}); if (jaM && sledz) map.setView(jaM.getLatLng(), map.getZoom(), {animate: false});
    kompas();
  }
  function kompas() { $('b-kurs').innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true" style="transform:rotate(${obrocona ? -B : 0}deg);transition:transform .6s linear"><path d="M12 2l4 10h-8z" fill="#d62828"/><path d="M12 22l-4-10h8z" fill="#9aa3a8"/><text x="12" y="9.5" text-anchor="middle" font-size="5" font-weight="800" fill="#fff" font-family="Inter,Arial">N</text></svg>`;
    $('b-kurs').ariaLabel = obrocona ? 'Odblokuj: północ u góry' : 'Zablokuj: kierunek jazdy u góry';
    $('b-kurs').style.background = obrocona ? '#00737e' : '#fff'; $('b-kurs').style.boxShadow = obrocona ? '0 0 0 3px #fff, 0 1px 6px rgba(0,0,0,.3)' : '';
    $('b-kurs').querySelector('svg path:last-of-type').setAttribute('fill', obrocona ? '#cfe6e6' : '#9aa3a8'); }
  function startJazdy(symulacja) {
    stan.jazda = true; idx = 0; wzdluz = 0; poza = 0; Object.assign(tempo, {real: 0, mod: 0, t: 0, v: 0, k: 1}); zapowiedz = new Set(); kierPokaz = null; sledz = true;
    sym = symulacja ? {d: 0} : null; panele('jazda'); glosIkona(); budzik();
    $('dol').innerHTML = `<div class="jdol"><div class="w"><b id="j-zost"></b><small id="j-opis"></small></div><button type="button" class="stop" id="b-stop">Zakończ</button></div>`;
    $('b-stop').onclick = koniecJazdy;
    map.setView(stan.T.ll[0], 17); B = brg(stan.T.ll[0], wDal(stan.T, 40)); if (kurs) obroc(true); else kompas();
    $('b-kurs').classList.remove('hide'); $('b-3d').classList.remove('hide'); trojwymiar();
    if (!sym) pozycja(stan.start, 20, true);
    if (sym) { symV = 1; $('b-sym').textContent = 'Symulacja: ×1'; sym.t = setInterval(() => { sym.d += 6 * symV; const p = wDal(stan.T, sym.d); pozycja(p, 5, sym.d); }, 1000); }
    else watch = GEO.sledz((p, acc) => pozycja(p, acc), () => { $('status').className = 'status zle'; $('status').querySelector('span').textContent = 'Brak sygnału GPS'; }, 'Do: ' + stan.celN);
    odswiez();
  }
  $('b-sym').onclick = () => { symV = symV === 1 ? 3 : symV === 3 ? 8 : 1; $('b-sym').textContent = 'Symulacja: ×' + symV; };
  function koniecJazdy() {
    stan.jazda = false; if (watch) watch(); watch = null;
    if (sym) clearInterval(sym.t); sym = null; try { wake && wake.release(); } catch (e) {} wake = null;
    if (jaM) { jaM.remove(); jaM = null; } if (obrocona) obroc(false); $('b-kurs').classList.add('hide'); $('b-3d').classList.add('hide'); ekran('s-mapa'); window.speechSynthesis && speechSynthesis.cancel(); podglad();
  }
  // rzut pozycji na trasę: szukamy w okolicy ostatniego znanego miejsca (żeby nie „przeskakiwać” na równoległy fragment)
  function rzut(T, p) {
    let best = null;
    const od = Math.max(0, idx - 30), doo = Math.min(T.ll.length - 1, idx + 600);
    for (let i = od; i < doo; i++) {
      const a = T.ll[i], b = T.ll[i + 1], kx = Math.cos(p[0] * rad);
      const ax = (a[1] - p[1]) * kx, ay = a[0] - p[0], bx = (b[1] - p[1]) * kx, by = b[0] - p[0], dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy;
      const t = L2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / L2)) : 0;
      const d = Math.hypot(ax + t * dx, ay + t * dy) * rad * RZ;
      if (!best || d < best.d - 0.5) best = {d, i, w: T.cum[i] + t * (T.cum[i + 1] - T.cum[i])};
    }
    return best;
  }
  function pozycja(p, acc, wSym) {
    const T = stan.T; if (!T || !stan.jazda) return;
    // dwa źródła pozycji (aplikacja): odrzuć wyraźnie gorszy odczyt, jeśli przed chwilą był lepszy
    const teraz = Date.now(); acc = acc || 20;
    if (pozycja.ost && teraz - pozycja.ost.t < 3000 && acc > Math.max(25, pozycja.ost.acc * 2)) return;
    pozycja.ost = {t: teraz, acc};
    const r = rzut(T, p);
    const kierRuchu = ostPoz && dist(ostPoz, p) > 3 ? brg(ostPoz, p) : null; if (!ostPoz || dist(ostPoz, p) > 3) ostPoz = p;
    // ikona „ja” – strzałka w kierunku jazdy
    const rot = kierRuchu ?? brg(wDal(T, r.w), wDal(T, r.w + 20));
    const ik = L.divIcon({className: '', html: `<svg class="ja" viewBox="0 0 30 30" style="transform:rotate(${rot}deg)"><circle cx="15" cy="15" r="13" fill="#1d4ed8" stroke="#fff" stroke-width="3"/><path d="M15 7l6 13-6-3-6 3z" fill="#fff"/></svg>`, iconSize: [30, 30], iconAnchor: [15, 15]});
    if (!jaM) jaM = L.marker(p, {icon: ik, interactive: false, zIndexOffset: 1000}).addTo(map); else { jaM.setLatLng(p); jaM.setIcon(ik); }
    if (sledz && obrocona) {
      // kierunek: trasa ok. 40 m przed Tobą (stabilny także na postoju), łagodnie wygładzony
      const cel = brg(wDal(T, r.w), wDal(T, r.w + 40)); B = (B + kat(cel, B) * .6 + 360) % 360;
      $('mapa').style.transform = tr(); kompas();
      map.setView(p, map.getZoom(), {animate: false});
    } else if (sledz) map.panTo(p, {animate: true, duration: .5});
    // zejście z trasy → przeliczenie od miejsca, w którym jesteś
    const prog = Math.max(40, Math.min(80, (acc || 20) * 1.5));
    if (r.d > prog && !wSym) {
      poza++;
      $('status').className = 'status zle'; $('status').querySelector('span').textContent = 'Poza trasą';
      if (poza >= 3 && Date.now() - ostPrzel > 8000) { ostPrzel = Date.now(); przelicz(p); }
      return;
    }
    poza = 0; $('status').className = 'status'; $('status').querySelector('span').textContent = acc > 40 ? 'Słaby GPS (±' + Math.round(acc) + ' m)' : 'Na trasie';
    if (r.w >= wzdluz - 30) { const przed = wzdluz; wzdluz = Math.max(wzdluz, r.w); idx = r.i; tempoAkt(przed, wzdluz); }
    odswiez();
  }
  // tempo rowerzysty: porównujemy faktyczny czas jazdy z czasem z modelu (postoje na skrzyżowaniach pomijamy);
  // na starcie zakładamy tempo z modelu, a im dłużej jedziesz, tym bardziej czas dojazdu opiera się na Twoim tempie
  const tempo = {real: 0, mod: 0, t: 0, v: 0, k: 1};
  function tempoAkt(w1, w2) {
    const t = Date.now(), dt = tempo.t ? (t - tempo.t) / 1000 : 0; tempo.t = t;
    if (!dt || dt > 30 || w2 <= w1) { if (dt > 3) tempo.v *= .5; return; }
    const v = (w2 - w1) / dt; tempo.v = tempo.v ? tempo.v * .6 + v * .4 : v;
    if (v < 0.8) return;                                   // stoisz / prowadzisz rower – nie liczymy
    tempo.real += dt; tempo.mod += czasDo(stan.T, w2) - czasDo(stan.T, w1);
    tempo.k = Math.max(0.6, Math.min(2, (tempo.real + 120) / (tempo.mod + 120)));
  }
  function przelicz(p) {
    stan.start = p; const T = policz(); if (T.blad) return;
    stan.T = T; stan.M = manewry(T); idx = 0; wzdluz = 0; zapowiedz = new Set(); rysuj(T, stan.M);
    powiedz('Nowa trasa'); navigator.vibrate && navigator.vibrate([80, 60, 80]);
    odswiez();
  }
  function odswiez() {
    const T = stan.T, M = stan.M;
    const zost = T.m - wzdluz;
    if (zost < 25) return dojechales();
    const nast = M.find(m => m.c > wzdluz - 20 && m.typ !== 'cel') || M[M.length - 1];
    const doN = Math.max(0, nast.c - wzdluz);
    // ekran przy drogowskazie (4b): od 30 m przed do 25 m za skrzyżowaniem
    const przy = M.find(m => m.typ === 'tab' && wzdluz > m.c - 30 && wzdluz < m.c + 25);
    if (przy !== kierPokaz) { kierPokaz = przy || null; if (przy) pokazKier(przy, M); else ekran('s-mapa'); }
    // pasek u góry: następny kierunek
    let html;
    if (nast.typ === 'tab') {
      html = `<div class="pasek"><div class="r1"><div class="strz">${strzalkaSVG(nast.k, '#00737e', 44)}</div><div><div class="lab">Następny kierunek · za ${kmTxt(doN)}</div><div class="co">${esc(kierTxt(nast.k))}, ${esc(nast.cele.join(' · '))}</div></div></div><div class="tab">${tabSVG(nast)}</div></div>`;
    } else if (nast.typ === 'skret') {
      html = `<div class="pasek"><div class="r1"><div class="strz">${strzalkaSVG(nast.k, '#00737e', 44)}</div><div><div class="lab">Następny skręt</div><div class="odl">${kmTxt(doN)}</div><div class="co">${esc(mTekst(nast))}</div></div></div></div>`;
    } else {
      html = `<div class="pasek"><div class="r1"><div class="strz">${strzalkaSVG('cel', '#1d3b30', 40)}</div><div><div class="lab">Do celu</div><div class="odl">${kmTxt(doN)}</div><div class="co">${esc(stan.celN)}</div></div></div></div>`;
    }
    if ($('gora').dataset.h !== html) { $('gora').innerHTML = html; $('gora').dataset.h = html; }
    const g = $('gora').getBoundingClientRect().height;
    $('prawe').style.top = (g + 12) + 'px'; $('status').style.top = (g + 12) + 'px'; $('b-sym').style.top = (g + 12) + 'px'; $('b-sym').style.right = '70px';
    const pozost = Math.max(0, (czasDo(T, T.m) - czasDo(T, wzdluz)) * tempo.k);
    $('j-zost').textContent = kmTxt(zost) + ' · ' + czasTxt(pozost) + ' · ' + godz(pozost);
    if (!odswiez.at) { odswiez.at = 1; atryb(); }
    const nTab = M.filter(m => m.typ === 'tab' && m.c > wzdluz).length;
    $('j-opis').textContent = (tempo.v > 0.8 ? Math.round(tempo.v * 3.6) + ' km/h · ' : '') + 'do: ' + stan.celN + (nTab ? ' · ' + nTab + ' drogowsk' + (nTab === 1 ? 'az' : nTab < 5 ? 'azy' : 'azów') + ' po drodze' : '');
    // zapowiedzi głosowe: ~150 m przed i na miejscu
    if (nast.typ !== 'cel') {
      const k = M.indexOf(nast);
      if (doN < 160 && doN > 60 && !zapowiedz.has(k + 'z')) { zapowiedz.add(k + 'z'); powiedz('Za ' + Math.round(doN / 10) * 10 + ' metrów: ' + mTekst(nast)); }
      if (doN <= 30 && !zapowiedz.has(k + 'n')) { zapowiedz.add(k + 'n'); powiedz(mTekst(nast)); navigator.vibrate && navigator.vibrate(200); }
    }
  }
  function pokazKier(m, M) {
    $('k-strz').innerHTML = strzalkaSVG(m.k, '#00737e', 48);
    $('k-tekst').innerHTML = esc(kierTxt(m.k)) + ', kierunek<br>' + esc(m.cele.join(' · '));
    $('k-tab').innerHTML = tabSVG(m, 'tb');
    const kol = m.t.e.flatMap(e => e[3] || []);
    $('k-opis').textContent = kol.length ? 'Kolorowe kółka na tabliczce to numery tras HUB – możesz się ich trzymać dalej.' : '';
    const i = M.indexOf(m), dalej = M[i + 1];
    $('k-potem').innerHTML = dalej ? `<b>Potem:</b> ${esc(mTekst(dalej))} · za ${kmTxt(dalej.c - m.c)}` : '';
    ekran('s-kier');
  }
  function dojechales() {
    if (!stan.jazda) return;
    powiedz('Jesteś na miejscu'); navigator.vibrate && navigator.vibrate([100, 80, 100, 80, 200]);
    if (watch) watch(); watch = null; if (sym) clearInterval(sym.t); sym = null;
    stan.jazda = false; try { wake && wake.release(); } catch (e) {}
    if (obrocona) obroc(false); $('b-kurs').classList.add('hide'); $('b-3d').classList.add('hide'); ekran('s-mapa'); panele('podglad');
    $("gora").innerHTML = `<div class="pasek" style="padding-left:76px"><div class="r1"><div class="strz">${strzalkaSVG("cel", "#1d3b30", 40)}</div><div><div class="lab">Jesteś na miejscu</div><div class="co">${esc(stan.celN)}</div></div></div></div>`; $('gora').dataset.h = '';
    $('dol').innerHTML = `<div class="uchwyt"></div><div style="font-size:20px;font-weight:800">Dojechałeś! ${kmTxt(stan.T.m)}</div><p class="msg">Coś było nie tak z trasą albo drogą? Oceń drogę na mapie wspólnej – poprawimy trasy dla wszystkich.</p><div class="rzad"><a class="btn2" href="${BAZA}#wspolna" style="text-decoration:none;color:inherit">Oceń drogę</a><button type="button" class="btn2" id="b-nowy">Nowy cel</button></div>`;
    $('b-nowy').onclick = () => { stan.start = jaM ? [jaM.getLatLng().lat, jaM.getLatLng().lng] : stan.start; if (jaM) { jaM.remove(); jaM = null; } ekran('s-cel'); };
  }
  // głos
  function powiedz(t) {
    if (!stan.glos) return;
    if (NAT && PL.TextToSpeech) { PL.TextToSpeech.speak({text: t, lang: 'pl-PL', rate: 1.0, category: 'playback'}).catch(() => {}); return; }
    if (!window.speechSynthesis) return; try { const u = new SpeechSynthesisUtterance(t); u.lang = 'pl-PL'; u.rate = 1.05; speechSynthesis.cancel(); speechSynthesis.speak(u); } catch (e) {} }
  function glosIkona() { $('b-glos').innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1d2a23" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9z"/>${stan.glos ? '<path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>' : '<path d="M17 9l5 6M22 9l-5 6"/>'}</svg>`; $('b-glos').ariaLabel = stan.glos ? 'Wyłącz komunikaty głosowe' : 'Włącz komunikaty głosowe'; }
  $('b-glos').onclick = () => { stan.glos = !stan.glos; LS.set('glos', stan.glos); glosIkona(); if (stan.glos) powiedz('Komunikaty głosowe włączone'); };
  $('b-srodek').onclick = () => { sledz = true; $('b-srodek').classList.add('hide'); if (kurs && stan.jazda) obroc(true); if (jaM) map.setView(jaM.getLatLng(), Math.max(map.getZoom(), 16), {animate: !obrocona}); };
  function trojwymiar() { const b = $('b-3d'); b.textContent = '3D'; b.style.cssText = `position:static;font-weight:800;font-size:15px;${tilt ? 'background:#00737e;color:#fff;box-shadow:0 0 0 3px #fff,0 1px 6px rgba(0,0,0,.3)' : ''}`; b.ariaLabel = tilt ? 'Widok płaski (2D)' : 'Widok pochylony (3D)'; b.setAttribute('aria-pressed', tilt); }
  $('b-3d').onclick = () => { tilt = !tilt; LS.set('tilt', tilt); trojwymiar(); if (tilt && !obrocona) { kurs = true; LS.set('kurs', true); } sledz = true; $('b-srodek').classList.add('hide'); obroc(true); };
  $('b-kurs').onclick = () => { kurs = !obrocona; LS.set('kurs', kurs); sledz = true; $('b-srodek').classList.add('hide'); obroc(kurs); };
  $('s-kier').onclick = () => { kierPokaz = null; ekran('s-mapa'); };   // dotknięcie – wróć do mapy

  // link z celem: jedz.html#do=lat,lon&n=Nazwa
  const hs = new URLSearchParams(location.hash.slice(1));
  if (hs.get('do')) { const [a, b] = hs.get('do').split(',').map(Number); if (isFinite(a) && isFinite(b)) setTimeout(() => ustawCel([a, b], hs.get('n') || 'Punkt na mapie', najblizszaMiejscowosc([a, b]) || ''), 300); }
  if (!NAT && 'serviceWorker' in navigator) navigator.serviceWorker.register('jedz-sw.js').catch(() => {});
  // przycisk „Zainstaluj na telefonie”: Android/Chrome – systemowe okno, iPhone – instrukcja; po instalacji znika
  const zainst = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  let prosba = null;
  if (!zainst && !NAT) {
    window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); prosba = e; $('b-instaluj').classList.remove('hide'); });
    if (ios) $('b-instaluj').classList.remove('hide');
  }
  window.addEventListener('appinstalled', () => $('b-instaluj').classList.add('hide'));
  $('b-instaluj').onclick = async () => {
    if (prosba) { prosba.prompt(); const w = await prosba.userChoice.catch(() => null); if (w && w.outcome === 'accepted') $('b-instaluj').classList.add('hide'); prosba = null; }
    else { $('ios').classList.remove('hide'); $('ios-ok').focus(); }
  };
  $('ios-ok').onclick = () => $('ios').classList.add('hide');
  $('ios').onclick = e => { if (e.target.id === 'ios') $('ios').classList.add('hide'); };
  window.JEDZ_DEBUG = {trasuj, manewry, stan, wDal, koszt, skok: d => { if (sym) sym.d = d; }};
})();
