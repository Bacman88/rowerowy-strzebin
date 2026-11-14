// „Jedź” – rodzaj roweru, tempo, wysokości (stan/wysokosci.js), profil trasy, czas jazdy i wykres.
// Moduły ładowane po kolei (jedz.html): wspolne → graf → profil → manewry → jedz.js (interfejs); wspólna przestrzeń window.JZ.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {WYS, $, rad, dist, LS, P, stOdc} = JZ;
  // rodzaj roweru wpływa tylko na CZAS jazdy (trasę wybiera tryb Bezpieczna / Najkrótsza):
  // s – prędkość na nawierzchni względem asfaltu, g – wrażliwość na podjazdy (prędkość ÷ (1 + g·nachylenie)),
  // vmax – prędkość maksymalna (z górki); tempo na płaskim ustawia suwak
  const ROWERY = {
    miejski:  {n: 'Miejski',     g: 16, vmax: 25, s: {srednia: .7,  trudna: .45, brak: .72}},
    trekking: {n: 'Trekkingowy', g: 14, vmax: 32, s: {srednia: .8,  trudna: .55, brak: .8}},
    szosa:    {n: 'Szosowy',     g: 11, vmax: 45, s: {srednia: .5,  trudna: .28, brak: .5}},
    gravel:   {n: 'Gravel',      g: 12, vmax: 40, s: {srednia: .88, trudna: .6,  brak: .88}},
    gorski:   {n: 'Górski',      g: 12, vmax: 35, s: {srednia: .92, trudna: .72, brak: .9}},
    elektryk: {n: 'Elektryczny', g: 4,  vmax: 35, s: {srednia: .8,  trudna: .55, brak: .8}},   // wspomaganie: podjazdy prawie bez zwalniania
  };
  // stan roweru i tempa – wspólny obiekt, zmieniany też w interfejsie (podgląd trasy)
  const RT0 = ROWERY[LS.get('rower', 'miejski')] ? LS.get('rower', 'miejski') : 'miejski';
  const ST = {RT: RT0, R: ROWERY[RT0], VU: 16};
  // ===================== wysokości, nawierzchnia i czas jazdy =====================
  // stan/wysokosci.js: window.WYS = {k: krok (m), z: {id odcinka: [wysokość w dm, różnice…]}} – próbki co ~k m wzdłuż odcinka
  //   (numeryczny model terenu GUGiK). Bez pliku: profil płaski, czas tylko z nawierzchni.
  const KOLST = {osm: '#8fcf9c', dobra: '#2b9348', srednia: '#e0a800', trudna: '#d62828', nieprzejezdna: '#111', brak: '#9aa3a8'};
  const NAZST = {osm: 'utwardzona', dobra: 'dobra', srednia: 'średnia', trudna: 'trudna', nieprzejezdna: 'nieprzejezdna', brak: 'bez oceny'};
  // prędkość: tempo z suwaka × współczynnik nawierzchni dla rodzaju roweru (ROWERY)
  // wpływ nachylenia: pod górę wyraźnie wolniej (5% ≈ o połowę), z górki szybciej, ale z umiarem i nie po wertepach
  // tempo rowerzysty na płaskim, po dobrej drodze (suwak w podglądzie trasy, zapamiętane w telefonie): 17 km/h = rekreacyjnie
  ST.VU = Math.max(8, Math.min(40, +LS.get('vplaska', 16) || 16));
  function predkosc(st, g) {
    let v = ST.VU * (st === 'nieprzejezdna' ? .25 : ST.R.s[st] ?? 1);
    if (g > 0) v /= 1 + ST.R.g * g;                       // g – nachylenie jako ułamek: 2% → ok. 13 km/h, 5% → ok. 10 km/h
    else v *= Math.min(st === 'trudna' || st === 'srednia' ? 1.15 : 1.45, 1 - 7 * g);
    return Math.max(4, Math.min(Math.max(ST.R.vmax, ST.VU), v));
  }
  const wysC = new Map();
  function wysOdc(s) {
    if (wysC.has(s)) return wysC.get(s);
    const a = WYS && WYS.z[s[0]]; let w = null;
    if (a && a.length) {
      const z = []; let v = 0; for (const d of a) { v += d; z.push(v / 10); }
      const c = s[7], ll = [], cum = [0]; for (let i = 0; i < c.length; i += 2) ll.push([c[i], c[i + 1]]);
      for (let i = 1; i < ll.length; i++) cum.push(cum[i - 1] + dist(ll[i - 1], ll[i]));
      w = {z, ll, cum, L: cum[cum.length - 1]};
    }
    wysC.set(s, w); return w;
  }
  // wysokość punktu leżącego na odcinku s (rzut na linię odcinka → odległość wzdłuż → interpolacja próbek)
  function wysPkt(s, p) {
    const w = s && wysOdc(s); if (!w) return null;
    const n = w.z.length - 1; if (n < 1) return w.z[0];
    let bd = Infinity, pos = 0; const kx = Math.cos(p[0] * rad);
    for (let i = 0; i < w.ll.length - 1; i++) {
      const A = w.ll[i], B = w.ll[i + 1], ax = (A[1] - p[1]) * kx, ay = A[0] - p[0], vx = (B[1] - A[1]) * kx, vy = B[0] - A[0], L2 = vx * vx + vy * vy;
      const t = L2 ? Math.max(0, Math.min(1, -(ax * vx + ay * vy) / L2)) : 0, d = Math.hypot(ax + t * vx, ay + t * vy);
      if (d < bd) { bd = d; pos = w.cum[i] + t * (w.cum[i + 1] - w.cum[i]); }
    }
    const f = w.L ? pos / w.L * n : 0, i = Math.min(n - 1, Math.floor(f));
    return w.z[i] + (w.z[i + 1] - w.z[i]) * (f - i);
  }
  // profil trasy co ~20 m: odległość, wysokość (wygładzona), rodzaj nawierzchni, czas od startu (s)
  function profil(T) {
    const d = [], z = [], st = [];
    for (let i = 0; i < T.ll.length - 1; i++) {
      const s = T.seg[i], a = T.ll[i], b = T.ll[i + 1], L = T.cum[i + 1] - T.cum[i], n = Math.max(1, Math.round(L / 20));
      for (let k = (i ? 1 : 0); k <= n; k++) {
        const t = k / n, p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
        d.push(T.cum[i] + L * t); z.push(wysPkt(s, p)); st.push(stOdc(s) || stOdc(T.seg[i - 1]) || stOdc(T.seg[i + 1]) || 'brak');
      }
    }
    // dziury (dojazd do drogi, odcinki bez danych) – interpolacja między znanymi wysokościami
    const zn = z.map((v, i) => v == null ? -1 : i).filter(i => i >= 0);
    const jest = zn.length > 0;
    if (jest) for (let i = 0, k = 0; i < z.length; i++) {
      if (z[i] != null) continue;
      while (k < zn.length - 1 && zn[k + 1] < i) k++;
      const lo = zn[k] < i ? zn[k] : null, hi = zn.find(j => j > i);
      z[i] = lo == null ? z[hi] : hi == null ? z[lo] : z[lo] + (z[hi] - z[lo]) * (d[i] - d[lo]) / (d[hi] - d[lo]);
    } else z.fill(0);
    // wygładzenie ~±40 m (nasypy, rowy i szum modelu nie mogą udawać podjazdów)
    const zs = z.map((_, i) => { let a = 0, c = 0; for (let j = i; j >= 0 && d[i] - d[j] <= 40; j--) { a += z[j]; c++; } for (let j = i + 1; j < z.length && d[j] - d[i] <= 40; j++) { a += z[j]; c++; } return a / c; });
    const tc = [0]; let up = 0, down = 0, ref = zs[0];
    for (let i = 1; i < d.length; i++) {
      const L = d[i] - d[i - 1]; if (L <= 0) { tc.push(tc[i - 1]); continue; }
      const g = (zs[i] - zs[i - 1]) / L;
      tc.push(tc[i - 1] + L / (predkosc(st[i], Math.max(-0.12, Math.min(0.12, g))) / 3.6));
      if (zs[i] - ref > 2) { up += zs[i] - ref; ref = zs[i]; } else if (ref - zs[i] > 2) { down += ref - zs[i]; ref = zs[i]; }
    }
    return {d, z: zs, st, tc, czas: tc[tc.length - 1], up, down, wys: jest};
  }
  // czas (s) od startu do punktu trasy w odległości w (m)
  function czasDo(T, w) {
    const P = T.prof; if (!P) return w / (15 / 3.6);
    let lo = 0, hi = P.d.length - 1; if (w >= P.d[hi]) return P.tc[hi];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (P.d[m] <= w) lo = m; else hi = m; }
    return P.tc[lo] + (P.tc[hi] - P.tc[lo]) * (w - P.d[lo]) / ((P.d[hi] - P.d[lo]) || 1);
  }
  // wykres: wysokość (pole kolorowane rodzajem nawierzchni) + pasek nawierzchni pod spodem
  function wykresSVG(P, W = 340) {
    const H1 = 92, H2 = 12, G = 6, top = 8, Hh = H1 + G + H2 + 16, M = P.d[P.d.length - 1] || 1;
    let zmin = Math.min(...P.z), zmax = Math.max(...P.z); if (zmax - zmin < 20) { const s = (20 - (zmax - zmin)) / 2; zmin -= s; zmax += s; }
    const X = d => (d / M * W).toFixed(1), Y = z => (top + (H1 - top) * (1 - (z - zmin) / (zmax - zmin))).toFixed(1);
    let pola = '', pasek = '', i0 = 0;
    for (let i = 1; i <= P.d.length; i++) {
      if (i < P.d.length && P.st[i] === P.st[i0]) continue;
      const a = i0, b = Math.min(i, P.d.length - 1), kol = KOLST[P.st[i0]] || KOLST.brak;
      let pts = `${X(P.d[a])},${H1} `; for (let j = a; j <= b; j++) pts += `${X(P.d[j])},${Y(P.z[j])} `; pts += `${X(P.d[b])},${H1}`;
      pola += `<polygon points="${pts}" fill="${kol}" fill-opacity=".38"/>`;
      pasek += `<rect x="${X(P.d[a])}" y="${H1 + G}" width="${Math.max(1, X(P.d[b]) - X(P.d[a])).toFixed(1)}" height="${H2}" fill="${kol}"/>`;
      i0 = i;
    }
    const linia = P.z.map((z, i) => `${i ? 'L' : 'M'}${X(P.d[i])},${Y(z)}`).join('');
    const km = M / 1000, krok = km > 20 ? 5 : km > 8 ? 2 : km > 3 ? 1 : .5;
    let os = ''; for (let k = krok; k < km - krok * .3; k += krok) os += `<text x="${X(k * 1000)}" y="${Hh - 2}" text-anchor="middle">${String(+k.toFixed(1)).replace('.', ',')}</text><line x1="${X(k * 1000)}" x2="${X(k * 1000)}" y1="${H1 + G + H2}" y2="${H1 + G + H2 + 3}" stroke="#9aa3a8"/>`;
    const zTxt = z => Math.round(z) + ' m';
    return `<svg class="profil" viewBox="0 0 ${W} ${Hh}" width="100%" height="${Hh}" role="img" aria-label="Profil wysokości i nawierzchnia trasy">
      <line x1="0" x2="${W}" y1="${Y(zmax)}" y2="${Y(zmax)}" stroke="#e3dccb" stroke-dasharray="3 3"/><line x1="0" x2="${W}" y1="${H1}" y2="${H1}" stroke="#e3dccb"/>
      ${P.wys ? pola + `<path d="${linia}" fill="none" stroke="#1d2a23" stroke-width="1.6" vector-effect="non-scaling-stroke"/>` : ''}
      <text x="3" y="${+Y(zmax) - 2}" class="zl">${P.wys ? zTxt(zmax) : ''}</text><text x="3" y="${H1 - 3}" class="zl">${P.wys ? zTxt(zmin) : ''}</text>
      ${pasek}${os}<text x="${W - 2}" y="${Hh - 2}" text-anchor="end">km</text>
      <line class="kursor" x1="0" x2="0" y1="0" y2="${H1 + G + H2}" stroke="#1d4ed8" stroke-width="2" vector-effect="non-scaling-stroke" style="display:none"/></svg>`;
  }
  Object.assign(JZ, {ROWERY, ST, KOLST, NAZST, predkosc, wysC, wysOdc, wysPkt, profil, czasDo, wykresSVG});
})();
