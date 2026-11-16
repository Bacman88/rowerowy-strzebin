// Drogi rowerowe i szerokie chodniki wzdłuż dróg głównych (z mapy uMap projektu, stan/jedz.js → JEDZ.linie) – warstwa na mapy
// strony (trasy, mapa wspólna) i nawigacji „Jedź”. Rysowane obok osi drogi, po tej stronie, po której naprawdę są.
(() => {
  'use strict';
  const OPIS = {
    rower: {n: 'Droga rowerowa', o: 'Istniejąca droga dla rowerów (ciąg pieszo-rowerowy) wzdłuż drogi wojewódzkiej.'},
    rowerOsm: {n: 'Droga dla rowerów', o: 'Istniejąca droga dla rowerów (z OpenStreetMap).'},
    chodnik: {n: 'Szeroki chodnik', o: 'Szeroki chodnik wzdłuż DW 906 (po południowej stronie) – bezpieczniejsza alternatywa dla jazdy jezdnią. Uważaj na pieszych.'},
  };
  function warstwa(L, o = {}) {
    const g = L.layerGroup(), linie = (window.JEDZ && window.JEDZ.linie) || [];
    const pane = o.pane;
    for (const l of linie) {
      const d = OPIS[l.typ]; if (!d || !l.ll || l.ll.length < 2) continue;
      const opcje = {interactive: !!o.podpowiedzi, pane, lineCap: 'round', lineJoin: 'round'};
      // droga rowerowa: „pas” – niebieskie krawędzie z białym środkiem (nie myli się z kolorowymi liniami tras);
      // szeroki chodnik: niebieska linia przerywana na białej obwódce
      const w = o.gr || 4; let ln;
      if (l.typ === 'rower') {
        ln = L.polyline(l.ll, {...opcje, color: '#1e6fd0', weight: w + 3, opacity: 1}).addTo(g);
        L.polyline(l.ll, {...opcje, interactive: false, color: '#fff', weight: Math.max(1.5, w - 1.5), opacity: 1}).addTo(g);
      } else {
        L.polyline(l.ll, {...opcje, interactive: false, color: '#fff', weight: w + 3, opacity: .95}).addTo(g);
        ln = L.polyline(l.ll, {...opcje, color: '#1e6fd0', weight: w, opacity: 1, dashArray: '7 6'}).addTo(g);
      }
      const dd = l.osm ? OPIS.rowerOsm : d;
      if (o.podpowiedzi) ln.bindTooltip(`<b>${dd.n}</b><br>${dd.o}`, {sticky: true, direction: 'top', opacity: .95});
    }
    return g;
  }
  // przełącznik warstwy na mapie (Leaflet control): „Drogi rowerowe” – pamiętany w przeglądarce
  function przelacznik(L, map, g) {
    const C = L.Control.extend({options: {position: 'topright'}, onAdd() {
      const d = L.DomUtil.create('label', 'infra-prz'); let on = true; try { on = localStorage.getItem('infra') !== '0'; } catch (e) {}
      d.innerHTML = `<input type="checkbox"${on ? ' checked' : ''}> <svg width="22" height="10" aria-hidden="true"><rect x="1" y="1" width="20" height="8" rx="4" fill="#fff" stroke="#1e6fd0" stroke-width="2.5"/></svg> Drogi rowerowe`;
      d.style.cssText = 'background:#fff;padding:5px 9px;border-radius:8px;box-shadow:0 1px 5px rgba(0,0,0,.25);font:600 13px system-ui,sans-serif;display:flex;align-items:center;gap:6px;cursor:pointer;color:#1d2a23';
      L.DomEvent.disableClickPropagation(d); const cb = d.querySelector('input');
      const ust = v => { if (v) g.addTo(map); else g.remove(); try { localStorage.setItem('infra', v ? '1' : '0'); } catch (e) {} };
      cb.onchange = () => ust(cb.checked); ust(on); return d; }});
    return new C().addTo(map);
  }
  window.INFRA = {warstwa, OPIS, przelacznik};
})();
