// „Jedź” – nawigacja rowerowa HUB Strzebiń (beta).
// Trasa liczona w telefonie po drogach z mapy wspólnej (stan/odcinki.js). Prowadzenie kierunkami z drogowskazów:
// przy każdym słupku na trasie apka pokazuje tabliczkę, za której kierunkiem jechać (tak, jak widzi ją rowerzysta),
// poza słupkami – skręty z nazwami ulic.
// Ten plik: interfejs (wyszukiwanie celu, mapa, podgląd trasy, jazda, głos). Logika w lib/jedz/*.js.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {H, ODC, $, rad, RZ, dist, brg, kat, esc, kmTxt, czasTxt, godz, norm, LS, TRASY, ROWER, P, DW, koszt, najblizszy, trasuj, wDal, stOdc, ROWERY, PIESZE, ustawPieszo, ST, KOLST, NAZST, profil, czasDo, wykresSVG, strzalkaSVG, kierunek, kierTxt, manewry, mTekst, tabSVG} = JZ;
  // aplikacja na Androida (Capacitor): GPS z usługą w tle (jazda na zgaszonym ekranie) i głos z syntezatora telefonu
  const CAP = window.Capacitor;
  const NAT = !!(CAP && CAP.isNativePlatform && CAP.isNativePlatform());
  // BAZA musi być przed wszystkim, co z niej korzysta (zgłoszenia w aplikacji)
  const BAZA = NAT ? 'https://rowerowy-strzebin.smart-ant.pl/' : './';
  const wtyczka = n => { try { return (CAP.Plugins && CAP.Plugins[n]) || (window.capacitorExports && window.capacitorExports.registerPlugin(n)) || (CAP.registerPlugin && CAP.registerPlugin(n)) || null; } catch (e) { return null; } };
  const PL = NAT ? {BackgroundGeolocation: wtyczka('BackgroundGeolocation'), TextToSpeech: wtyczka('TextToSpeech'), LocalNotifications: wtyczka('LocalNotifications')} : {};
  const diag = {};
  const pokazDiag = () => { if (!NAT) return; const el = document.querySelector('#s-cel .stopka'); if (!el) return; let d = document.getElementById('diag'); if (!d) { d = document.createElement('div'); d.id = 'diag'; d.style.cssText = 'margin-top:6px;font-size:11px;opacity:.7'; el.appendChild(d); }
    d.textContent = 'Aplikacja · GPS w tle: ' + (PL.BackgroundGeolocation ? (diag.bg || 'gotowy') : 'brak') + ' · głos: ' + (PL.TextToSpeech ? (diag.glos || 'tak') : 'brak') + ' · powiadomienia: ' + (PL.LocalNotifications ? 'tak' : 'brak'); };
  setTimeout(pokazDiag, 500);
  // oceny dróg zatwierdzone w panelu (mapa wspólna) – najpierw zapamiętane w telefonie (działa bez zasięgu), potem świeże z serwera
  let ocenyN = JZ.oceny(LS.get('oceny', (window.JEDZ && JEDZ.oceny) || {}));
  // węzły przesunięte w panelu (słupki – drogowskazy na trasie liczone od nowego miejsca)
  const wezly = w => { for (const [nr, ll] of Object.entries(w || {})) { const p = H.posts.find(q => q.nr === +nr); if (p) { p.lat = ll[0]; p.lon = ll[1]; } } };
  wezly(LS.get('wezly', {}));
  // zatwierdzone na mapie wspólnej zmiany tabliczek (api/wezly.php), jeszcze niewdrożone w danych: usunięte kierunki znikają z drogowskazów w nawigacji
  const zmianyTab = L => { for (const z of L || []) { if ((H.wdrozone || []).includes(z.id) || z.wezel == null) continue;
    const p = H.posts.find(q => q.nr === z.wezel), us = (z.zmiany && z.zmiany.usun) || []; if (!p || !p.tab || !us.length) continue;
    p.tab = p.tab.map(t => ({...t, e: t.e.filter(e => !us.includes(e[0]))})).filter(t => t.e.length); } };
  zmianyTab(LS.get('zmianyTab', []));
  fetch(BAZA + 'api/wezly.php', {cache: 'no-store'}).then(r => r.ok ? r.json() : Promise.reject()).then(j => { if (j && Array.isArray(j.wezly)) { const L = j.wezly.map(z => ({id: z.id, wezel: z.wezel, zmiany: {usun: (z.zmiany && z.zmiany.usun) || []}})); LS.set('zmianyTab', L); zmianyTab(L); } }).catch(() => {});
  fetch(BAZA + 'api/stan.php', {cache: 'no-store'}).then(r => r.ok ? r.json() : Promise.reject()).then(j => {
    if (!j || !j.stany) return;
    const m = {}; for (const [id, zid] of Object.entries(j.stany)) { const z = j.zgloszenia[zid]; if (z) m[id] = z[0]; }
    LS.set('oceny', m); ocenyN = JZ.oceny(m); if (j.wezly) { LS.set('wezly', j.wezly); wezly(j.wezly); }
    if (stan.T && !stan.jazda && $('s-mapa').classList.contains('on') && $('dol').querySelector('.staty')) podglad();   // podgląd już otwarty – policz z nowymi ocenami
  }).catch(() => {});
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
  const CELE = (H.cele || []).filter(c => !/Rajza|Liswarcia/.test(c.n)).map(c => ({n: c.n, s: c.cat === 'blue' ? 'Miejscowość' : 'Cel z drogowskazów', lat: c.lat, lon: c.lon, typ: 'm'}))
    .concat(((window.JEDZ && JEDZ.szlaki) || []).map(s => ({n: s.n, s: 'szlak rowerowy – najbliższy wjazd', typ: 'm', szlak: s.n})));
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
  const TYPM = {stacja: 'Stacja napraw rowerów', serwis: 'Serwis rowerowy', wiata: 'Wiata', lawka: 'Ławka', piknik: 'Piknik / ognisko', widok: 'Punkt widokowy', woda: 'Woda', jedzenie: 'Jedzenie', kawa: 'Kawiarnia', bar: 'Bar', nocleg: 'Nocleg', kosciol: 'Kościół / kapliczka', zabytek: 'Zabytek', przyroda: 'Przyroda', sport: 'Sport', zabawa: 'Plac zabaw', wc: 'WC', aed: 'Defibrylator AED', apteka: 'Apteka', pkp: 'Kolej', autobus: 'Przystanek autobusowy', sklep: 'Sklep spożywczy', parking: 'Parking', ciekawe: 'Ciekawe miejsce'};
  const MIEJSCA = (H.places || []).filter(p => p.nazwa && p.typ !== 'lawka').map(p => ({n: p.nazwa, s: (TYPM[p.typ] || 'Miejsce') + (najblizszaMiejscowosc([p.lat, p.lon]) ? ' · ' + najblizszaMiejscowosc([p.lat, p.lon]) : ''), lat: p.lat, lon: p.lon, typ: 'p'}));
  // węzły (słupki) HUB: wpisz „49”, „w49” albo „węzeł 49”; położenie bierzemy z H.posts w chwili wyboru (przesunięcia z panelu)
  const WEZLY = H.posts.map(p => ({n: 'Węzeł ' + p.nr, s: p.loc || 'węzeł HUB', p, typ: 'w', nr: p.nr}));
  const WSZYSTKO = [...CELE, ...MIEJSCA, ...ULICE, ...WEZLY].map(x => ({...x, q: norm(x.n + ' ' + x.s + (x.typ === 'w' ? ' slupek w' + x.nr : ''))}));
  const celXY = x => x.p ? [x.p.lat, x.p.lon] : [x.lat, x.lon];
  function szukaj(q) {
    q = norm(q.trim());
    const nr = q.match(/^(?:w|wezel|wezla|slupek|nr)?\s*\.?\s*(\d{1,3})$/);   // sam numer – węzeł na pierwszym miejscu
    if (nr) { const w = WSZYSTKO.find(x => x.typ === 'w' && x.nr === +nr[1]); if (q.length < 2) return w ? [w] : [];
      const reszta = q.length >= 2 ? szukajTekst(q).filter(x => x !== w) : []; return (w ? [w] : []).concat(reszta).slice(0, 12); }
    return szukajTekst(q);
  }
  function szukajTekst(q) {
    if (q.length < 2) return [];
    // numer domu („Lubliniecka 47”, „sienkiewicza 5a”) – adresów z numerami nie mamy, więc szukamy samej ulicy
    let sl = q.split(/\s+/).filter(Boolean); const bezNr = sl.filter(w => !/^\d+[a-z]?(\/\d+)?$/.test(w));
    if (bezNr.length && bezNr.length < sl.length) { sl = bezNr; q = bezNr.join(' '); }
    // przy równym dopasowaniu bliższe wyniki wyżej (ta sama ulica jest w kilku miejscowościach)
    const ja = (typeof stan !== 'undefined' && stan.start) || [50.616, 18.897];
    return WSZYSTKO.map(x => {
      if (!sl.every(w => x.q.includes(w))) return null;
      const n = norm(x.n).replace(/^ul\. /, ''); let sc = n.startsWith(q) || n.startsWith(sl[0]) ? 0 : n.includes(' ' + sl[0]) ? 1 : 2;
      sc += {m: 0, p: .3, u: .6, w: .9}[x.typ];
      const xy = x.p ? [x.p.lat, x.p.lon] : [x.lat, x.lon];
      return [sc + Math.min(dist(ja, xy) / 40000, .29), x];
    }).filter(Boolean).sort((a, b) => a[0] - b[0] || a[1].n.length - b[1].n.length).slice(0, 12).map(a => a[1]);
  }
  const IKW = {m: ['#e7eef8', '#0759A7', 'M3 21h18M5 21V10l7-5 7 5v11M10 21v-6h4v6'], u: ['#dfe9e4', '#1d3b30', 'M4 20 10 4M20 20 14 4M12 6v2M12 11v2M12 16v2'], p: ['#f3e9dc', '#81552F', 'M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12zM12 11.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5'], g: ['#e5e7eb', '#1d2a23', 'M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z']};
  function pokazWyniki(lista) {
    const el = $('wyniki');
    el.classList.toggle('hide', !lista.length); $('szybkie').classList.toggle('hide', !!lista.length);
    el.innerHTML = lista.map((x, i) => { const [bg, kol, d] = IKW[x.typ] || IKW.g;
      if (x.typ === 'w') return `<button type="button" role="option" data-i="${i}"><span class="ik" style="background:#1d3b30;color:#fff;border-radius:50%;font-size:${x.nr > 9 ? 14 : 16}px">${x.nr}</span><span><span class="t">${esc(x.n)}</span><br><span class="s">${esc(x.s)}</span></span></button>`;
      return `<button type="button" role="option" data-i="${i}"><span class="ik" style="background:${bg}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${kol}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg></span><span><span class="t">${esc(x.n)}</span><br><span class="s">${esc(x.s)}</span></span></button>`; }).join('');
    el.querySelectorAll('button').forEach(b => b.onclick = () => { const x = lista[+b.dataset.i]; if (x.szlak) return doSzlaku(x.szlak); ustawCel(celXY(x), x.n, x.s); });
  }
  $('szukaj').addEventListener('input', e => pokazWyniki(szukaj(e.target.value)));
  $('szukaj').addEventListener('keydown', e => { if (e.key === 'Enter') { const w = szukaj(e.target.value); if (w[0]) { if (w[0].szlak) doSzlaku(w[0].szlak); else ustawCel(celXY(w[0]), w[0].n, w[0].s); } } });
  const SZYBKIE = [['Strzebiń', ''], ['Bukowiec', ''], ['Koszęcin', ''], ['Kalety', ''], ['Boronów', ''], ['Leśno Rajza', 'g'], ['Stacja napraw', 's']];
  $('chipy').innerHTML = SZYBKIE.map(([n, c]) => `<button type="button" class="${c}">${n}</button>`).join('');
  $('chipy').querySelectorAll('button').forEach(b => b.onclick = () => {
    const n = b.textContent;
    if (n === 'Stacja napraw') { const s = (H.places || []).filter(p => p.typ === 'stacja'); const ja = stan.start || [50.616, 18.897]; s.sort((a, c) => dist(ja, [a.lat, a.lon]) - dist(ja, [c.lat, c.lon])); if (s[0]) ustawCel([s[0].lat, s[0].lon], 'Stacja napraw rowerów', s[0].opis || ''); return; }
    if (n === 'Leśno Rajza') return doSzlaku('Leśno Rajza');
    const c = (H.cele || []).find(c => c.n === n); if (c) ustawCel([c.lat, c.lon], c.n, 'Miejscowość');
  });
  // ---- miejsca (POI): stałe z data.js + zatwierdzone z mapy wspólnej (api/miejsca.php) z poprawkami administratora
  const MJ = window.MIEJSCA;
  let MSC = (H.places || []).slice();
  function ladujMSC(j) { if (!j || !MJ) return; const K = j.korekty || {};
    MSC = (H.places || []).map(m => MJ.popraw(m, K)).concat((j.miejsca || []).map(m => MJ.popraw(m, K))).filter(Boolean); setTimeout(rysujPOI, 0); }
  ladujMSC(LS.get('miejsca', null));
  fetch(BAZA + 'api/miejsca.php', {cache: 'no-store'}).then(r => r.ok ? r.json() : Promise.reject()).then(j => { if (j && j.miejsca) { LS.set('miejsca', j); ladujMSC(j); } }).catch(() => {});
  // „W pobliżu”: 5 najbliższych miejsc danego rodzaju, odległość i czas liczone po drogach (nie w linii prostej)
  const POBL = [['aed', 'AED', ['aed']], ['apteka', 'Apteka', ['apteka']], ['sklep', 'Sklep', ['sklep']], ['jedzenie', 'Jedzenie', ['jedzenie', 'kawa', 'bar']],
                ['wc', 'WC', ['wc']], ['pkp', 'Pociąg', ['pkp']], ['autobus', 'Autobus', ['autobus']], ['stacja', 'Serwis rowerowy', ['stacja', 'serwis', 'wypozycz']], ['wiata', 'Wiata / odpoczynek', ['wiata', 'piknik']]];
  if (MJ) {
    $('pobl-chipy').innerHTML = POBL.map(([t, n]) => `<button type="button" data-k="${t}" aria-pressed="false" style="background:${MJ.TYP[t].c}"><span class="mj">${MJ.svg(t, '#fff', 15)}</span>${n}</button>`).join('');
    $('pobl-chipy').querySelectorAll('button').forEach(b => b.onclick = () => {
      const on = b.getAttribute('aria-pressed') === 'true';
      $('pobl-chipy').querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', 'false'));
      if (on) { $('pobl-lista').classList.add('hide'); $('pobl-msg').hidden = true; return; }
      b.setAttribute('aria-pressed', 'true'); wPoblizu(POBL.find(x => x[0] === b.dataset.k));
    });
  }
  function godzTxt(m) { const g = MJ && MJ.godziny(m.h); if (!g) return '';
    return `<div class="g">${g.otwarte === true ? `<b class="o">otwarte${esc(g.dopisek || '')}</b> · ` : g.otwarte === false ? '<b class="z">teraz zamknięte</b> · ' : ''}${esc(g.txt)}</div>`; }
  function wPoblizu([kat, nazwa, typy]) {
    const msg = t => { $('pobl-msg').textContent = t; $('pobl-msg').hidden = !t; };
    const licz = ja => {
      const kand = MSC.filter(m => typy.includes(m.typ)).map(m => ({m, d: dist(ja, [m.lat, m.lon])})).filter(x => x.d < 30000).sort((a, b) => a.d - b.d).slice(0, 10);
      const w = [];
      for (const x of kand) { const T = trasuj(ja, [x.m.lat, x.m.lon], {tryb: stan.tryb}); if (T.blad) continue; T.prof = profil(T); w.push({...x, T}); }
      w.sort((a, b) => a.T.m - b.T.m); const top = w.slice(0, 5);
      if (!top.length) { $('pobl-lista').classList.add('hide'); return msg(`Nie mamy na mapie ${nazwa.toLowerCase()} w promieniu 30 km.`); }
      msg('');
      $('pobl-lista').innerHTML = top.map((x, i) => { const t = MJ.TYP[x.m.typ];
        return `<button type="button" data-i="${i}"><span class="ik" style="background:${t.c}">${MJ.svg(x.m.typ, '#fff', 18, x.m.ik)}</span><span style="flex:1;min-width:0"><span class="t">${esc(x.m.nazwa || t.n)}</span><br>
          <span class="s">${kmTxt(x.T.m)} · ${czasTxt(x.T.prof.czas)} · ${esc(x.m.nazwa ? t.n : (najblizszaMiejscowosc([x.m.lat, x.m.lon]) || ''))}</span>${godzTxt(x.m)}</span></button>`; }).join('');
      $('pobl-lista').classList.remove('hide');
      $('pobl-lista').querySelectorAll('button').forEach(b => b.onclick = () => { const x = top[+b.dataset.i]; ustawCel([x.m.lat, x.m.lon], x.m.nazwa || MJ.TYP[x.m.typ].n, MJ.TYP[x.m.typ].n); });
    };
    if (stan.start) return licz(stan.start);
    msg('Ustalam Twoją lokalizację…');
    gps(p => { stan.start = p; opiszStart(); licz(p); }, e => msg(e));
  }
  // ---- miejsca na mapie nawigacji: AED, apteki i stacje napraw od przybliżenia 13, reszta od 15; dotknięcie – opis i „Jedź tutaj”.
  //      Rysujemy tylko znaczniki w widocznym obszarze (z zapasem) – setki znaczników poza ekranem spowalniały by mapę na telefonie.
  let poiL = null, poiKlucz = '';
  // wybór miejsc na mapie (przycisk z pinezką): kategorie pamiętane w telefonie
  const POIK = [['aed', 'AED', ['aed', 'apteczka']], ['apteka', 'Apteki', ['apteka']], ['sklep', 'Sklepy', ['sklep']], ['jedzenie', 'Jedzenie', ['jedzenie', 'kawa', 'bar']],
    ['wc', 'WC', ['wc']], ['autobus', 'Przystanki', ['autobus', 'pkp']], ['stacja', 'Serwis rowerowy', ['stacja', 'serwis', 'wypozycz', 'stojak']],
    ['wiata', 'Odpoczynek', ['wiata', 'piknik', 'lawka', 'widok', 'woda', 'zabawa']], ['ciekawe', 'Ciekawe miejsca', ['ciekawe', 'zabytek', 'kosciol', 'przyroda', 'sport']],
    ['nocleg', 'Nocleg', ['nocleg']], ['parking', 'Parking i inne', []]];
  const poiKat = t => (POIK.find(k => k[2].includes(t)) || POIK[POIK.length - 1])[0];
  let poiOff = new Set(LS.get('poiOff', []));
  $('b-poi').onclick = () => {
    if (!MJ) return; const el = $('poiu'); if (!el.classList.contains('hide')) { el.classList.add('hide'); return; }
    el.innerHTML = `<h3>Miejsca na mapie</h3><div class="o">Wybierz, co pokazywać (widać po przybliżeniu mapy).</div>
      <div class="poik">${POIK.map(([k, n]) => `<label><input type="checkbox" data-k="${k}"${poiOff.has(k) ? '' : ' checked'}><span class="mj" style="background:${(MJ.TYP[k] || MJ.TYP.parking).c}">${MJ.svg(MJ.TYP[k] ? k : 'parking', '#fff', 15)}</span>${n}</label>`).join('')}</div>
      <div class="poiz"><button type="button" id="poi-all">Wszystkie</button><button type="button" id="poi-none">Żadne</button></div><button type="button" class="an" id="poi-ok">Gotowe</button>`;
    el.classList.remove('hide'); $('ocs').classList.add('hide');
    const ust = () => { poiOff = new Set([...el.querySelectorAll('input')].filter(i => !i.checked).map(i => i.dataset.k)); LS.set('poiOff', [...poiOff]); poiKlucz = ''; rysujPOI.widok(); };
    el.querySelectorAll('input').forEach(i => i.onchange = ust);
    $('poi-all').onclick = () => { el.querySelectorAll('input').forEach(i => i.checked = true); ust(); };
    $('poi-none').onclick = () => { el.querySelectorAll('input').forEach(i => i.checked = false); ust(); };
    $('poi-ok').onclick = () => el.classList.add('hide');
  };
  const WAZNE = ['aed', 'apteka', 'stacja'];
  function rysujPOI() {
    if (!map || !MJ) return;
    if (!poiL) { poiL = L.layerGroup().addTo(map); map.on('moveend zoomend', () => rysujPOI.widok());
      map.on('popupopen', e => { const b = e.popup.getElement().querySelector('.jt'); if (b) b.onclick = () => { map.closePopup(); const m = MSC[+b.dataset.i]; if (m) { ekran('s-cel'); ustawCel([m.lat, m.lon], m.nazwa || MJ.TYP[m.typ].n, MJ.TYP[m.typ].n); } }; }); }
    poiKlucz = ''; rysujPOI.widok();
  }
  rysujPOI.widok = () => {
    if (!poiL) return;
    const z = map.getZoom(), bb = map.getBounds().pad(0.3);
    const wid = z < 13 ? [] : MSC.map((m, i) => [m, i]).filter(([m]) => MJ.TYP[m.typ] && !poiOff.has(poiKat(m.typ)) && (z >= 15 || WAZNE.includes(m.typ)) && bb.contains([m.lat, m.lon]));
    const k = wid.map(x => x[1]).join(',') + '|' + stan.jazda; if (k === poiKlucz) return; poiKlucz = k;
    poiL.clearLayers();
    for (const [m, i] of wid) L.marker([m.lat, m.lon], {icon: MJ.icon(m), title: m.nazwa || MJ.TYP[m.typ].n, zIndexOffset: 100})
      .bindPopup(() => MJ.popup(m).replace(/<\/div>\s*$/, '') + (stan.jazda ? '' : `<button type="button" class="jt" data-i="${i}">Jedź tutaj</button>`) + '</div>', {maxWidth: 260}).addTo(poiL);
  };
  // nawigacja do szlaku (Leśno Rajza, Liswarciański): kilka najbliższych punktów szlaku (co najmniej 400 m od siebie),
  // dla każdego trasa po drogach – wybieramy najkrótszą, czyli najbliższe miejsce, w którym naprawdę wjedziesz na szlak
  function doSzlaku(nazwa) {
    const sz = ((window.JEDZ && JEDZ.szlaki) || []).find(s => s.n === nazwa); if (!sz) return;
    const licz = ja => {
      const pkt = sz.linie.flat().map(p => [p, dist(ja, p)]).sort((a, b) => a[1] - b[1]), kand = [];
      for (const [p] of pkt) { if (kand.every(q => dist(q, p) > 400)) kand.push(p); if (kand.length >= 5) break; }
      let best = null; for (const p of kand) { const T = trasuj(ja, p, {tryb: stan.tryb}); if (!T.blad && (!best || T.m < best.m)) best = {p, m: T.m}; }
      if (best) ustawCel(best.p, nazwa, 'najbliższy wjazd na szlak');
    };
    if (stan.start) return licz(stan.start);
    gps(p => { stan.start = p; opiszStart(); licz(p); }, () => licz([50.616, 18.897]));
  }
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
      box.innerHTML = `<div class="moff"><span><b>Mapa offline</b> – lasy, wody, budynki i nazwy także bez zasięgu. <button type="button" class="moff-b" id="moff-p">Pobierz mapę offline (ok. 8 MB)</button></span></div>`;
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
    // trasa i znaczniki jako SVG: płótno canvas przy obróconej / pochylonej (3D) mapie miało ponad 4000×4000 px i każdy ruch
    // przerysowywał je od nowa (przycięcia na telefonie). Animacja przybliżania zostaje – patrz widok() niżej.
    map = L.map('mapa', {zoomControl: false, attributionControl: false, preferCanvas: false, renderer: L.svg({padding: 0.1})}).setView([50.615, 18.9], 13);
    map.on('zoomend', () => { if (czekaWidok) { const [p, z] = czekaWidok; czekaWidok = null; map.setView(p, z ?? map.getZoom(), {animate: false}); } });
    // mapa offline (lib/jedz/podklad.js) zawsze pod spodem; kafelki OSM na wierzchu, chyba że wybrano „zawsze offline”.
    // Bez zasięgu kafelki się nie wczytają (zostają niewidoczne) i widać podkład offline – wtedy dokładamy też nazwy miejscowości.
    map.createPane('nazwy').style.zIndex = 390;
    // podkład rysujemy TYLKO gdy jest potrzebny (zawsze offline albo kafelki się nie wczytują) – rysowanie tysięcy dróg
    // na telefonie kosztuje, a przy zasięgu i tak przykrywają go kafelki OSM
    const podklad = JZ.podklad.warstwa(L), nazwy = JZ.podklad.nazwy(L, map);
    const pokazPodklad = tak => { if (tak) { if (!map.hasLayer(podklad)) podklad.addTo(map); nazwy.addTo(map); } else { podklad.remove(); nazwy.remove(); } };
    let bledyK = 0, ostOk = 0;
    const kafelki = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {maxZoom: 19, attribution: '© OpenStreetMap', keepBuffer: 1})
      .on('tileerror', () => { if (++bledyK >= 3 && Date.now() - ostOk > 4000) pokazPodklad(true); })
      .on('tileload', () => { ostOk = Date.now(); bledyK = 0; if (!mapaOffline && map.hasLayer(podklad)) pokazPodklad(false); });
    mapaUstaw = off => { mapaOffline = off; if (off) { kafelki.remove(); pokazPodklad(true); } else { kafelki.addTo(map); pokazPodklad(false); } };
    mapaUstaw(mapaOffline);
    // drogi rowerowe i szerokie chodniki wzdłuż DW – pod trasą
    if (window.INFRA) { map.createPane('infra').style.zIndex = 380; INFRA.warstwa(L, {pane: 'infra', gr: 4}).addTo(map); }
    warstwa = L.layerGroup().addTo(map);
    map.on('dragstart', () => { if (stan.jazda) { sledz = false; $('b-srodek').classList.remove('hide'); } });
    // obrót „zablokowany” kompasem: mapy nie da się przesunąć, ale da się ją przybliżać/oddalać (wokół Twojej pozycji);
    // odblokowanie – tylko przyciskiem kompasu
    window.addEventListener('resize', () => { if (obrocona) obroc(true); });
    map.on('click', e => { if (stan.wybor) stan.wybor([e.latlng.lat, e.latlng.lng]); });
    rysujPOI();
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
        zgodaPow.then(() => stop ? null : PL.BackgroundGeolocation.addWatcher({backgroundTitle: 'Jedź – nawigacja aktywna', backgroundMessage: opis || 'Prowadzimy Cię trasą rowerową', requestPermissions: true, stale: !!stara, distanceFilter: !stara && LS.get('oszcz', false) ? 8 : 0},
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
    $('gora').innerHTML = `<div class="pasek" style="padding-left:70px"><div class="co">${esc(tytul)}</div><div class="lab">Działa na obszarze mapy HUB-u (Koszęcin i okolice)</div></div>`;
    $('dol').innerHTML = start ? `<button type="button" class="btn2" id="b-gps">${strzalkaSVG('prosto', '#1d2a23', 18)}Użyj mojej lokalizacji (GPS)</button><p class="msg" id="msg-w"></p>` : '<p class="msg" id="msg-w"></p>';
    if (start) $('b-gps').onclick = () => gps(p => { stan.start = p; stan.startGPS = true; opiszStart(); stan.wybor = null; ekran('s-cel'); }, e => { $('msg-w').textContent = e; });
    map.setView(stan.cel || stan.start || [50.615, 18.9], 13);
    stan.wybor = p => { if (najblizszy(p)[1] > 600) { $('msg-w').textContent = 'Za daleko od dróg z mapy HUB-u – wybierz punkt bliżej Koszęcina i okolic.'; $('msg-w').className = 'msg err'; return; } stan.wybor = null; cb(p); };
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
    if (tryb !== 'jazda') $('prawe').style.top = 'calc(14px + env(safe-area-inset-top))';   // poza jazdą przyciski po prawej na wysokości „Wróć” (pod paskiem stanu telefonu)
    $('b-glos').classList.toggle('hide', tryb !== 'jazda'); $('b-ocen').classList.toggle('hide', tryb !== 'jazda'); $('b-srodek').classList.add('hide'); if (tryb !== 'jazda') ocenaZamknij();
    $('status').classList.toggle('hide', tryb !== 'jazda'); $('b-sym').classList.toggle('hide', !(tryb === 'jazda' && sym));
  }

  // ===================== 2. podgląd trasy =====================
  // kary dla odcinków: wybrany wariant alternatywny (podgląd) i objazd trudnego odcinka (jazda) – ważne dla tego samego celu i trybu
  const klucz = () => JSON.stringify(stan.cel) + '|' + stan.tryb;
  function kary() {
    const m = new Map();
    for (const k of [stan.kara, stan.objazd]) if (k && k.klucz === klucz()) for (const [id, f] of k.ids) m.set(id, Math.max(m.get(id) || 1, f));
    return m.size ? m : null;
  }
  function policz() {
    const opc = {tryb: stan.tryb, kara: kary()};
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
  const TRYBY = {bezp: 'Bezpieczna', krotko: 'Najkrótsza', szosa: 'Szosowa', pieszo: 'Spacerowa'};
  function ostrzezenie(T, inne) {
    if (ST.pieszo) return '';
    const a = nieutw(T); let alt = null;
    for (const [k, X] of Object.entries(inne || {})) { const b = nieutw(X); if (X && !X.blad && b.nu < a.nu - 200 && (!alt || b.nu < alt.nu)) alt = {k, nu: b.nu}; }
    const lepiej = alt ? ` Trasa „${TRYBY[alt.k]}” ma ich mniej (${kmTxt(alt.nu)}).` : '';
    if (ST.RT === 'szosa' && a.nu > 300) return `⚠ Szosówką może być ciężko: ${kmTxt(a.nu)} trasy to drogi nieutwardzone, leśne albo bez oceny.${lepiej}`;
    if (ST.RT !== 'gorski' && ST.RT !== 'gravel' && a.tr > 200) return `⚠ Na trasie ${kmTxt(a.tr)} dróg ocenionych jako trudne (piach, korzenie, dziury).${lepiej}`;
    return '';
  }
  const tempoNazwa = v => ST.pieszo ? (ST.PT === 'bieg' ? (v < 8.5 ? 'trucht' : v < 12 ? 'bieg' : 'szybki bieg') : ST.PT === 'nordic' ? (v < 5.5 ? 'spokojnie' : v < 7 ? 'marsz' : 'szybko') : (v < 4 ? 'spacerowo' : v < 5.5 ? 'marsz' : 'szybki marsz')) : v < 13 ? 'spacerowo' : v < 20 ? 'rekreacyjnie' : v < 27 ? 'sportowo' : 'wyczynowo';
  // biegacze myślą tempem (min/km) – przy biegu pokazujemy oba
  const vTxt = v => String(v).replace('.', ',') + (ST.pieszo && ST.PT === 'bieg' ? '' : '');
  const vOpis = v => vTxt(v) + ' km/h' + (ST.pieszo && ST.PT === 'bieg' ? ` (${Math.floor(60 / v)}:${String(Math.round(3600 / v) % 60).padStart(2, '0')} min/km)` : '');
  function tempoSuwak(T) {
    const r = $('p-tempo'); if (!r) return;
    r.oninput = () => {
      ST.VU = +r.value; LS.set(ST.pieszo ? 'vpiesza_' + ST.PT : 'vplaska', ST.VU); T.prof = profil(T);
      $('p-v').textContent = vOpis(ST.VU) + ' · ' + tempoNazwa(ST.VU); $('p-czas').textContent = czasTxt(T.prof.czas);
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
  // ===================== trasa alternatywna (podgląd) =====================
  // kandydaci: wariant omijający odcinki głównej trasy (×1,8), trasy z innych trybów, a gdy wybrano już wariant – zwykła trasa.
  // Pokazujemy pierwszego, który naprawdę się różni (wspólne < 75%) i nie jest dużo dłuższy (< +60%).
  function alternatywa(T, inne) {
    const P0 = JZ.podsumuj(T), kand = [];
    if (kary()) kand.push({typ: 'zwykla', T: trasuj(stan.start, stan.cel, {tryb: stan.tryb})});
    const omin = new Map(); for (const id of P0.ids.keys()) omin.set(id, 1.8);
    kand.push({typ: 'objazd', T: trasuj(stan.start, stan.cel, {tryb: stan.tryb, kara: omin}), ids: omin});
    for (const [k, X] of Object.entries(inne)) kand.push({typ: 'tryb', tryb: k, T: X});
    for (const c of kand) {
      if (!c.T || c.T.blad || c.T.m > T.m * 1.6) continue;
      const PA = JZ.podsumuj(c.T); if (JZ.wspolne(PA, P0) > 0.75) continue;
      c.T.prof = profil(c.T); c.P = PA; c.P0 = P0; c.txt = altOpis(PA, P0, c.T.prof.czas - T.prof.czas, c); return c;
    }
    return null;
  }
  function altOpis(A, B, dt, c) {
    const d = A.m - B.m, t = [];
    t.push((d >= 0 ? '+' : '−') + kmTxt(Math.abs(d)) + (Math.abs(dt) >= 60 ? ` (${dt >= 0 ? '+' : '−'}${Math.round(Math.abs(dt) / 60)} min)` : ''));
    if (B.tr - A.tr > 80) t.push('omija ' + kmTxt(B.tr - A.tr) + ' drogi trudnej');
    else if (B.sr - A.sr > 200) t.push('mniej o ' + kmTxt(B.sr - A.sr) + ' drogi średniej');
    if (B.dw - A.dw > 100) t.push('mniej jezdnią DW o ' + kmTxt(B.dw - A.dw));
    if (A.tr - B.tr > 80) t.push('ale ' + kmTxt(A.tr - B.tr) + ' drogi trudnej');
    if (A.dw - B.dw > 100) t.push('ale ' + kmTxt(A.dw - B.dw) + ' jezdnią DW');
    if (A.sr - B.sr > 200 && !(B.tr - A.tr > 80)) t.push('ale ' + kmTxt(A.sr - B.sr) + ' drogi średniej');
    if (A.nu - B.nu > 300) t.push('więcej dróg nieutwardzonych / bez oceny (+' + kmTxt(A.nu - B.nu) + ')');
    else if (B.nu - A.nu > 300) t.push('więcej po utwardzonej (+' + kmTxt(B.nu - A.nu) + ')');
    if (c.typ === 'tryb') t.push('tryb „' + TRYBY[c.tryb] + '”');
    return t.join(' · ');
  }
  function rysujAlt(c) {
    const A = c.T, g = L.layerGroup().addTo(warstwa);
    const kl = () => wybierzAlt(c);
    L.polyline(A.ll, {color: '#fff', weight: 9, opacity: .9}).on('click', kl).addTo(g).bringToBack();
    L.polyline(A.ll, {color: '#7f9e9a', weight: 5, opacity: .95, dashArray: '10 7', lineCap: 'round'}).on('click', kl).addTo(g);
    // dopisek w miejscu najdalszym od głównej trasy
    const M = stan.T.ll.filter((_, i) => i % 3 === 0); let best = null, bd = -1;
    for (let i = 0; i < A.ll.length; i += 2) { let m = 1e9; for (const q of M) m = Math.min(m, dist(A.ll[i], q)); if (m > bd) { bd = m; best = A.ll[i]; } }
    if (best && bd > 30) L.marker(best, {icon: L.divIcon({className: '', html: `<div class="alt-et">${esc((c.typ === 'zwykla' ? 'główna · ' : '') + c.txt.split(' · ')[0])}</div>`, iconSize: null})}).on('click', kl).addTo(g);
    g.eachLayer(l => l.bringToBack && l.bringToBack());
  }
  function wybierzAlt(c) {
    if (c.typ === 'tryb') { stan.tryb = c.tryb; LS.set('tryb', stan.tryb); stan.kara = null; }
    else if (c.typ === 'objazd') stan.kara = {klucz: klucz(), ids: c.ids};
    else { stan.kara = null; stan.objazd = null; }
    const y = $('dol').scrollTop; podglad(); $('dol').scrollTop = y;
  }
  // inne tempo / rower → inna godzina przyjazdu: odśwież zdanie o zmroku (prognoza zostaje)
  function slOdswiez(T) { const e = document.querySelector('#p-pog .pg-sl'); if (e && JZ.pogoda) e.textContent = JZ.pogoda.swiatlo(T.ll[0][0], T.ll[0][1], T.prof.czas); }
  function podglad() {
    if (stan.tryb === 'szosa' && ST.RT !== 'szosa') stan.tryb = 'bezp';
    if (ST.pieszo && stan.tryb !== 'krotko') stan.tryb = 'pieszo'; else if (!ST.pieszo && stan.tryb === 'pieszo') stan.tryb = 'bezp';
    ekran('s-mapa'); mapa(); panele('podglad'); stan.wybor = null;
    $('gora').innerHTML = '';
    const T = policz();
    if (T.blad) {
      warstwa.clearLayers();
      $('dol').innerHTML = `<div class="uchwyt"></div><p class="msg err">${T.blad === 'start' ? 'Jesteś poza obszarem mapy HUB-u (Koszęcin i okolice). Zmień start – możesz go wskazać na mapie.' : T.blad === 'cel' ? 'Cel jest poza obszarem mapy HUB-u.' : 'Nie znalazłem drogi między tymi punktami.'}</p><button type="button" class="btn2" id="b-wroc">Wróć</button>`;
      $('b-wroc').onclick = () => ekran('s-cel'); return;
    }
    stan.T = T; stan.M = manewry(T); rysuj(T, stan.M);
    // porównanie z drugim trybem (do przełącznika)
    // pozostałe tryby (do przełącznika i podpowiedzi w ostrzeżeniu); „Szosowa” tylko przy rowerze szosowym
    const tryby = ST.pieszo ? ['pieszo', 'krotko'] : ST.RT === 'szosa' ? ['bezp', 'krotko', 'szosa'] : ['bezp', 'krotko'];
    const inne = {}; for (const k of tryby) if (k !== stan.tryb) inne[k] = trasuj(stan.start, stan.cel, {tryb: k});
    const km = k => k === stan.tryb ? T.m : inne[k].m;
    const alt = alternatywa(T, inne); if (alt) rysujAlt(alt);
    const opisT = {bezp: ' · omija DW i DK', krotko: '', szosa: ' · asfalt, główne drogi', pieszo: ' · lasem i ścieżkami'};
    const nTab = stan.M.filter(m => m.typ === 'tab').length;
    const lista = stan.M.slice(0, 40).map(m => `<div>${strzalkaSVG(m.k, m.typ === 'tab' ? '#0759A7' : m.typ === 'cel' ? '#1d3b30' : '#1d2a23', 22)}<span>${esc(mTekst(m))}</span><span class="km">${kmTxt(m.c)}</span></div>`).join('');
    $('dol').innerHTML = `<div class="uchwyt"></div>
      <div><div class="msg">${esc(stan.startGPS ? 'Z Twojej lokalizacji' : stan.startN)} →</div><div style="font-size:21px;font-weight:800">${esc(stan.celN)}</div>${stan.celS ? `<div class="msg">${esc(stan.celS)}</div>` : ''}</div>
      <div class="tryb${tryby.length > 2 ? ' t3' : ''}" role="radiogroup" aria-label="Rodzaj trasy">
        ${tryby.map(k => `<button type="button" role="radio" data-t="${k}" aria-checked="${stan.tryb === k}"><b>${TRYBY[k]}</b><span>${kmTxt(km(k))}${opisT[k]}</span></button>`).join('')}
      </div>
      ${alt ? `<div class="alt"><span><b>${alt.typ === 'zwykla' ? 'Wróć do głównej trasy' : 'Trasa alternatywna'}</b> – ${esc(alt.txt)}</span><button type="button" class="moff-b" id="b-alt">Wybierz</button></div>` : ''}
      <div class="staty"><div><b>${kmTxt(T.m)}</b><span>długość</span></div><div><b id="p-czas">${czasTxt(T.prof.czas)}</b><span>${ST.pieszo ? (ST.PT === 'bieg' ? 'czasu biegu' : 'czasu marszu') : 'czasu jazdy'}</span></div><div><b>${nTab}</b><span>drogowskazów</span></div></div>
      <div class="tryb pr" role="radiogroup" aria-label="Rowerem czy pieszo"><button type="button" role="radio" data-p="0" aria-checked="${!ST.pieszo}"><b>🚲 Rowerem</b></button><button type="button" role="radio" data-p="1" aria-checked="${ST.pieszo}"><b>🚶 Pieszo</b></button></div>
      ${ST.pieszo ? `<div class="rower" role="radiogroup" aria-label="Rodzaj aktywności">${Object.entries(PIESZE).map(([k, r]) => `<button type="button" role="radio" data-pt="${k}" aria-checked="${k === ST.PT}">${r.n}</button>`).join('')}</div>` : `<div class="rower" role="radiogroup" aria-label="Rodzaj roweru">${Object.entries(ROWERY).map(([k, r]) => `<button type="button" role="radio" data-r="${k}" aria-checked="${k === ST.RT}">${r.n}</button>`).join('')}</div>`}
      <div class="msg ostrz" id="p-ostrz"${ostrzezenie(T, inne) ? '' : ' hidden'}>${esc(ostrzezenie(T, inne))}</div>
      <div class="pogoda" id="p-pog"></div>
      <div class="tempo"><div class="tnag"><span>Twoje tempo na płaskim</span><b id="p-v">${vOpis(ST.VU)} · ${tempoNazwa(ST.VU)}</b></div>
        ${ST.pieszo ? `<input type="range" id="p-tempo" min="${ST.R.od}" max="${ST.R.do}" step="${ST.R.krok}" value="${ST.VU}" aria-label="Twoje tempo (km/h)">
        <div class="tskala">${(ST.PT === 'bieg' ? ['trucht', 'bieg', 'szybki bieg'] : ST.PT === 'nordic' ? ['spokojnie', 'marsz', 'szybko'] : ['spacerowo', 'marsz', 'szybki marsz']).map(x => `<span>${x}</span>`).join('')}</div>` : `<input type="range" id="p-tempo" min="8" max="40" step="1" value="${ST.VU}" aria-label="Twoja średnia prędkość na płaskim (km/h)">
        <div class="tskala"><span>spacerowo</span><span>rekreacyjnie</span><span>sportowo</span><span>wyczynowo</span></div>`}</div>
      <div class="tempo oszcz"><label><input type="checkbox" id="p-oszcz"${LS.get('oszcz', false) ? ' checked' : ''}> <b>Oszczędzanie baterii</b><span>ekran może zgasnąć – prowadzi głos, GPS rzadziej na prostych</span></label>
        <button type="button" class="moff-b" id="p-glostest">Test głosu</button></div>
      ${wykresBlok(T)}
      <div class="msg">${T.km.trasy > 100 ? `Trasami HUB-u: ${kmTxt(T.km.trasy)}. ` : ''}${T.km.dw > 50 ? `Po drogach wojewódzkich i krajowych: ${kmTxt(T.km.dw)}.` : 'Bez dróg wojewódzkich i krajowych.'}</div>
      <button type="button" class="btn" id="b-jedz">${strzalkaSVG('prosto', '#fff', 22)}${ST.pieszo ? (ST.PT === 'bieg' ? 'Biegnij' : 'Idź') : 'Jedź'}</button>
      <div class="rzad"><a class="btn2" id="b-google" target="_blank" rel="noopener" style="text-decoration:none;color:inherit">Mapy Google</a>${NAT ? '' : '<button type="button" class="btn2" id="b-gpx">GPX</button>'}</div>
      <button type="button" class="btn2" id="b-symstart" style="border-style:dashed">Symulacja przejazdu (test w domu)</button>
      <div class="sek">Po drodze</div><div class="manew">${lista}</div>
      <div class="moff p-off" id="p-offline"${JZ.podklad.pobrana() ? ' hidden' : ''}><span>Jedziesz przez las albo tam, gdzie słaby zasięg? <button type="button" class="moff-b" id="p-offline-b">Pobierz mapę offline (ok. 8 MB)</button></span></div>
      <button type="button" class="btn2" id="b-zglos" style="border-style:dashed">Coś nie tak z tą trasą? Zgłoś błąd / sugestię</button>`;
    $('dol').querySelectorAll('.tryb:not(.pr) button').forEach(b => b.onclick = () => { stan.tryb = b.dataset.t; if (b.dataset.t !== 'pieszo') LS.set('tryb', stan.tryb); podglad(); });
    // zmiana roweru: tylko czas jazdy (prędkości na nawierzchniach, podjazdy, vmax) – trasa i suwak tempa bez zmian
    $('dol').querySelectorAll('.rower button[data-pt]').forEach(b => b.onclick = () => {   // spacer / nordic walking / bieg – inne tempo
      ST.PT = b.dataset.pt; LS.set('piesze', ST.PT); ustawPieszo(true); const y = $('dol').scrollTop; podglad(); $('dol').scrollTop = y; });
    $('dol').querySelectorAll('.rower button[data-r]').forEach(b => b.onclick = () => {
      const zSzosy = ST.RT === 'szosa'; ST.RT = b.dataset.r; ST.R = ROWERY[ST.RT]; LS.set('rower', ST.RT);
      // szosówka: od razu tryb „Szosowa”; przesiadka z szosówki – z trybu szosowego wracamy do „Bezpieczna”
      if (ST.RT === 'szosa' || (zSzosy && stan.tryb === 'szosa')) { stan.tryb = ST.RT === 'szosa' ? 'szosa' : 'bezp'; LS.set('tryb', stan.tryb); const y = $('dol').scrollTop; podglad(); $('dol').scrollTop = y; return; }
      if (zSzosy) { const y = $('dol').scrollTop; podglad(); $('dol').scrollTop = y; return; }   // znika trzeci przycisk trybu
      T.prof = profil(T);
      $('dol').querySelectorAll('.rower button').forEach(x => x.setAttribute('aria-checked', x === b));
      $('p-czas').textContent = czasTxt(T.prof.czas); wykresInterakcja(T); slOdswiez(T);
      const o = ostrzezenie(T, inne); $('p-ostrz').textContent = o; $('p-ostrz').hidden = !o;
    });
    $('b-jedz').onclick = () => startJazdy(false);
    if (JZ.pogoda) JZ.pogoda.blok($('p-pog'), T);   // pogoda na starcie, po drodze i na miejscu + wschód/zachód słońca
    // rowerem / pieszo: inny sposób liczenia trasy (pieszo: ścieżki i las, nawierzchnia bez znaczenia) i osobne tempo
    $('dol').querySelectorAll('.tryb.pr button').forEach(b => b.onclick = () => { if ((b.dataset.p === '1') === ST.pieszo) return;
      ustawPieszo(b.dataset.p === '1'); stan.tryb = ST.pieszo ? 'pieszo' : (LS.get('tryb', 'bezp') === 'pieszo' ? 'bezp' : LS.get('tryb', 'bezp')); const y = $('dol').scrollTop; podglad(); $('dol').scrollTop = y; });
    $('p-oszcz').onchange = e => LS.set('oszcz', e.target.checked);
    $('p-glostest').onclick = () => { if (!stan.glos) { stan.glos = true; LS.set('glos', true); } powiedz('Test głosu. Za 100 metrów skręć w prawo.', true); };
    $('b-zglos').onclick = () => zglos(true);
    if ($('b-alt')) $('b-alt').onclick = () => wybierzAlt(alt);
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
    dopasuj(); const roz = map.getSize();
    setTimeout(() => { const r = map.getSize(); map.invalidateSize({pan: false}); if (!map.getSize().equals(roz) || !r.equals(roz)) dopasuj(); }, 150);   // drugi raz tylko, gdy zmienił się rozmiar
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
  let zegarJ = null;
  let watch = null, sym = null, symV = 1, wake = null, poza = 0, ostPrzel = 0, idx = 0, wzdluz = 0, ostPoz = null, zapowiedz = new Set(), kierPokaz = null;
  // ekran włączony w czasie jazdy – chyba że wybrano „Oszczędzanie baterii” (wtedy prowadzi głos, ekran gaśnie jak zwykle)
  async function budzik() { if (LS.get('oszcz', false)) return; try { if ('wakeLock' in navigator) { wake = await navigator.wakeLock.request('screen'); } } catch (e) {} }
  document.addEventListener('visibilitychange', () => { if (stan.jazda && document.visibilityState === 'visible') budzik(); });
  // ---- mapa obrócona „kierunkiem jazdy do góry”: kontener mapy to kwadrat o boku = przekątnej ekranu,
  //      środek kwadratu (= Twoja pozycja) w 62% wysokości ekranu, obrót CSS wokół środka
  let obrocona = false, B = 0, kurs = LS.get('kurs', true), tilt = LS.get('tilt', false);
  // 3D: obrócona mapa dodatkowo pochylona jak kartka na stole (perspektywa CSS); kontener większy, żeby pokryć „dal”
  const KROTNOSC_3D = +(new URLSearchParams(location.search).get('k3d') || 1.9);   // rozmiar mapy w 3D względem przekątnej ekranu
  const tr = () => tilt && obrocona ? `perspective(${Math.round($('s-mapa').clientHeight * 1.1)}px) rotateX(48deg) rotate(${-B}deg)` : `rotate(${-B}deg)`;
  // przestawianie mapy przez apkę (pozycja GPS, start jazdy) – zawsze bez animacji, a w trakcie przybliżania palcami / animacji
  // przybliżania czekamy do jej końca: wcześniej kolejna pozycja GPS przerywała animację i trasa (SVG) zostawała w złej skali
  let czekaWidok = null;
  function widok(p, z) {
    if (map._animatingZoom || (map.touchZoom && map.touchZoom._zooming)) { czekaWidok = [p, z]; return; }
    map.setView(p, z ?? map.getZoom(), {animate: false});
  }
  function obroc(on) {
    const el = $('mapa'), box = $('s-mapa'), w = box.clientWidth, h = box.clientHeight;
    obrocona = on;
    map.options.touchZoom = map.options.doubleClickZoom = map.options.scrollWheelZoom = on ? 'center' : true;
    if (on) { const D = Math.ceil(Math.hypot(w, h) * (tilt ? KROTNOSC_3D : 1)) + 4, ay = Math.round(h * (tilt ? .7 : .62)); el.style.cssText = `inset:auto;left:${Math.round((w - D) / 2)}px;top:${ay - Math.round(D / 2)}px;width:${D}px;height:${D}px;transition:transform .6s linear`; el.style.transform = tr(); map.dragging.disable(); }
    else { el.style.cssText = ''; map.dragging.enable(); }
    map.invalidateSize({pan: false}); if (jaM && sledz) widok(jaM.getLatLng());
    kompas();
  }
  function kompas() { $('b-kurs').innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24" aria-hidden="true" style="transform:rotate(${obrocona ? -B : 0}deg);transition:transform .6s linear"><path d="M12 2l4 10h-8z" fill="#d62828"/><path d="M12 22l-4-10h8z" fill="#9aa3a8"/><text x="12" y="9.5" text-anchor="middle" font-size="5" font-weight="800" fill="#fff" font-family="Inter,Arial">N</text></svg>`;
    $('b-kurs').ariaLabel = obrocona ? 'Odblokuj: północ u góry' : 'Zablokuj: kierunek jazdy u góry';
    $('b-kurs').style.background = obrocona ? '#00737e' : '#fff'; $('b-kurs').style.boxShadow = obrocona ? '0 0 0 3px #fff, 0 1px 6px rgba(0,0,0,.3)' : '';
    $('b-kurs').querySelector('svg path:last-of-type').setAttribute('fill', obrocona ? '#cfe6e6' : '#9aa3a8'); }
  let pogT = 0;
  function startJazdy(symulacja) {
    stan.jazda = true; idx = 0; wzdluz = 0; poza = 0; pytano.clear(); Object.assign(tempo, {real: 0, mod: 0, t: 0, v: 0, k: 1}); zapowiedz = new Set(); kierPokaz = null; sledz = true;
    sym = symulacja ? {d: 0} : null; panele('jazda'); glosIkona(); budzik();
    if (!symulacja) powiedz('Ruszamy. Do celu ' + kmTxt(stan.T.m) + '.');
    if (!symulacja) JZ.historia.start({cel: stan.celN, tryb: stan.tryb, rower: ST.pieszo ? (ST.PT === 'spacer' ? 'pieszo' : ST.PT) : ST.RT});   // zapis przejazdu (tylko w telefonie)
    $('dol').innerHTML = `<div class="jdol"><div class="w"><b id="j-zost"></b><small id="j-opis"></small><small id="j-pog"></small></div><button type="button" class="stop" id="b-stop">Zakończ</button></div>`;
    $('b-stop').onclick = koniecJazdy;
    widok(stan.T.ll[0], 17); B = brg(stan.T.ll[0], wDal(stan.T, 40)); if (kurs) obroc(true); else kompas();
    $('b-kurs').classList.remove('hide'); $('b-3d').classList.remove('hide'); trojwymiar();
    if (!sym) pozycja(stan.start, 20, true);
    if (sym) { symV = 1; $('b-sym').textContent = 'Symulacja: ×1'; sym.t = setInterval(() => { sym.d += 6 * symV; const p = wDal(stan.T, sym.d); pozycja(p, 5, sym.d); }, 1000); }
    // zegar: co 5 s odśwież czas i godzinę przyjazdu także na postoju (GPS bez ruchu nie przysyła nowych pozycji) – stoisz,
    // więc godzina przyjazdu przesuwa się do przodu, a prędkość spada do zera
    clearInterval(zegarJ); zegarJ = setInterval(() => { if (!stan.jazda) return clearInterval(zegarJ); if (Date.now() - (tempo.t || 0) > 6000) tempo.v = 0; odswiez(); }, 5000);
    // pogoda w trakcie jazdy: co 5 min (prognoza w pamięci 30 min, więc pobieranie rzadko) (deszcz za ~30 min, zmrok); głosowo raz – 20 min przed zachodem, gdy do celu dalej
    clearInterval(pogT); let zachG = false;
    const pog = () => { if (!stan.jazda || !JZ.pogoda) return clearInterval(pogT); JZ.pogoda.wJezdzie(stan.T, wzdluz).then(r => { const e = $('j-pog'); if (e) e.textContent = r.txt ? ' · ' + r.txt : '';
      if (r.zach && !zachG) { const za = r.zach.getTime() - Date.now(); if (za > 0 && za < 20 * 6e4) { zachG = true; powiedz('Za ' + Math.round(za / 6e4) + ' minut zachód słońca. Włącz światła.'); } } }); };
    pogT = setInterval(pog, 5 * 6e4); setTimeout(pog, 3000);
    if (!sym) watch = GEO.sledz((p, acc) => pozycja(p, acc), () => { $('status').className = 'status zle'; $('status').querySelector('span').textContent = 'Brak sygnału GPS'; }, 'Do: ' + stan.celN);
    odswiez();
  }
  $('b-sym').onclick = () => { symV = symV === 1 ? 3 : symV === 3 ? 8 : 1; $('b-sym').textContent = 'Symulacja: ×' + symV; };
  // komunikat po zapisaniu przejazdu (na górze panelu)
  function pokazZapis(z) {
    if (!z) return; const d = document.createElement('div'); d.className = 'hzap';
    d.innerHTML = `Zapisano przejazd: <b>${esc(JZ.historia.opis(z))}</b> · <a href="#" id="zap-hist">Moje przejazdy</a>`;
    $('dol').prepend(d); $('zap-hist').onclick = e => { e.preventDefault(); przejazdy(); };
  }

  // ===================== ocena dróg z nawigacji: w trakcie jazdy (gwiazdka) i po przejeździe =====================
  // Oceny trafiają do moderacji jak z mapy wspólnej (api/zglos.php). Bez zasięgu czekają w kolejce w telefonie i wysyłają się później.
  const OC4 = [['dobra', '👍', 'Dobra', '#1E6B3A'], ['srednia', '😐', 'Średnia', '#B96516'], ['trudna', '👎', 'Trudna', '#902B38'], ['nieprzejezdna', '⛔', 'Nieprzejezdna', '#3a3a3a']];
  const opisOdc = s => (s[2] ? s[2] + ' · ' : '') + s[1] + (s[3] ? ', ' + s[3] : '');
  // „odcinek do oceny” = ciąg kolejnych kawałków trasy tej samej drogi (ta sama nazwa i rodzaj)
  function grupaOdc(T, i) {
    const s = T.seg[i]; if (!s) return null; const kl = x => x ? x[1] + '|' + x[2] : '';
    let a = i, b = i; while (a > 0 && kl(T.seg[a - 1]) === kl(s)) a--; while (b < T.seg.length - 1 && kl(T.seg[b + 1]) === kl(s)) b++;
    const ll = []; for (let k = a; k <= b + 1 && k < T.ll.length; k++) ll.push(T.ll[k]);
    return {a, b, ids: [...new Set(T.seg.slice(a, b + 1).filter(Boolean).map(x => x[0]))], m: T.cum[b + 1] - T.cum[a], s, ll};
  }
  // odcinek w dotychczasowym obszarze (gmina z okolicą)? – tylko tam zbieramy oceny (stan/rdzen.js; bez pliku – wszędzie)
  const RDZC = new Map();
  const wRdz = s => { if (!s || !window.wRdzeniu) return true; if (!RDZC.has(s[0])) RDZC.set(s[0], wRdzeniu(s[7][0], s[7][1])); return RDZC.get(s[0]); };
  function kawalekOdc(T, d) {
    let i = 0; while (i < T.seg.length - 1 && T.cum[i + 1] < d) i++;
    if (!T.seg[i]) { i = Math.min(i + 1, T.seg.length - 1); if (!T.seg[i]) return null; }
    const id0 = T.seg[i][0]; let a = i, b = i;
    while (a > 0 && T.seg[a - 1] && (T.seg[a - 1][0] === id0 || T.cum[a] > d - 100) && T.seg[a - 1][2] === T.seg[i][2]) a--;
    while (b < T.seg.length - 1 && T.seg[b + 1] && (T.seg[b + 1][0] === id0 || T.cum[b + 1] < d + 100) && T.seg[b + 1][2] === T.seg[i][2]) b++;
    const ll = []; for (let k = a; k <= b + 1 && k < T.ll.length; k++) ll.push(T.ll[k]);
    return {a, b, ids: [...new Set(T.seg.slice(a, b + 1).filter(Boolean).map(x => x[0]))], m: T.cum[b + 1] - T.cum[a], s: T.seg[i], ll};
  }
  function wyslijOceny() {
    const K = LS.get('kolejkaOcen', []); if (!K.length || !navigator.onLine) return;
    const st = K[0].stan, paczka = K.filter(k => k.stan === st), ids = [...new Set(paczka.flatMap(k => k.ids))].slice(0, 300);
    fetch(BAZA + 'api/zglos.php', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
      stan: st, odcinki: ids, nick: LS.get('nick', '') || 'Jedź', komentarz: 'Ocena z nawigacji Jedź' + (NAT ? ' (aplikacja)' : ''), data: new Date().toISOString().slice(0, 10), urz: (() => { try { let u = localStorage.getItem('hub_urz'); if (!/^[0-9a-f]{12}$/.test(u || '')) { u = Array.from(crypto.getRandomValues(new Uint8Array(6)), b => b.toString(16).padStart(2, '0')).join(''); localStorage.setItem('hub_urz', u); } return u; } catch (e) { return ''; } })()})})
      .then(r => r.json().catch(() => ({}))).then(j => { if (j.ban) LS.set('ban', {t: j.blad, do: j.ban});
        if (j.ok || j.ban || j.zewn || /Nieznany odcinek|Zaznacz od/.test(j.blad || '')) {
        LS.set('kolejkaOcen', LS.get('kolejkaOcen', []).filter(k => k.stan !== st)); setTimeout(wyslijOceny, 300); } }).catch(() => {});
  }
  // wysyłka po 10 s od ostatniego dotknięcia – zmiana zdania („średnia” → „trudna”) podmienia ocenę w kolejce, zamiast wysyłać kilka
  let ocT = 0;
  function dodajOcene(ids, st) { const K = LS.get('kolejkaOcen', []).filter(k => k.ids.join() !== ids.join()); K.push({ids, stan: st, t: Date.now()}); LS.set('kolejkaOcen', K);
    clearTimeout(ocT); ocT = setTimeout(wyslijOceny, 10000); }
  document.addEventListener('visibilitychange', () => { if (document.hidden && LS.get('kolejkaOcen', []).length) { clearTimeout(ocT); wyslijOceny(); } });
  window.addEventListener('online', wyslijOceny); setTimeout(wyslijOceny, 3000);
  let ocenaL = null;
  function podswietl(ll) { if (ocenaL) { ocenaL.remove(); ocenaL = null; } if (!map || !ll || ll.length < 2) return;
    ocenaL = L.layerGroup([L.polyline(ll, {color: '#ffd400', weight: 14, opacity: .75, interactive: false}), L.polyline(ll, {color: '#1d3b30', weight: 3, dashArray: '4 6', interactive: false})]).addTo(map); }
  function ocenaZamknij() { $('ocs').classList.add('hide'); if (ocenaL) { ocenaL.remove(); ocenaL = null; } }
  $('b-ocen').onclick = () => {
    const T = stan.T; if (!T) return;
    // w trakcie jazdy oceniamy tylko kawałek, na którym jesteś: odcinki mapy w promieniu ~100 m (odcinki mają do 400 m, zwykle ok. 100 m),
    // żeby 50 m piachu nie zepsuło oceny całej dobrej drogi
    const bn = LS.get('ban', null);   // jawna blokada z serwera: zamiast przycisków ocen – informacja, do kiedy
    if (bn && new Date(bn.do.replace(' ', 'T')) > new Date()) { $('ocs').innerHTML = `<h3>Oceny wstrzymane</h3><div class="o">${esc(bn.t)}</div><button type="button" class="an" id="oc-an">Zamknij</button>`; $('ocs').classList.remove('hide'); $('oc-an').onclick = ocenaZamknij; return; }
    let g = kawalekOdc(T, wzdluz);
    // 17.11.2026: nowe tereny mapy (poza gminą z okolicą) – nawigacja prowadzi, ale ocen jeszcze nie zbieramy
    if (g && !wRdz(g.s)) { $('ocs').innerHTML = `<h3>Tu jeszcze nie oceniamy</h3><div class="o">Oceny dróg zbieramy na razie w gminie Koszęcin i okolicy. Ta część mapy dopiero się rozwija – nawigacja prowadzi tu normalnie.</div><button type="button" class="an" id="oc-an">Zamknij</button>`; $('ocs').classList.remove('hide'); $('oc-an').onclick = ocenaZamknij; return; }
    if (!g) { $('ocs').innerHTML = `<h3>Tu nie ma odcinka do oceny</h3><div class="o">Ocenić można drogi z mapy – spróbuj za chwilę, gdy wjedziesz na drogę.</div><button type="button" class="an" id="oc-an">Zamknij</button>`; $('ocs').classList.remove('hide'); $('oc-an').onclick = ocenaZamknij; return; }
    podswietl(g.ll);
    $('ocs').innerHTML = `<h3>Jak się jedzie tym odcinkiem?</h3><div class="o">${esc(opisOdc(g.s))} · ${kmTxt(g.m)} (zaznaczony na żółto)</div>
      ${LS.get('nick', '') ? '' : '<input id="oc-nick" maxlength="60" placeholder="Twoje imię lub nick (raz, zapamiętam)" autocomplete="nickname">'}
      <div class="oc4">${OC4.map(([k, e, n, c]) => `<button type="button" data-k="${k}" style="background:${c}"><span>${e}</span>${n}</button>`).join('')}</div>
      <button type="button" class="an" id="oc-an">Anuluj</button>`;
    $('ocs').classList.remove('hide'); $('oc-an').onclick = ocenaZamknij;
    $('ocs').querySelectorAll('.oc4 button').forEach(b => b.onclick = () => {
      const n = $('oc-nick'); if (n && n.value.trim().length >= 2) LS.set('nick', n.value.trim());
      dodajOcene(g.ids, b.dataset.k); navigator.vibrate && navigator.vibrate(40);
      $('ocs').innerHTML = `<h3>Dziękujemy! 🙌</h3><div class="o">${navigator.onLine ? 'Ocena przyjęta – po sprawdzeniu trafi do nawigacji dla wszystkich.' : 'Ocena zapisana – wyślę ją, gdy będzie zasięg.'}</div>`;
      setTimeout(ocenaZamknij, 1800);
    });
  };
  // po przejeździe: 3 najdłuższe odcinki dróg nieutwardzonych / bez oceny (asfalt i drogi wojewódzkie na końcu) – jedno dotknięcie na odcinek
  function blokOcen(T, doM) {
    const gr = [], wazny = g => { const st = JZ.stOdc(g.s); return JZ.DW(g.s) ? 0 : st === 'osm' ? 1 : 2; };
    for (let i = 0; i < T.seg.length;) { const g = grupaOdc(T, i); if (!g) { i++; continue; } if (T.cum[g.a] < doM && g.m >= 150 && wRdz(g.s)) gr.push(g); i = g.b + 1; }
    const top = gr.sort((a, b) => wazny(b) - wazny(a) || b.m - a.m).slice(0, 3); if (!top.length) return null;
    const bn = LS.get('ban', null); if (bn && new Date(bn.do.replace(' ', 'T')) > new Date()) return null;
    const d = document.createElement('div'); d.className = 'ocpo';
    d.innerHTML = `<h4>Jak się jechało? Oceń drogi z tej trasy</h4>
      ${LS.get('nick', '') ? '' : '<input id="ocp-nick" maxlength="60" placeholder="Twoje imię lub nick (raz, zapamiętam)" style="width:100%;box-sizing:border-box;font:inherit;padding:8px 10px;border:1px solid #cfd8d3;border-radius:10px;margin-bottom:4px">'}
      ${top.map((g, i) => `<div class="ocw" data-i="${i}"><div class="t"><b>${esc(g.s[2] || g.s[1])}</b>${esc([g.s[2] ? g.s[1] : g.s[3], kmTxt(g.m)].filter(Boolean).join(' · '))}</div>
        <div class="bb">${OC4.map(([k, e, n]) => `<button type="button" data-k="${k}" title="${n}" aria-label="${n}">${e}</button>`).join('')}</div></div>`).join('')}
      <div class="m">Ocena dotyczy całej drogi – dotknij nazwy, żeby ją zobaczyć. Jeśli źle było tylko w jednym miejscu, następnym razem dotknij gwiazdki właśnie tam (oceni ok. 200 m wokół Ciebie).</div>`;
    d.querySelectorAll('.ocw').forEach(w => { const g = top[+w.dataset.i];
      w.querySelector('.t').onclick = () => { podswietl(g.ll); if (map) map.fitBounds(L.latLngBounds(g.ll), {padding: [40, 40], maxZoom: 16}); };
      w.querySelectorAll('.bb button').forEach(b => b.onclick = () => {
        const n = $('ocp-nick'); if (n && n.value.trim().length >= 2) LS.set('nick', n.value.trim());
        w.querySelectorAll('.bb button').forEach(x => x.classList.toggle('on', x === b)); dodajOcene(g.ids, b.dataset.k);
        d.querySelector('.m').textContent = navigator.onLine ? 'Dziękujemy! Oceny wysłane do sprawdzenia.' : 'Dziękujemy! Wyślę oceny, gdy będzie zasięg.'; }); });
    return d;
  }
  // ===================== moje przejazdy (historia i statystyki – tylko w telefonie) =====================
  const dataTxt = t => new Date(t).toLocaleDateString('pl-PL', {day: 'numeric', month: 'short'}) + ', ' + new Date(t).toLocaleTimeString('pl-PL', {hour: '2-digit', minute: '2-digit'});
  function przejazdy() {
    ekran('s-mapa'); mapa(); panele('podglad'); warstwa.clearLayers(); $('gora').innerHTML = '';
    const HI = JZ.historia, a = HI.lista(), st = HI.statystyki();
    const bb = []; a.slice(0, 20).forEach(z => { const s = HI.slad(z); if (s.length > 1) { L.polyline(s, {color: '#7b3fa0', weight: 3, opacity: .35, interactive: false}).addTo(warstwa); bb.push(...s); } });
    if (bb.length) map.fitBounds(L.latLngBounds(bb), {padding: [30, 30], paddingBottomRight: [20, window.innerHeight * .5]});
    $('dol').innerHTML = `<div class="uchwyt"></div><div style="font-size:20px;font-weight:800">Moje przejazdy</div>
      ${a.length ? `<div class="hstat"><div><b>${kmTxt(st.km)}</b><span>razem · ${st.n} przejazd${st.n === 1 ? '' : st.n < 5 ? 'y' : 'ów'}</span></div>
        <div><b>${kmTxt(st.kmMies)}</b><span>w tym miesiącu</span></div><div><b>${HI.czasTxtD(st.ruch)}</b><span>w ruchu</span></div></div>
        <div class="msg">Najdłuższy: ${kmTxt(st.najdl)}${st.vmax ? ' · najszybciej: ' + String(st.vmax).replace('.', ',') + ' km/h' : ''}</div>
        <div class="hlista">${a.map(z => `<button type="button" class="hpoz" data-id="${z.id}"><span><b>${esc(z.cel ? '→ ' + z.cel : z.tryb === 'nagranie' ? 'Nagrana trasa' : 'Przejazd')}</b><small>${dataTxt(z.data)} · ${esc(HI.opis(z))}</small></span><span aria-hidden="true">›</span></button>`).join('')}</div>
        <button type="button" class="btn2" id="h-czysc" style="border-style:dashed">Usuń całą historię</button>`
      : `<p class="msg">Nie masz jeszcze zapisanych przejazdów. Każda nawigacja dłuższa niż 200 m zapisze się tutaj sama – z trasą, czasem i prędkością.</p>`}
      <p class="msg" style="font-size:12px">Historia jest zapisana tylko w tym telefonie – nie wysyłamy jej nigdzie.</p>`;
    $('dol').querySelectorAll('.hpoz').forEach(b => b.onclick = () => przejazd(a.find(z => z.id === +b.dataset.id)));
    if ($('h-czysc')) $('h-czysc').onclick = () => { if (confirm('Usunąć wszystkie zapisane przejazdy z tego telefonu?')) { HI.wyczysc(); przejazdy(); } };
  }
  function przejazd(z) {
    const HI = JZ.historia, s = HI.slad(z); warstwa.clearLayers();
    if (s.length > 1) { L.polyline(s, {color: '#fff', weight: 9, opacity: .9}).addTo(warstwa); L.polyline(s, {color: '#7b3fa0', weight: 5}).addTo(warstwa);
      L.circleMarker(s[0], {radius: 7, color: '#fff', weight: 3, fillColor: '#2b9348', fillOpacity: 1}).addTo(warstwa);
      L.circleMarker(s[s.length - 1], {radius: 7, color: '#fff', weight: 3, fillColor: '#b00020', fillOpacity: 1}).addTo(warstwa);
      map.fitBounds(L.latLngBounds(s), {paddingTopLeft: [20, 70], paddingBottomRight: [20, Math.min(window.innerHeight * .5, 380)]}); }
    const sr = HI.sredniaKmh(z), R0 = ROWERY[z.rower];
    $('dol').innerHTML = `<div class="uchwyt"></div><div class="msg">${dataTxt(z.data)}</div><div style="font-size:20px;font-weight:800">${esc(z.cel ? '→ ' + z.cel : z.tryb === 'nagranie' ? 'Nagrana trasa' : 'Przejazd')}</div>
      <div class="hstat"><div><b>${kmTxt(z.km)}</b><span>przejechane</span></div><div><b>${HI.czasTxtD(z.ruch || z.czas)}</b><span>w ruchu (razem ${HI.czasTxtD(z.czas)})</span></div>
        <div><b>${sr ? sr.toFixed(1).replace('.', ',') : '–'}</b><span>śr. km/h${z.vmax ? ' · max ' + String(z.vmax).replace('.', ',') : ''}</span></div></div>
      <div class="msg">${z.rower === 'pieszo' ? 'Pieszo · ' : z.rower === 'nordic' ? 'Nordic walking · ' : z.rower === 'bieg' ? 'Bieg · ' : R0 ? 'Rower: ' + R0.n.toLowerCase() + ' · ' : ''}${z.tryb && z.tryb !== 'nagranie' ? 'trasa: ' + (TRYBY[z.tryb] || z.tryb) : z.tryb === 'nagranie' ? 'nagrana bez nawigacji' : ''}</div>
      <div style="display:flex;gap:8px">${NAT ? '' : `<a class="btn2" id="h-gpx" style="flex:1;text-decoration:none;color:inherit;text-align:center" download="przejazd-${new Date(z.data).toISOString().slice(0, 10)}.gpx">Pobierz GPX</a>`}
        <button type="button" class="btn2" id="h-usun" style="flex:1">Usuń</button></div>
      <button type="button" class="btn2" id="h-lista">← Wszystkie przejazdy</button>`;
    if ($('h-gpx')) $('h-gpx').href = URL.createObjectURL(new Blob([HI.gpx(z)], {type: 'application/gpx+xml'}));
    $('h-usun').onclick = () => { if (confirm('Usunąć ten przejazd?')) { HI.usun(z.id); przejazdy(); } };
    $('h-lista').onclick = przejazdy;
  }
  $('b-hist').onclick = przejazdy;
  // ===================== nagrywanie trasy bez celu (tracking): ślad, dystans, czas, tempo – zapis w „Moich przejazdach” =====================
  let nagr = null;
  $('b-nagraj').onclick = () => {
    if (stan.jazda || nagr) return;
    ekran('s-mapa'); mapa(); panele('jazda'); $('b-glos').classList.add('hide'); $('b-ocen').classList.add('hide'); $('status').classList.add('hide'); warstwa.clearLayers(); $('gora').innerHTML = '';
    const rodz = ST.pieszo ? (ST.PT === 'spacer' ? 'pieszo' : ST.PT) : ST.RT;
    JZ.historia.start({cel: '', tryb: 'nagranie', rower: rodz}); budzik();
    nagr = {pauza: false, linia: L.polyline([], {color: '#7b3fa0', weight: 5}).addTo(warstwa), ost: null, v: 0, tv: 0, pauzaOd: 0, pauzaS: 0};
    $('dol').innerHTML = `<div class="uchwyt"></div><div class="ndol"><div class="nrec" id="n-rec"><i></i><span>Nagrywam trasę</span></div>
      <div class="nst"><div><b id="n-km">0 m</b><span>dystans</span></div><div><b id="n-czas">0:00</b><span>czas</span></div>
        <div><b id="n-v">–</b><span>${ST.pieszo && ST.PT === 'bieg' ? 'tempo teraz (min/km)' : 'prędkość teraz (km/h)'}</span></div><div><b id="n-sr">–</b><span>${ST.pieszo && ST.PT === 'bieg' ? 'średnie tempo (min/km)' : 'średnio w ruchu (km/h)'}</span></div></div>
      <div class="nrz"><button type="button" class="btn2" id="n-pauza">Pauza</button><button type="button" class="stop" id="n-stop">Zakończ i zapisz</button></div>
      <div class="msg">Ślad zostaje tylko w Twoim telefonie (Moje przejazdy, eksport GPX).</div></div>`;
    const tempoTxt = kmh => kmh > 0.5 ? (ST.pieszo && ST.PT === 'bieg' ? `${Math.floor(60 / kmh)}:${String(Math.round(3600 / kmh) % 60).padStart(2, '0')}` : kmh.toFixed(1).replace('.', ',')) : '–';
    const odswiezN = () => { if (!nagr) return; const b = JZ.historia.biezacy(); if (!b) return;
      const s = Math.round((Date.now() - b.t0) / 1000) - nagr.pauzaS - (nagr.pauza ? Math.round((Date.now() - nagr.pauzaOd) / 1000) : 0);
      $('n-km').textContent = kmTxt(b.km); $('n-czas').textContent = Math.floor(s / 3600) ? `${Math.floor(s / 3600)}:${String(Math.floor(s / 60) % 60).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}` : `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
      if (Date.now() - nagr.tv > 6000) nagr.v = 0;
      $('n-v').textContent = tempoTxt(nagr.v * 3.6); $('n-sr').textContent = b.ruch > 20 ? tempoTxt(b.km / b.ruch * 3.6) : '–'; };
    nagr.zegar = setInterval(odswiezN, 1000);
    nagr.watch = GEO.sledz((p, acc) => {
      if (!nagr || (acc && acc > 35)) return; const t = Date.now();
      if (!nagr.pauza) $('n-rec').querySelector('span').textContent = 'Nagrywam trasę';
      if (nagr.ost) { const d = dist(nagr.ost.p, p), dt = (t - nagr.ost.t) / 1000; if (d > 3 && dt > 0 && d / dt < 25) { nagr.v = d / dt; nagr.tv = t; } }
      const rot = nagr.ost && dist(nagr.ost.p, p) > 3 ? brg(nagr.ost.p, p) : (nagr.rot || 0); nagr.rot = rot; nagr.ost = {p, t};
      const ik = L.divIcon({className: '', html: `<svg class="ja" viewBox="0 0 30 30" style="transform:rotate(${rot}deg)"><circle cx="15" cy="15" r="13" fill="#1d4ed8" stroke="#fff" stroke-width="3"/><path d="M15 7l6 13-6-3-6 3z" fill="#fff"/></svg>`, iconSize: [30, 30], iconAnchor: [15, 15]});
      if (!jaM) jaM = L.marker(p, {icon: ik, interactive: false, zIndexOffset: 1000}).addTo(map); else { jaM.setLatLng(p); jaM.setIcon(ik); }
      widok(p, Math.max(map.getZoom(), 16));
      if (nagr.pauza) return;
      JZ.historia.punkt(p, acc); nagr.linia.addLatLng(p); odswiezN();
    }, () => { $('n-rec').querySelector('span').textContent = 'Brak sygnału GPS – czekam…'; }, 'Nagrywanie trasy');
    $('n-pauza').onclick = () => { nagr.pauza = !nagr.pauza; $('n-pauza').textContent = nagr.pauza ? 'Wznów' : 'Pauza';
      $('n-rec').classList.toggle('p', nagr.pauza); $('n-rec').querySelector('span').textContent = nagr.pauza ? 'Pauza' : 'Nagrywam trasę';
      if (nagr.pauza) nagr.pauzaOd = Date.now(); else { nagr.pauzaS += Math.round((Date.now() - nagr.pauzaOd) / 1000); JZ.historia.wznow(); } };
    $('n-stop').onclick = () => {
      clearInterval(nagr.zegar); if (nagr.watch) nagr.watch(); nagr = null; try { wake && wake.release(); } catch (e) {} wake = null;
      if (jaM) { jaM.remove(); jaM = null; } $('status').classList.remove('hide'); panele('podglad');
      const z = JZ.historia.koniec();
      if (z) przejazd(z); else { ekran('s-cel'); $('msg-cel').textContent = 'Nagranie było krótsze niż 200 m – nie zapisano.'; }
    };
  };
  function koniecJazdy() {
    stan.jazda = false; clearInterval(zegarJ); if (watch) watch(); watch = null;
    if (sym) clearInterval(sym.t); sym = null; try { wake && wake.release(); } catch (e) {} wake = null;
    // po zakończeniu start = miejsce, w którym jesteś teraz (a nie to, skąd ruszyłeś) – podgląd pokazuje resztę drogi od Ciebie
    if (jaM) { const q = jaM.getLatLng(); stan.start = [q.lat, q.lng]; stan.startGPS = true; opiszStart(); jaM.remove(); jaM = null; }
    if (obrocona) obroc(false); $('b-kurs').classList.add('hide'); $('b-3d').classList.add('hide'); ekran('s-mapa'); window.speechSynthesis && speechSynthesis.cancel(); const zap = JZ.historia.koniec(); const doM = wzdluz, T0 = stan.T; podglad(); pokazZapis(zap);
    if (!sym && doM > 500) { const bo = blokOcen(T0, doM); if (bo) $('dol').querySelector('.uchwyt').after(bo); }
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
    if (!wSym) JZ.historia.punkt(p, acc);
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
      widok(p);
    } else if (sledz) { if (map._animatingZoom || (map.touchZoom && map.touchZoom._zooming)) czekaWidok = [p, null]; else map.panTo(p, {animate: true, duration: .5}); }
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
    if (!dt || dt > 30 || w2 <= w1) { tempo.v *= dt > 3 ? .3 : .6; return; }   // stoisz – prędkość szybko spada
    const v = (w2 - w1) / dt; if (v > 20) return;                 // skok GPS (ponad 70 km/h) – pomijamy
    tempo.v = tempo.v ? tempo.v * .6 + v * .4 : v;
    if (v < 0.8) return;                                   // stoisz / prowadzisz rower – nie liczymy
    tempo.real += dt; tempo.mod += czasDo(stan.T, w2) - czasDo(stan.T, w1);
    tempo.k = Math.max(0.6, Math.min(2, (tempo.real + 120) / (tempo.mod + 120)));
  }
  // ===================== objazd trudnego odcinka (w trakcie jazdy) =====================
  // co ~8 s patrzymy 60–700 m przed siebie: jeśli zaczyna się tam droga trudna dłuższa niż 200 m, liczymy trasę omijającą ją
  // (kara ×20) i – gdy omija większość, a nadkłada rozsądnie – proponujemy objazd. O ten sam odcinek pytamy raz.
  let objazdT = 0; const pytano = new Set();
  function sprawdzObjazd() {
    const ban = $('objazd');
    if (ban) { if (wzdluz > +ban.dataset.od) ban.remove(); return; }
    if (Date.now() - objazdT < 8000) return; objazdT = Date.now();
    const T = stan.T, ids = new Map(); let od = -1, L0 = 0, przerwa = 0;
    for (let i = Math.max(0, idx - 1); i < T.seg.length; i++) {
      const a = T.cum[i], b = T.cum[i + 1]; if (b < wzdluz + 60) continue; if (od < 0 && a > wzdluz + 700) break;
      const st = JZ.stOdc(T.seg[i]);
      if (st === 'trudna' || st === 'nieprzejezdna') { if (od < 0) od = a; L0 += b - a; ids.set(T.seg[i][0], 20); przerwa = 0; }
      else if (od >= 0) { przerwa += b - a; if (przerwa > 40) break; }
    }
    if (od < 0 || L0 < 200) return;
    const k = [...ids.keys()].sort().join(','); if (pytano.has(k)) return; pytano.add(k);
    const p = jaM ? [jaM.getLatLng().lat, jaM.getLatLng().lng] : wDal(T, wzdluz);
    const A = trasuj(p, stan.cel, {tryb: stan.tryb, kara: ids}); if (A.blad) return;
    const PA = JZ.podsumuj(A); let zost = 0; for (const id of ids.keys()) zost += PA.ids.get(id) || 0;
    const extra = A.m - (T.m - wzdluz);
    if (L0 - zost < L0 * 0.7 || extra > Math.max(1200, L0 * 1.5)) return;   // objazd nic nie daje albo jest za długi
    const d = document.createElement('div'); d.id = 'objazd'; d.className = 'objazd'; d.dataset.od = od;
    d.innerHTML = `<div><b>Za ${kmTxt(od - wzdluz)} droga trudna (${kmTxt(L0)})</b><span>Objazd: ${extra >= 0 ? '+' : '−'}${kmTxt(Math.abs(extra))}${zost > 20 ? `, zostaje ${kmTxt(zost)} trudnej` : ''}</span></div>
      <button type="button" class="ok" id="obj-tak">Objazd</button><button type="button" id="obj-nie">Zostaję</button>`;
    $('dol').prepend(d);
    powiedz(`Za ${Math.round((od - wzdluz) / 50) * 50} metrów zaczyna się trudna droga. Możesz ją objechać, ${extra > 0 ? Math.round(extra / 50) * 50 + ' metrów dłużej' : 'nawet krócej'}.`);
    $('obj-tak').onclick = () => { stan.objazd = {klucz: klucz(), ids}; d.remove(); przelicz(p); };
    $('obj-nie').onclick = () => d.remove();
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
    sprawdzObjazd();
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
    $('k-opis').textContent = kol.length ? 'Kolorowe kółka na tabliczce to numery tras HUB-u – możesz się ich trzymać dalej.' : '';
    const i = M.indexOf(m), dalej = M[i + 1];
    $('k-potem').innerHTML = dalej ? `<b>Potem:</b> ${esc(mTekst(dalej))} · za ${kmTxt(dalej.c - m.c)}` : '';
    ekran('s-kier');
  }
  function dojechales() {
    if (!stan.jazda) return;
    powiedz('Jesteś na miejscu'); navigator.vibrate && navigator.vibrate([100, 80, 100, 80, 200]);
    if (watch) watch(); watch = null; if (sym) clearInterval(sym.t); sym = null;
    stan.jazda = false; clearInterval(zegarJ); try { wake && wake.release(); } catch (e) {}
    const zap = JZ.historia.koniec(); setTimeout(() => pokazZapis(zap), 0);
    if (obrocona) obroc(false); $('b-kurs').classList.add('hide'); $('b-3d').classList.add('hide'); ekran('s-mapa'); panele('podglad');
    $("gora").innerHTML = `<div class="pasek" style="padding-left:76px"><div class="r1"><div class="strz">${strzalkaSVG("cel", "#1d3b30", 40)}</div><div><div class="lab">Jesteś na miejscu</div><div class="co">${esc(stan.celN)}</div></div></div></div>`; $('gora').dataset.h = '';
    $('dol').innerHTML = `<div class="uchwyt"></div><div style="font-size:20px;font-weight:800">Dojechałeś! ${kmTxt(stan.T.m)}</div><p class="msg">Każda ocena drogi poprawia trasy dla wszystkich.</p><div class="rzad"><a class="btn2" href="${BAZA}#wspolna" style="text-decoration:none;color:inherit">Mapa wspólna</a><button type="button" class="btn2" id="b-nowy">Nowy cel</button></div>`;
    $('b-nowy').onclick = () => { stan.start = jaM ? [jaM.getLatLng().lat, jaM.getLatLng().lng] : stan.start; if (jaM) { jaM.remove(); jaM = null; } ocenaZamknij(); ekran('s-cel'); };
    const bo = blokOcen(stan.T, stan.T.m); if (bo) $('dol').querySelector('.rzad').before(bo);
  }
  // głos
  // głos: w aplikacji syntezator Androida (działa też przy zgaszonym ekranie), gdy zawiedzie – głos przeglądarki;
  // przy teście (pokaz = true) czytelny komunikat, co zrobić, gdy telefon nie ma polskiego głosu
  function glosWeb(t) { if (!window.speechSynthesis) return false; try { const u = new SpeechSynthesisUtterance(t); u.lang = 'pl-PL'; u.rate = 1.05; speechSynthesis.cancel(); speechSynthesis.speak(u); return true; } catch (e) { return false; } }
  function glosBlad(e, pokaz) { diag.glos = 'błąd: ' + (e && e.message || e || '?'); pokazDiag();
    if (pokaz) alert('Telefon nie odtworzył komunikatu głosowego.\n\nSprawdź głośność multimediów i w Ustawieniach Androida: Ułatwienia dostępu → Zamiana tekstu na mowę – wybierz syntezator Google i pobierz język polski.'); }
  function powiedz(t, pokaz) {
    if (!stan.glos) return;
    if (NAT && PL.TextToSpeech) {
      PL.TextToSpeech.speak({text: t, lang: 'pl-PL', rate: 1.0, volume: 1.0, category: 'playback'}).then(() => { diag.glos = 'działa'; })
        .catch(e => PL.TextToSpeech.speak({text: t, rate: 1.0, volume: 1.0}).then(() => { diag.glos = 'działa (domyślny język)'; })
          .catch(e2 => { if (!glosWeb(t)) glosBlad(e2 || e, pokaz); }));
      return;
    }
    if (!glosWeb(t) && pokaz) glosBlad('brak syntezatora mowy w przeglądarce', true); }
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
