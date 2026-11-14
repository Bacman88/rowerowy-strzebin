// „Jedź” – graf dróg i trasowanie: węzły z odcinków (stan/odcinki.js), koszty trybów Bezpieczna / Najkrótsza / Szosowa, Dijkstra.
// Moduły ładowane po kolei (jedz.html): wspolne → graf → profil → manewry → jedz.js (interfejs); wspólna przestrzeń window.JZ.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {ODC, J, rad, RZ, dist} = JZ;
  // ===================== graf dróg =====================
  const TRASY = new Set(J.trasy), ROWER = new Set(J.rower);
  const F = {osm: 1, dobra: 1, srednia: 1.35, trudna: 2.2, nieprzejezdna: 50, brak: 1.25};
  const P = [], adj = [], klucz = new Map();
  // węzły: końce odcinków; końce leżące do 4 m od siebie łączymy (w OSM drogi leśne często „prawie” się stykają)
  const WS = new Map(), wk = p => Math.floor(p[0] * 2e4) + ':' + Math.floor(p[1] * 1.4e4);
  const wezel = p => {
    const k = p[0].toFixed(5) + ',' + p[1].toFixed(5); if (klucz.has(k)) return klucz.get(k);
    const y = Math.floor(p[0] * 2e4), x = Math.floor(p[1] * 1.4e4);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) for (const i of WS.get((y + dy) + ':' + (x + dx)) || []) if (dist(p, P[i]) < 4) { klucz.set(k, i); return i; }
    const i = P.length; klucz.set(k, i); P.push(p); adj.push([]);
    const c = wk(p); if (!WS.has(c)) WS.set(c, []); WS.get(c).push(i);
    return i;
  };
  for (const s of ODC) {
    const c = s[7], ll = []; for (let i = 0; i < c.length; i += 2) ll.push([c[i], c[i + 1]]);
    const a = wezel(ll[0]), b = wezel(ll[ll.length - 1]);
    adj[a].push({v: b, s, ll}); adj[b].push({v: a, s, ll: ll.slice().reverse()});
  }
  const DW = s => s[1] === 'droga wojewódzka' || s[1] === 'droga krajowa';
  // dwa tryby:
  //  bezp   – „Bezpieczna”: drogi wojewódzkie i krajowe ×6 (krótki odcinek przejdzie, dłuższy – objazd),
  //           chyba że obok jest droga rowerowa; uliczki w miejscowościach i drogi gminne/powiatowe – normalnie;
  //           lekka preferencja tras HUB (×0,9, bez kary za brak oceny) i ocen nawierzchni od mieszkańców
  //  krotko – „Najkrótsza”: sama długość (omija tylko drogi ocenione jako nieprzejezdne, trudne lekko droższe)
  function koszt(s, opc) {
    const st = s[4] || 'brak';
    if (opc.tryb === 'krotko') return s[6] * (st === 'nieprzejezdna' ? 50 : st === 'trudna' ? 1.4 : 1);
    // szosa – „prawie jak autem”: asfalt i drogi główne (wojewódzkie i krajowe bez kary, nawet lekko preferowane),
    // drogi nieutwardzone / bez oceny / leśne – mocno omijane; autostrad i ekspresówek nie ma w sieci dróg (odcinki.py)
    if (opc.tryb === 'szosa') {
      let f = {osm: 1, dobra: 1, srednia: 3, trudna: 10, nieprzejezdna: 50, brak: 4}[stOdc(s)] ?? 4;
      if (s[1] === 'ścieżka piesza' || s[1] === 'ścieżka' || s[1] === 'droga leśna/polna') f = Math.max(f, f === 1 ? 2 : 5);
      if (DW(s) || ROWER.has(s[0])) f *= 0.9;
      return s[6] * f;
    }
    let f = F[st] ?? 1.25;
    if (TRASY.has(s[0])) f = Math.min(f, 1) * 0.9;   // drogi tras HUB są sprawdzone – bez kary „brak oceny”
    if (ROWER.has(s[0])) f = Math.min(f, 0.85);
    else if (DW(s)) f *= 6;
    return s[6] * f;
  }
  // najbliższy węzeł grafu (siatka ~1 km, żeby nie przeszukiwać 27 tys. punktów co sekundę)
  const SIAT = new Map(), sk = p => Math.floor(p[0] * 100) + ':' + Math.floor(p[1] * 70);
  P.forEach((p, i) => { const k = sk(p); if (!SIAT.has(k)) SIAT.set(k, []); SIAT.get(k).push(i); });
  function najblizszy(p) {
    let b = -1, bd = Infinity; const y = Math.floor(p[0] * 100), x = Math.floor(p[1] * 70);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) for (const i of SIAT.get((y + dy) + ':' + (x + dx)) || []) { const d = dist(p, P[i]); if (d < bd) { bd = d; b = i; } }
    return [b, bd];
  }
  // --- przyczepienie punktu do najbliższej DROGI (rzut prostopadły na odcinek), nie do najbliższego węzła –
  //     tak start „poza drogą” prowadzi najkrótszą linią do drogi, a cel na środku długiej drogi nie trafia do ślepej ścieżki
  const SEGS = [], SIDX = new Map();
  ODC.forEach((s, j) => {
    const c = s[7], ll = []; for (let i = 0; i < c.length; i += 2) ll.push([c[i], c[i + 1]]);
    const g = {s, ll, a: klucz.get(ll[0][0].toFixed(5) + ',' + ll[0][1].toFixed(5)), b: klucz.get(ll[ll.length - 1][0].toFixed(5) + ',' + ll[ll.length - 1][1].toFixed(5))};
    SEGS.push(g);
    const kom = new Set(ll.map(sk)); for (let i = 1; i < ll.length; i++) kom.add(sk([(ll[i][0] + ll[i - 1][0]) / 2, (ll[i][1] + ll[i - 1][1]) / 2]));
    for (const k of kom) { if (!SIDX.has(k)) SIDX.set(k, []); SIDX.get(k).push(j); }
  });
  function przyczep(p) {
    let best = null; const y = Math.floor(p[0] * 100), x = Math.floor(p[1] * 70), kx = Math.cos(p[0] * rad);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) for (const j of SIDX.get((y + dy) + ':' + (x + dx)) || []) {
      const g = SEGS[j], ll = g.ll;
      for (let i = 0; i < ll.length - 1; i++) {
        const A = ll[i], B = ll[i + 1], ax = (A[1] - p[1]) * kx, ay = A[0] - p[0], bx = (B[1] - p[1]) * kx, by = B[0] - p[0], vx = bx - ax, vy = by - ay, L2 = vx * vx + vy * vy;
        const t = L2 ? Math.max(0, Math.min(1, -(ax * vx + ay * vy) / L2)) : 0;
        const d = Math.hypot(ax + t * vx, ay + t * vy) * rad * RZ, kara = g.s[1] === 'ścieżka piesza' ? 15 : 0;
        if (!best || d + kara < best.dk) best = {dk: d + kara, d, g, i, pt: [A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t]};
      }
    }
    if (!best) return null;
    const {g, i, pt} = best;
    best.doA = [pt, ...g.ll.slice(0, i + 1).reverse()];    // od punktu do początku odcinka (węzeł a)
    best.doB = [pt, ...g.ll.slice(i + 1)];                 // od punktu do końca odcinka (węzeł b)
    const dl = l => { let m = 0; for (let k = 1; k < l.length; k++) m += dist(l[k - 1], l[k]); return m; };
    best.mA = dl(best.doA); best.mB = dl(best.doB);
    return best;
  }
  function trasuj(a, b, opc) {
    const S = przyczep(a), T = przyczep(b);
    if (!S || S.d > 600) return {blad: 'start'};
    if (!T || T.d > 600) return {blad: 'cel'};
    const kf = (g, m) => koszt(g.s, opc) * (m / (g.s[6] || 1));
    const n = P.length, cost = new Float64Array(n).fill(Infinity), prev = new Int32Array(n).fill(-1), via = new Array(n);
    const h = [];
    const push = x => { h.push(x); let i = h.length - 1; while (i > 0) { const j = (i - 1) >> 1; if (h[j][0] <= h[i][0]) break; [h[i], h[j]] = [h[j], h[i]]; i = j; } };
    const pop = () => { const top = h[0], e = h.pop(); if (h.length) { h[0] = e; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i; if (l < h.length && h[l][0] < h[m][0]) m = l; if (r < h.length && h[r][0] < h[m][0]) m = r; if (m === i) break; [h[i], h[m]] = [h[m], h[i]]; i = m; } } return top; };
    for (const [v, m] of [[S.g.a, S.mA], [S.g.b, S.mB]]) { const w = kf(S.g, m); if (w < cost[v]) { cost[v] = w; prev[v] = -2; push([w, v]); } }
    // koszt dojazdu do celu z obu końców odcinka celu
    const konc = [[T.g.a, T.mA, T.doA], [T.g.b, T.mB, T.doB]];
    let najl = Infinity;
    // oba punkty na tym samym odcinku – jazda wprost po nim
    let wprost = null;
    if (S.g === T.g) {
      const pS = S.mA, pT = T.mA; const ll = S.g.ll;
      const geo = pT >= pS ? [S.pt, ...ll.slice(S.i + 1, T.i + 1), T.pt] : [S.pt, ...ll.slice(T.i + 1, S.i + 1).reverse(), T.pt];
      wprost = {w: kf(S.g, Math.abs(pT - pS)), geo}; najl = wprost.w;
    }
    while (h.length) {
      const [c, u] = pop(); if (c > cost[u]) continue; if (c > najl) break;
      for (const [v, m] of konc) if (u === v) najl = Math.min(najl, c + kf(T.g, m));
      for (const e of adj[u]) { const w = c + koszt(e.s, opc); if (w < cost[e.v]) { cost[e.v] = w; prev[e.v] = u; via[e.v] = e; push([w, e.v]); } }
    }
    // wybór końca
    let kon = null, kw = wprost ? wprost.w : Infinity;
    for (const [v, m, geo] of konc) { const w = cost[v] + kf(T.g, m); if (w < kw - 1e-9) { kw = w; kon = {v, geo}; } }
    if (!isFinite(kw)) return {blad: 'brak'};
    const ll = [a], seg = [], wez = [];
    const dodaj = (pts, s) => { for (const q of pts) { if (dist(ll[ll.length - 1], q) < 0.5) continue; seg.push(s); ll.push(q); } };
    dodaj([S.pt], null);                         // prostopadle do drogi
    let kroki = [];
    if (!kon) dodaj(wprost.geo, S.g.s);
    else {
      let v = kon.v; while (prev[v] !== -2) { kroki.unshift(via[v]); v = prev[v]; }
      const v0 = v;
      dodaj((v0 === S.g.a ? S.doA : S.doB).slice(1), S.g.s);
      wez.push({i: ll.length - 1, deg: adj[v0].length});
      for (const e of kroki) { dodaj(e.ll.slice(1), e.s); wez.push({i: ll.length - 1, deg: adj[e.v].length}); }
      dodaj(kon.geo.slice().reverse().slice(1), T.g.s);
    }
    dodaj([b], null);                             // od drogi do celu
    const cum = [0]; for (let i = 1; i < ll.length; i++) cum.push(cum[i - 1] + dist(ll[i - 1], ll[i]));
    return {ll, seg, cum, m: cum[cum.length - 1], wez, kroki};
  }
  // punkt na trasie w odległości d (m) od startu
  function wDal(T, d) {
    d = Math.max(0, Math.min(T.m, d));
    let lo = 0, hi = T.cum.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T.cum[m] <= d) lo = m; else hi = m; }
    const a = T.ll[lo], b = T.ll[hi], L = T.cum[hi] - T.cum[lo] || 1, t = (d - T.cum[lo]) / L;
    return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  }

  const UTW = /asfalt|kostka|beton|płyty|plyty|paved|asphalt|concrete/i;
  // rodzaj nawierzchni do wykresu i prędkości: ocena mieszkańców / pomiar, a bez niej – utwardzona wg OSM albo „bez oceny”
  const stOdc = s => !s ? null : s[4] && s[4] !== 'osm' ? s[4] : (s[4] === 'osm' || UTW.test(s[3] || '')) ? 'osm' : 'brak';
  Object.assign(JZ, {TRASY, ROWER, F, P, adj, DW, koszt, najblizszy, przyczep, trasuj, wDal, UTW, stOdc});
})();
