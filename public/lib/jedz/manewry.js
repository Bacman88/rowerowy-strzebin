// „Jedź” – manewry: drogowskazy na trasie (tabliczka tak, jak widzi ją rowerzysta) i skręty z nazwami ulic.
// Moduły ładowane po kolei (jedz.html): wspolne → graf → profil → manewry → jedz.js (interfejs); wspólna przestrzeń window.JZ.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {H, TB, $, dist, brg, kat, DW, wDal} = JZ;
  // ===================== manewry =====================
  // nazwa drogi do komunikatu: „ul. Leśna”, „DW 906”, „Dojazd pożarowy 75”; drogi bez nazwy – pusto
  const nazwaDrogi = s => {
    if (!s || !s[2]) return '';
    if (DW(s)) return (s[1] === 'droga krajowa' ? 'DK ' : 'DW ') + (/^\d+$/.test(s[2]) ? s[2] : s[2]);
    if (/^\d+$/.test(s[2])) return '';
    return ['ulica', 'droga powiatowa/gminna', 'droga lokalna', 'droga dojazdowa'].includes(s[1]) && !/^(ul\.|aleja|al\.|plac|dojazd)/i.test(s[2]) ? 'ul. ' + s[2] : s[2];
  };
  function strzalkaSVG(kier, kol = '#00737e', w = 44) {
    const d = {lewo: 'M19 12H5M11 6l-6 6 6 6', prawo: 'M5 12h14M13 6l6 6-6 6', prosto: 'M12 20V4M6 10l6-6 6 6', 'lekko w lewo': 'M17 20V12L8 5M8 11V5h6', 'lekko w prawo': 'M7 20V12l9-7M16 11V5h-6', 'ostro w lewo': 'M17 4v9a5 5 0 0 1-10 0V8M3 11l4-4 4 4', 'ostro w prawo': 'M7 4v9a5 5 0 0 0 10 0V8M13 11l4-4 4 4', cel: 'M6 21V3l12 5-12 5'}[kier] || 'M12 20V4M6 10l6-6 6 6';
    return `<svg width="${w}" height="${w}" viewBox="0 0 24 24" fill="none" stroke="${kol}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
  }
  const kierunek = t => { const a = Math.abs(t); return a < 25 ? 'prosto' : a < 55 ? (t < 0 ? 'lekko w lewo' : 'lekko w prawo') : a < 140 ? (t < 0 ? 'lewo' : 'prawo') : (t < 0 ? 'ostro w lewo' : 'ostro w prawo'); };
  const kierTxt = k => ({lewo: 'W lewo', prawo: 'W prawo', prosto: 'Prosto', 'lekko w lewo': 'Lekko w lewo', 'lekko w prawo': 'Lekko w prawo', 'ostro w lewo': 'Ostro w lewo', 'ostro w prawo': 'Ostro w prawo'}[k] || k);
  function manewry(T) {
    const out = [];
    // 1) drogowskazy (przyszłe słupki) na trasie
    for (const p of H.posts) {
      const q = [p.lat, p.lon]; let b = -1, bd = 30;
      for (let i = 0; i < T.ll.length; i++) { const d = dist(q, T.ll[i]); if (d < bd) { bd = d; b = i; } }
      if (b < 0) continue;
      const c = T.cum[b]; if (c < 20 || c > T.m - 20) continue;
      const wej = brg(wDal(T, c - 40), q), wyj = brg(q, wDal(T, c + 60));
      let best = null;
      for (const t of p.tab) { if (t.g == null) continue; const d = Math.abs(kat(t.g, wyj)); if (d < 40 && (!best || d < best.d)) best = {t, d}; }
      if (!best) continue;
      const k = kierunek(kat(wyj, wej));
      const wzgl = kat(best.t.g, wej);   // tabliczka oglądana od strony nadjeżdżającego: grot po lewej czy po prawej?
      const strona = Math.abs(wzgl) < 15 ? best.t.d : (wzgl < 0 ? 'left' : 'right');
      out.push({typ: 'tab', c, k, t: best.t, strona, cele: best.t.e.map(e => e[0]), nr: p.nr});
    }
    // 2) skręty poza drogowskazami (nazwy ulic z OSM)
    for (let j = 1; j < T.wez.length - 1; j++) {
      const w = T.wez[j]; if (w.deg < 3) continue;
      const c = T.cum[w.i]; if (c < 15 || c > T.m - 15) continue;
      if (out.some(m => Math.abs(m.c - c) < 70)) continue;
      const q = T.ll[w.i], t = kat(brg(q, wDal(T, c + 30)), brg(wDal(T, c - 30), q));
      if (Math.abs(t) < 35) continue;
      const nz = nazwaDrogi(T.seg[w.i]), przed = T.seg[w.i - 1];
      if (nz && przed && nazwaDrogi(przed) === nz && Math.abs(t) < 75) continue;   // ta sama droga, tylko zakręt
      out.push({typ: 'skret', c, k: kierunek(t), ulica: nz});
    }
    out.sort((a, b) => a.c - b.c);
    out.push({typ: 'cel', c: T.m, k: 'cel'});
    return out;
  }
  const mTekst = m => m.typ === 'tab' ? `${kierTxt(m.k)}, kierunek ${m.cele.join(' · ')}`
    : m.typ === 'skret' ? (m.ulica ? `${kierTxt(m.k)} · ${m.ulica}` : kierTxt(m.k))
    : 'Cel: ' + ((JZ.stan && JZ.stan.celN) || '');   // JZ.stan – stan interfejsu (jedz.js)
  const tabSVG = (m, cls = '') => TB.svg(m.strona, 800, m.t.cat, m.t.e).svg.replace('<svg ', `<svg class="${cls}" `);

  Object.assign(JZ, {nazwaDrogi, strzalkaSVG, kierunek, kierTxt, manewry, mTekst, tabSVG});
})();
