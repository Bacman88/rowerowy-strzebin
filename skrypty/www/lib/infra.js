// Drogi rowerowe i szerokie chodniki wzdłuż dróg głównych (z mapy uMap projektu, stan/jedz.js → JEDZ.linie) – warstwa na mapy
// strony (trasy, mapa wspólna) i nawigacji „Jedź”. Rysowane obok osi drogi, po tej stronie, po której naprawdę są.
(() => {
  'use strict';
  const OPIS = {
    rower: {n: 'Droga rowerowa', o: 'Istniejąca droga dla rowerów (ciąg pieszo-rowerowy) wzdłuż DW 906 – po północnej stronie.'},
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
      if (o.podpowiedzi) ln.bindTooltip(`<b>${d.n}</b><br>${d.o}`, {sticky: true, direction: 'top', opacity: .95});
    }
    return g;
  }
  window.INFRA = {warstwa, OPIS};
})();
