// Podgląd tabliczki w przeglądarce – ten sam układ co plates.py (generator V22 „HUB Strzebiń”, płyta cięta po obrysie).
// Dane generatora (kolory, piktogramy, rower, szerokości liter Fira Sans Condensed 600): lib/tabliczka-dane.js
window.TABLICZKA = (() => {
  const T = window.TABD;
  const FONT = 44, ICON = 36, BIKE = 100, TEXTGAP = 24, BIKEBOXW = 128, DINSET = 28, MINGAP = 18, BG_INSET = 7, MOUNT_ZONE = 60;
  const RT_D = 31, RT_GAP = 7, RT_AFTER = 10, BASE_OFF = 15.327 / 44, BB = {minX: 39, minY: 69, w: 324, h: 212};
  const FAM = "'Fira Sans Condensed', 'Roboto Condensed', 'Arial Narrow', sans-serif";
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const width = (t, size) => [...t].reduce((a, c) => a + (T.ADV[c] ?? .5), 0) * size;
  const f_ = v => +v.toFixed(3);
  const pathL = W => `M 94,8 H ${W-35} Q ${W-10},8 ${W-10},33 V 167 Q ${W-10},192 ${W-35},192 H 94 Q 79,192 69,178 L 7,113 Q -3,100 7,87 L 69,22 Q 79,8 94,8 Z`;
  const pathR = W => `M 35,8 H ${W-94} Q ${W-79},8 ${W-69},22 L ${W-7},87 Q ${W+3},100 ${W-7},113 L ${W-69},178 Q ${W-79},192 ${W-94},192 H 35 Q 10,192 10,167 V 33 Q 10,8 35,8 Z`;
  function colorShapeL(W, i = BG_INSET) {
    const top = 8 + i, bottom = 192 - i, tip = 14 + i, shoulder = 69 + i, flat = 94 + i, right = W - 10 - i, r = 25 - i / 3, sT = 22 + i, sB = 178 - i;
    return `M ${flat} ${top} H ${f_(right-r)} Q ${right} ${top} ${right} ${f_(top+r)} V ${f_(bottom-r)} Q ${right} ${bottom} ${f_(right-r)} ${bottom} ` +
           `H ${flat} Q ${flat-15} ${bottom} ${shoulder} ${sB} L ${tip} 113 Q ${tip-10} 100 ${tip} 87 L ${shoulder} ${sT} Q ${flat-15} ${top} ${flat} ${top} Z`;
  }
  function geometry(d, W) {
    const fx = d === 'left' ? 154 : 54, fw = W - 208, il = fx + 12, ir = fx + fw - 12;
    return {fx, fw, bb: [il, 27, BIKEBOXW, 146], nameX: il + BIKEBOXW + TEXTGAP, kmR: ir - (DINSET - 12)};
  }
  // entries: [[nazwa, "2,1 km", piktogram|null, [trasy]]]
  function layout(d, W, entries, size, two, gap, rt) {
    const g = geometry(d, W); const items = []; let ok = true; const multi = two && entries.length === 1;
    entries.forEach(([name, km, ico, rts], i) => {
      let lines, bases, ky;
      if (multi) {
        const w_ = name.split(' '); let best = null;
        for (let k = 1; k < w_.length; k++) { const a = w_.slice(0, k).join(' '), b = w_.slice(k).join(' '), m = Math.max(width(a, size), width(b, size)); if (!best || m < best[2]) best = [a, b, m]; }
        lines = [best[0], best[1]]; bases = [83, 148]; ky = 102 + BASE_OFF * size;
      } else { lines = [name]; bases = [(entries.length === 1 ? 102 : (i === 0 ? 67 : 133)) + BASE_OFF * size]; ky = bases[0]; }
      const tb = lines.map((t, j) => [g.nameX, bases[j] - T.ASC * size, width(t, size), (T.ASC + T.DESC) * size]);
      let icon = null;
      if (ico && T.ICONS[ico]) { const t = tb[tb.length - 1]; icon = [t[0] + t[2] + 10, t[1] + (t[3] - ICON) / 2]; }
      let nameRight = Math.max(...tb.map(t => t[0] + t[2])); if (icon) nameRight = Math.max(nameRight, icon[0] + ICON);
      let dots = null;
      if (rts && rts.length) {
        const D_ = rt[0], t = rt[1] === 'first' && tb.length > 1 ? tb[0] : tb[tb.length - 1];
        const px = (icon && t === tb[tb.length - 1] ? icon[0] + ICON : t[0] + t[2]) + RT_AFTER;
        dots = [px, t[1] + (t[3] - D_) / 2, D_]; nameRight = Math.max(nameRight, px + rts.length * D_ + (rts.length - 1) * RT_GAP);
      }
      const distLeft = g.kmR - width(km, size);
      if ((d === 'left' && g.kmR > W - MOUNT_ZONE) || (d === 'right' && g.nameX < MOUNT_ZONE)) ok = false;
      if (nameRight + gap > distLeft + .5) ok = false;
      for (const t of tb) if (t[1] < 23 || t[1] + t[3] > 177) ok = false;
      items.push({lines: lines.map((t, j) => [t, bases[j]]), km, ky, ico, icon, rts, dots});
    });
    return [ok, items];
  }
  function bestLayout(d, W, entries) {
    const opts = entries.some(e => e[3] && e[3].length) ? [[RT_D, 'last'], [RT_D, 'first'], [26, 'last'], [26, 'first'], [22, 'last'], [22, 'first']] : [[RT_D, 'last']];
    for (const rt of opts) {
      for (const gap of [MINGAP, 14, 12])
        for (const two of (entries.length === 1 && entries[0][0].includes(' ') ? [false, true] : [false])) {
          const [ok, it] = layout(d, W, entries, FONT, two, gap, rt); if (ok) return {items: it, size: FONT, two};
        }
      for (const size of [42, 40, 39, 38]) { const [ok, it] = layout(d, W, entries, size, false, MINGAP, rt); if (ok) return {items: it, size, two: false}; }
    }
    return null;
  }
  function svg(d, W, cat, entries, cls = '') {
    const color = T.PALETTE[cat] || T.PALETTE.blue;
    let lay = bestLayout(d, W, entries), uwaga = '';
    if (!lay) { const [, it] = layout(d, W, entries, 34, false, 8, [22, 'last']); lay = {items: it, size: 34}; uwaga = 'nie mieści się – potrzebna dłuższa tabliczka'; }
    const g = geometry(d, W), s = lay.size, parts = [];
    lay.items.forEach((it, i) => {
      it.lines.forEach(([t, b]) => parts.push(`<text x="${g.nameX}" y="${f_(b)}" font-size="${s}" font-family="${FAM}" font-weight="600" fill="${color}">${esc(t)}</text>`));
      parts.push(`<text x="${g.kmR}" y="${f_(it.ky)}" text-anchor="end" font-size="${s}" font-family="${FAM}" font-weight="600" fill="${color}">${esc(it.km)}</text>`);
      if (it.icon) parts.push(`<g fill="none" stroke="${color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" transform="translate(${f_(it.icon[0])} ${f_(it.icon[1])}) scale(${ICON / 24})">${T.ICONS[it.ico]}</g>`);
      if (it.dots) {
        const [px, py, D_] = it.dots;
        it.rts.forEach((r, j) => {
          const cx = px + D_ / 2 + j * (D_ + RT_GAP), cy = py + D_ / 2, [col, txt] = T.KOL[r] || ['#555', 'white'], fs = D_ * (r.length === 1 ? .66 : .49);
          parts.push(`<circle cx="${f_(cx)}" cy="${f_(cy)}" r="${D_ / 2}" fill="${col}" stroke="white" stroke-width="1.4"/><text x="${f_(cx)}" y="${f_(cy + fs * .36)}" text-anchor="middle" fill="${txt}" font-family="Arial, sans-serif" font-size="${f_(fs)}" font-weight="700">${esc(r)}</text>`);
        });
      }
    });
    const sc = BIKE / BB.w, dw = BB.w * sc, dh = BB.h * sc;
    const tx = g.bb[0] + (g.bb[2] - dw) / 2 - BB.minX * sc, ty = g.bb[1] + (g.bb[3] - dh) / 2 - BB.minY * sc;
    const arrow = d === 'left' ? 'M 54 100 L 112 50 L 112 83 L 146 83 L 146 117 L 112 117 L 112 150 Z'
      : `M ${W-52} 100 L ${W-107} 50 L ${W-107} 83 L ${W-146} 83 L ${W-146} 117 L ${W-107} 117 L ${W-107} 150 Z`;
    const cx = ((14 + BG_INSET) + (W - 10 - BG_INSET)) / 2, flip = d === 'right' ? ` transform="translate(${W} 0) scale(-1 1)"` : '';
    return {uwaga, svg: `<svg xmlns="http://www.w3.org/2000/svg" class="${cls}" viewBox="-2 -2 ${W + 4} 204" role="img" aria-label="${esc(entries.map(e => e[0] + ' ' + e[1]).join(', '))}">` +
      `<path d="${d === 'left' ? pathL(W) : pathR(W)}" fill="white" stroke="#B8C1C7" stroke-width="2.5"/>` +
      `<path d="${colorShapeL(W)}" fill="${color}"${flip}/>` +
      `<rect x="${g.fx}" y="19" width="${g.fw}" height="162" rx="15" fill="white" stroke="${color}" stroke-width="5"/><path d="${arrow}" fill="white"/>` +
      parts.join('') +
      `<g transform="translate(${f_(tx)} ${f_(ty)}) scale(${f_(sc)})" fill="none" stroke="${color}" stroke-width="10.5" stroke-linecap="round" stroke-linejoin="round">${T.BIKE}</g></svg>`};
  }
  // grupowanie celów w tabliczki: ta sama strzałka i kategoria, maks. 2 cele, rosnąco wg odległości (jak plates.py, uproszczone)
  function tabliczki(cele) {
    const gr = {};
    cele.forEach(c => { const k = c.d + '|' + c.cat + (c.cat === 'green' && c.ico === 'route' ? '|lr' + c.n : ''); (gr[k] ||= []).push(c); });
    const out = [];
    for (const k in gr) {
      const s = gr[k].sort((a, b) => a.kmv - b.kmv);
      for (let i = 0; i < s.length; i += 2) {
        let pair = s.slice(i, i + 2);
        if (pair.length === 2 && !bestLayout(pair[0].d, 800, pair.map(ent))) { out.push([pair[0]], [pair[1]]); continue; }
        out.push(pair);
      }
    }
    return out.map(p => ({d: p[0].d, cat: p[0].cat, e: p.map(ent)}));
  }
  const ent = c => [c.n, c.km, c.ico || null, c.rts || []];
  return {svg, tabliczki, bestLayout};
})();
