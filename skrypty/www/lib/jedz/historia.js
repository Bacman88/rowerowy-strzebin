// „Jedź” – historia przejazdów i statystyki. Zapis TYLKO w telefonie (localStorage), nic nie idzie na serwer.
// Podczas jazdy: start(meta) → punkt(p, acc, t) przy każdej pozycji GPS → koniec() zapisuje przejazd (od 200 m).
// Ślad upraszczany (punkt co ~12 m, współrzędne co 1e-5° różnicowo) – ok. 2–3 KB na 10 km; trzymamy 60 ostatnich przejazdów.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {dist, LS, kmTxt, esc} = JZ;
  const KLUCZ = 'przejazdy', MAX = 60;
  let biez = null;
  const wczytaj = () => { const a = LS.get(KLUCZ, []); return Array.isArray(a) ? a : []; };
  const zapisz = a => { try { LS.set(KLUCZ, a.slice(0, MAX)); return true; } catch (e) { try { LS.set(KLUCZ, a.slice(0, 20)); return true; } catch (e2) { return false; } } };
  function start(meta) { biez = {id: Date.now(), t0: Date.now(), cel: meta.cel || '', tryb: meta.tryb || '', rower: meta.rower || '', pts: [], km: 0, ruch: 0, vmax: 0, ost: null}; }
  function punkt(p, acc, t = Date.now()) {
    if (!biez || !p || (acc && acc > 35)) return;              // słabe odczyty GPS pomijamy
    const o = biez.ost;
    if (o) {
      const d = dist(o.p, p), dt = (t - o.t) / 1000;
      if (d < 4) return;                                        // drżenie GPS na postoju
      if (dt > 0 && dt < 30) { const v = d / dt; if (v < 25) { biez.km += d; if (v > 0.8) biez.ruch += dt; biez.vmax = Math.max(biez.vmax, Math.min(v, 20)); } }
    }
    biez.ost = {p, t};
    const l = biez.pts[biez.pts.length - 1];
    if (!l || dist([l[0], l[1]], p) >= 12) biez.pts.push([p[0], p[1]]);
  }
  const koduj = pts => { const o = []; let a = 0, b = 0; for (const [la, lo] of pts) { const x = Math.round(la * 1e5), y = Math.round(lo * 1e5); o.push(x - a, y - b); a = x; b = y; } return o; };
  const dekoduj = c => { const o = []; let a = 0, b = 0; for (let i = 0; i < c.length; i += 2) { a += c[i]; b += c[i + 1]; o.push([a / 1e5, b / 1e5]); } return o; };
  function koniec() {
    const r = biez; biez = null;
    if (!r || r.km < 200) return null;
    if (r.ost && r.pts.length) { const l = r.pts[r.pts.length - 1]; if (l[0] !== r.ost.p[0] || l[1] !== r.ost.p[1]) r.pts.push([r.ost.p[0], r.ost.p[1]]); }
    const z = {id: r.id, data: r.t0, cel: r.cel, tryb: r.tryb, rower: r.rower, km: Math.round(r.km), czas: Math.round((Date.now() - r.t0) / 1000),
      ruch: Math.round(r.ruch), vmax: Math.round(r.vmax * 3.6 * 10) / 10, s: koduj(r.pts)};
    const a = wczytaj(); a.unshift(z); zapisz(a);
    return z;
  }
  const lista = () => wczytaj();
  const slad = z => dekoduj(z.s || []);
  function usun(id) { zapisz(wczytaj().filter(z => z.id !== id)); }
  function wyczysc() { LS.set(KLUCZ, []); }
  const sredniaKmh = z => z.ruch > 30 ? z.km / z.ruch * 3.6 : 0;
  function statystyki() {
    const a = wczytaj(), mies = new Date(); mies.setDate(1); mies.setHours(0, 0, 0, 0);
    const suma = f => a.reduce((s, z) => s + f(z), 0), wMies = a.filter(z => z.data >= +mies);
    return {n: a.length, km: suma(z => z.km), ruch: suma(z => z.ruch), nMies: wMies.length, kmMies: wMies.reduce((s, z) => s + z.km, 0),
      najdl: a.reduce((m, z) => Math.max(m, z.km), 0), vmax: a.reduce((m, z) => Math.max(m, z.vmax || 0), 0)};
  }
  function gpx(z) {
    const pts = slad(z), d = new Date(z.data).toISOString();
    return `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Jedź – HUB rowerowy Strzebiń" xmlns="http://www.topografix.com/GPX/1/1">\n<metadata><name>Przejazd ${esc(new Date(z.data).toLocaleString('pl-PL'))}${z.cel ? ' – ' + esc(z.cel) : ''}</name><time>${d}</time></metadata>\n<trk><name>${esc(z.cel || 'Przejazd')}</name><trkseg>\n${pts.map(([la, lo]) => `<trkpt lat="${la.toFixed(5)}" lon="${lo.toFixed(5)}"/>`).join('\n')}\n</trkseg></trk>\n</gpx>\n`;
  }
  const czasTxtD = s => { const m = Math.round(s / 60); return m < 60 ? m + ' min' : Math.floor(m / 60) + ' h ' + String(m % 60).padStart(2, '0') + ' min'; };
  const opis = z => `${kmTxt(z.km)} · ${czasTxtD(z.ruch || z.czas)} jazdy${sredniaKmh(z) ? ' · śr. ' + sredniaKmh(z).toFixed(1).replace('.', ',') + ' km/h' : ''}`;
  Object.assign(JZ, {historia: {start, punkt, koniec, lista, slad, usun, wyczysc, statystyki, gpx, opis, czasTxtD, sredniaKmh, wTrakcie: () => !!biez,
    biezacy: () => biez && {km: biez.km, ruch: biez.ruch, vmax: biez.vmax, t0: biez.t0, pts: biez.pts},
    wznow: () => { if (biez) biez.ost = null; }}});   // po pauzie nie liczymy dystansu „przeskoku”
})();
