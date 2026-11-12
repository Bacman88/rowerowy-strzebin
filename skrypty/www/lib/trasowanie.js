// Odległości po drogach w przeglądarce (edytor tabliczek): graf z odcinków mapy wspólnej (stan/odcinki.js),
// koszt jak w directions.py – drogi utwardzone/dobre taniej, trudne i nieprzejezdne drożej.
window.TRASOWANIE = (() => {
  const R = 6371000, rad = Math.PI / 180;
  const dist = (a, b) => { const x = (b[1] - a[1]) * rad * Math.cos((a[0] + b[0]) / 2 * rad), y = (b[0] - a[0]) * rad; return Math.hypot(x, y) * R; };
  const F = {osm: 1.0, dobra: 1.0, srednia: 1.35, trudna: 2.2, nieprzejezdna: 50, brak: 1.25};
  let G = null;
  function graf(stanOf) {
    const key = p => p[0].toFixed(5) + ',' + p[1].toFixed(5);
    const nodes = new Map(), adj = [];
    const id = p => { const k = key(p); if (!nodes.has(k)) { nodes.set(k, nodes.size); adj.push([]); P.push(p); } return nodes.get(k); };
    const P = [];
    for (const s of window.ODC) {
      const c = s[7], ll = []; for (let i = 0; i < c.length; i += 2) ll.push([c[i], c[i + 1]]);
      const a = id(ll[0]), b = id(ll[ll.length - 1]), f = F[stanOf ? stanOf(s[0], s[4]) : (s[4] || 'brak')] ?? 1.25;
      adj[a].push([b, s[6], s[6] * f, ll]); adj[b].push([a, s[6], s[6] * f, ll.slice().reverse()]);
    }
    G = {P, adj}; return G;
  }
  function najblizszy(p) { let b = 0, bd = Infinity; G.P.forEach((q, i) => { const d = dist(p, q); if (d < bd) { bd = d; b = i; } }); return [b, bd]; }
  // Dijkstra od punktu: zwraca funkcję trasa(cel) -> {m, ll}
  function od(p) {
    const [s, d0] = najblizszy(p), n = G.P.length, cost = new Float64Array(n).fill(Infinity), len = new Float64Array(n), prev = new Int32Array(n).fill(-1), via = new Array(n);
    cost[s] = 0; len[s] = d0; const h = [[0, s]];
    const push = x => { h.push(x); let i = h.length - 1; while (i > 0) { const j = (i - 1) >> 1; if (h[j][0] <= h[i][0]) break; [h[i], h[j]] = [h[j], h[i]]; i = j; } };
    const pop = () => { const t = h[0], e = h.pop(); if (h.length) { h[0] = e; let i = 0; for (;;) { const l = 2 * i + 1, r = l + 1; let m = i; if (l < h.length && h[l][0] < h[m][0]) m = l; if (r < h.length && h[r][0] < h[m][0]) m = r; if (m === i) break; [h[i], h[m]] = [h[m], h[i]]; i = m; } } return t; };
    while (h.length) {
      const [c, u] = pop(); if (c > cost[u]) continue;
      for (const [v, m, w, ll] of G.adj[u]) if (c + w < cost[v]) { cost[v] = c + w; len[v] = len[u] + m; prev[v] = u; via[v] = ll; push([cost[v], v]); }
    }
    return cel => {
      const [t, d1] = najblizszy(cel); if (!isFinite(cost[t])) return null;
      const seg = []; for (let v = t; v !== s; v = prev[v]) seg.unshift(via[v]);
      const out = [p]; seg.forEach(sg => out.push(...sg.slice(1)));
      return {m: len[t] + d1, ll: out};
    };
  }
  function azymut(ll) {
    let acc = 0, b = ll[ll.length - 1];
    for (let i = 1; i < ll.length; i++) { acc += dist(ll[i - 1], ll[i]); b = ll[i]; if (acc > 80) break; }
    const x = (b[1] - ll[0][1]) * Math.cos(ll[0][0] * rad), y = b[0] - ll[0][0];
    return (Math.atan2(x, y) / rad + 360) % 360;
  }
  // strzałka jak w plates.py: wsch. i płn. →, zach. i płd. ←
  const strzalka = deg => { const s = Math.sin(deg * rad), c = Math.cos(deg * rad); return (s > .34 || (Math.abs(s) <= .34 && c > 0)) ? 'right' : 'left'; };
  // trasy pokazowe, którymi prowadzi ścieżka: punkty pierwszego min(1 km, 60%) drogi (bez pierwszych 60 m od słupka) leżą do 20 m od trasy
  function trasy(ll, routes) {
    let total = 0; for (let i = 1; i < ll.length; i++) total += dist(ll[i - 1], ll[i]);
    const need = Math.min(1000, .6 * total), probe = []; let acc = 0;
    for (let i = 1; i < ll.length && acc < need; i++) { const d = dist(ll[i - 1], ll[i]); for (let k = 1; k <= Math.ceil(d / 40); k++) { const t = k / Math.ceil(d / 40); if (acc + d * t < 60) continue; probe.push([ll[i - 1][0] + (ll[i][0] - ll[i - 1][0]) * t, ll[i - 1][1] + (ll[i][1] - ll[i - 1][1]) * t]); } acc += d; }
    const out = [];
    for (const r of routes) {
      if (r.alt) continue;
      const pts = r.parts.flatMap(p => p.c);
      const near = q => { for (let i = 1; i < pts.length; i++) if (dSeg(q, pts[i - 1], pts[i]) < 20) return true; return false; };
      if (probe.length && probe.every(near)) out.push(r.id);
    }
    return out.slice(0, 4);
  }
  function dSeg(p, a, b) {
    const kx = Math.cos(p[0] * rad) * R * rad, ky = R * rad;
    const ax = (a[1] - p[1]) * kx, ay = (a[0] - p[0]) * ky, bx = (b[1] - p[1]) * kx, by = (b[0] - p[0]) * ky;
    const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy; let t = L2 ? -(ax * dx + ay * dy) / L2 : 0; t = Math.max(0, Math.min(1, t));
    return Math.hypot(ax + t * dx, ay + t * dy);
  }
  return {graf, od, azymut, strzalka, trasy, dist};
})();
