// „Jedź” – mapa offline: własny podkład rysowany w telefonie z danych OpenStreetMap (stan/podklad.js: lasy, wody,
// zabudowa, budynki, tory, nazwy) i z naszych dróg (stan/odcinki.js). Leży pod kafelkami OSM – gdy nie ma zasięgu
// (kafelki się nie wczytają) albo gdy wybrano „zawsze mapa offline”, widać właśnie ją.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {ODC, LS} = JZ;
  // mapa offline jest na życzenie: dopóki użytkownik jej nie pobierze (JZ.podklad.pobierz), rysujemy tylko nasze drogi
  const pobrana = () => !!LS.get('mapaPobrana', false);
  let wW = null, wypelnijNazwy = () => {};
  let PD = window.PODKLAD || null;                    // stan/podklad.js wczytujemy w tle przy pierwszym otwarciu mapy (2,8 MB – nie blokuje startu)
  // współrzędne w układzie Mercatora znormalizowanym do 0..1 (jak kafelki): x = lon, y = lat
  const mx = lon => (lon + 180) / 360;
  const my = lat => { const s = Math.sin(lat * Math.PI / 180); return .5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI); };
  const CEL = 0.004;                                     // komórka indeksu przestrzennego (w jednostkach 0..1, ok. 1,7 km)
  const IDX = new Map(), cel = (x, y) => Math.floor(x / CEL) + ':' + Math.floor(y / CEL);
  const OB = [];                                          // obiekty: {k, r: [Float64Array x,y…], x0,y0,x1,y1, l?: linia}
  function dodaj(k, ringi, linia, extra) {
    let x0 = 9, y0 = 9, x1 = -9, y1 = -9;
    for (const r of ringi) for (let i = 0; i < r.length; i += 2) { if (r[i] < x0) x0 = r[i]; if (r[i] > x1) x1 = r[i]; if (r[i + 1] < y0) y0 = r[i + 1]; if (r[i + 1] > y1) y1 = r[i + 1]; }
    const o = {k, r: ringi, l: linia, x0, y0, x1, y1, ...extra}, n = OB.push(o) - 1;
    for (let a = Math.floor(x0 / CEL); a <= Math.floor(x1 / CEL); a++) for (let b = Math.floor(y0 / CEL); b <= Math.floor(y1 / CEL); b++) { const c = a + ':' + b; if (!IDX.has(c)) IDX.set(c, []); IDX.get(c).push(n); }
  }
  // dekodowanie: [dlat, dlon, …] w 1e-5 stopnia, różnicowo
  const dek = a => { const r = new Float64Array(a.length); let la = 0, lo = 0; for (let i = 0; i < a.length; i += 2) { la += a[i]; lo += a[i + 1]; r[i] = mx(lo / 1e5); r[i + 1] = my(la / 1e5); } return r; };
  let drogiGotowe = false, pdGotowy = false;
  function przygotujPD() {
    if (pdGotowy || !PD) return; pdGotowy = true;
    for (const k of ['ziel', 'zab', 'przem', 'cment', 'las', 'woda']) for (const p of PD[k] || []) dodaj(k, p.map(dek), false);
    // budynki: tylko pierwszy punkt do indeksu, pełny kształt dekodowany przy pierwszym rysowaniu (49 tys. – szybki start)
    for (const b of PD.bud || []) { const x = mx((b[1]) / 1e5), y = my(b[0] / 1e5); dodajBud(b, x, y); }
    for (const k of ['rzeki', 'tory']) for (const l of PD[k] || []) dodaj(k, [dek(l)], true);
  }
  function dodajBud(raw, x, y) {
    const d = 0.0000035, o = {k: 'bud', raw, x0: x - d, y0: y - d, x1: x + d, y1: y + d}, n = OB.push(o) - 1, c = cel(x, y);
    if (!IDX.has(c)) IDX.set(c, []); IDX.get(c).push(n);
  }
  let laduje = null;
  function laduj(cb) {
    if (PD || window.PODKLAD) { PD = PD || window.PODKLAD; return cb(); }
    if (!laduje) { laduje = []; const sc = document.createElement('script'); sc.src = 'stan/podklad.js'; sc.async = true;
      sc.onload = () => { PD = window.PODKLAD || null; const l = laduje; laduje = null; l.forEach(f => f()); };
      sc.onerror = () => { laduje = null; sc.remove(); };
      document.head.appendChild(sc); }
    laduje.push(cb);
  }
  function przygotuj() {
    if (drogiGotowe) return; drogiGotowe = true;
    for (const s of ODC) {
      const c = s[7], r = new Float64Array(c.length); for (let i = 0; i < c.length; i += 2) { r[i] = mx(c[i + 1]); r[i + 1] = my(c[i]); }
      const t = s[1], k = t === 'droga wojewódzka' || t === 'droga krajowa' || t === 'primary_link' ? 'dg' : ['ulica', 'droga powiatowa/gminna', 'droga lokalna', 'droga dojazdowa', 'pedestrian'].includes(t) ? 'du'
        : t === 'droga rowerowa' ? 'dr' : 'dl';
      dodaj(k, [r], true);
    }
  }
  // style: kolejność rysowania i wygląd (jasne, spokojne – trasa ma się wyróżniać)
  const KOL = {ziel: '#dcebcd', zab: '#ece6dc', przem: '#e6dfe8', cment: '#d2e2cb', las: '#c9e0bb', woda: '#acd0e8', bud: '#d8cfc3'};
  const KOLEJ = ['ziel', 'zab', 'przem', 'cment', 'las', 'woda', 'rzeki', 'bud', 'tory', 'dl', 'dr', 'du', 'dg'];
  const LINIE = {
    rzeki: z => ({k: '#9cc4df', w: z < 14 ? 1.2 : 2.2}),
    tory: z => ({k: '#8e8e8e', w: z < 14 ? 1.2 : 2, d: z >= 14 ? [6, 4] : null}),
    dl: z => z < 13 ? null : ({k: '#b9a888', w: z < 15 ? 1 : 1.6, d: [4, 3]}),
    dr: z => z < 12 ? null : ({k: '#2f8f6f', w: z < 15 ? 1.4 : 2.4, d: [5, 3]}),
    du: z => ({k: '#ffffff', w: z < 13 ? 1.4 : z < 15 ? 3 : 5, o: '#cfc6b6'}),
    dg: z => ({k: '#f6cf63', w: z < 13 ? 2.4 : z < 15 ? 4.5 : 7, o: '#d9a93a'}),
  };
  function warstwa(L) {
    przygotuj();
    const W = L.GridLayer.extend({
      createTile(c) {
        const t = document.createElement('canvas'), S = this.getTileSize(), dpr = Math.min(2, window.devicePixelRatio || 1);
        t.width = S.x * dpr; t.height = S.y * dpr;
        const g = t.getContext('2d'), z = c.z, sk = S.x * Math.pow(2, z), ox = c.x * S.x, oy = c.y * S.y;
        g.scale(dpr, dpr); g.fillStyle = '#f3efe5'; g.fillRect(0, 0, S.x, S.y);
        // obiekty z komórek indeksu przecinających kafelek (z marginesem na grubość linii)
        const m = 8 / sk, X0 = ox / sk - m, Y0 = oy / sk - m, X1 = (ox + S.x) / sk + m, Y1 = (oy + S.y) / sk + m, wid = new Set();
        for (let a = Math.floor(X0 / CEL); a <= Math.floor(X1 / CEL); a++) for (let b = Math.floor(Y0 / CEL); b <= Math.floor(Y1 / CEL); b++) for (const n of IDX.get(a + ':' + b) || []) wid.add(n);
        const lista = [...wid].map(n => OB[n]).filter(o => o.x1 >= X0 && o.x0 <= X1 && o.y1 >= Y0 && o.y0 <= Y1 && (o.k !== 'bud' || z >= 15));
        for (const o of lista) if (o.raw) { o.r = [dek(o.raw)]; o.raw = null; }
        const sciezka = r => { for (let i = 0; i < r.length; i += 2) { const x = r[i] * sk - ox, y = r[i + 1] * sk - oy; i ? g.lineTo(x, y) : g.moveTo(x, y); } };
        for (const k of KOLEJ) {
          const ob = lista.filter(o => o.k === k); if (!ob.length) continue;
          if (KOL[k]) {
            g.beginPath(); for (const o of ob) for (const r of o.r) { sciezka(r); g.closePath(); }
            g.fillStyle = KOL[k]; g.fill('evenodd');
            if (k === 'bud') { g.strokeStyle = '#c6bcae'; g.lineWidth = .6; g.stroke(); }
            continue;
          }
          const st = LINIE[k](z); if (!st) continue;
          g.lineJoin = g.lineCap = 'round';
          for (const [kol, w] of st.o ? [[st.o, st.w + 1.6], [st.k, st.w]] : [[st.k, st.w]]) {
            g.beginPath(); for (const o of ob) sciezka(o.r[0]);
            g.strokeStyle = kol; g.lineWidth = w; g.setLineDash(st.d && kol === st.k ? st.d : []); g.stroke();
          }
          g.setLineDash([]);
        }
        return t;
      }
    });
    const w = new W({maxZoom: 20, keepBuffer: 2, updateWhenZooming: false});
    wW = w;
    if (pobrana()) setTimeout(() => laduj(() => { przygotujPD(); w.redraw(); }), 300);   // najpierw same drogi, po chwili lasy, wody, budynki
    return w;
  }
  // nazwy miejscowości (osobna warstwa znaczników – tekst nie urywa się na krawędziach kafelków)
  function nazwy(L, map) {
    const g = L.layerGroup();
    const pokaz = () => { const z = map.getZoom(); g.eachLayer(m => { const r = +m.options.icon.options.className.slice(-1); m.getElement() && (m.getElement().style.display = (r <= 2 && z >= 11) || (r === 3 && z >= 13) || z >= 15 ? '' : 'none'); }); };
    map.on('zoomend', pokaz); g.on('add', () => setTimeout(pokaz, 0));
    let jest = false;
    wypelnijNazwy = () => { if (jest || !PD) return; jest = true; for (const [la, lo, n, r] of PD.nazwy || []) g.addLayer(L.marker([la, lo], {interactive: false, keyboard: false, pane: 'nazwy',
      icon: L.divIcon({className: 'pn r' + r, html: n.replace(/[&<>]/g, ''), iconSize: null})})); setTimeout(pokaz, 0); };
    if (pobrana()) laduj(wypelnijNazwy);
    return g;
  }
  // pobranie mapy offline (przycisk w Jedź): wczytuje plik (w przeglądarce zapisze go service worker, w aplikacji jest w środku)
  function pobierz(ok, zle) {
    laduj(() => { if (!PD) return zle && zle(); LS.set('mapaPobrana', true); przygotujPD(); if (wW) wW.redraw(); wypelnijNazwy(); ok && ok(); });
    setTimeout(() => { if (!PD) zle && zle(); }, 30000);
  }
  function usun() { LS.set('mapaPobrana', false); }
  Object.assign(JZ, {podklad: {warstwa, nazwy, pobierz, usun, pobrana}});
})();
