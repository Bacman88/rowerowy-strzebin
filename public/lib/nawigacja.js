// Udogodnienia nawigacji dla obu map: strzałki przesuwania, „pokaż całość”, „moja lokalizacja”, pełny ekran.
// Na pełnym ekranie mapa przesuwa się zwykle (jednym palcem / kółkiem) – wyłączamy wtedy ochronę przewijania strony.
window.NAWIGACJA = (map, box, calosc) => {
  const css = document.createElement('style');
  css.textContent = `.nav-ctl{display:grid;grid-template-columns:repeat(3,38px);grid-template-rows:repeat(3,38px);gap:2px;background:rgba(255,255,255,.85);border-radius:10px;padding:3px;box-shadow:0 1px 5px rgba(0,0,0,.25)}
    .nav-ctl button,.nav-btns button{all:unset;cursor:pointer;display:grid;place-items:center;background:#fff;border-radius:8px;font:700 18px/1 Inter,system-ui,sans-serif;color:#1d2a23;width:38px;height:38px;box-shadow:0 0 0 1px rgba(0,0,0,.12)}
    .nav-ctl button:hover,.nav-btns button:hover{background:#efe9da}
    .nav-ctl button:focus-visible,.nav-btns button:focus-visible{outline:3px solid #1d4ed8}
    .nav-btns{display:flex;flex-direction:column;gap:6px}
    .nav-btns button{font-size:17px}
    .leaflet-touch .leaflet-bar a{width:40px;height:40px;line-height:40px;font-size:22px}
    .mapa-pelna{position:fixed!important;inset:0;z-index:5000;border-radius:0!important;height:100%!important;max-height:none!important;background:#fff}
    .mapa-pelna .leaflet-container{height:100%!important}
    body.ma-pelna{overflow:hidden}
    @media (max-width:900px){.mapa-pelna{display:flex!important;flex-direction:column}.mapa-pelna>.side{max-height:42vh;overflow:auto;order:2}.mapa-pelna>.leaflet-container,.mapa-pelna>[id^=map]{flex:1;order:1;height:auto!important}}`;
  if (!document.getElementById('nav-css')) { css.id = 'nav-css'; document.head.appendChild(css); }
  const IK = {"↑": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M12 19V5M6 11l6-6 6 6\"/></svg>", "↓": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M12 5v14M6 13l6 6 6-6\"/></svg>", "←": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M19 12H5M11 6l-6 6 6 6\"/></svg>", "→": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M5 12h14M13 6l6 6-6 6\"/></svg>", "⌂": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M4 11l8-7 8 7\"/><path d=\"M6 10v10h12V10\"/></svg>", "⛶": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5\"/></svg>", "✕": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M6 6l12 12M18 6L6 18\"/></svg>", "◎": "<svg viewBox=\"0 0 24 24\" width=\"22\" height=\"22\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.8\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><circle cx=\"12\" cy=\"12\" r=\"4\"/><path d=\"M12 2v3M12 19v3M2 12h3M19 12h3\"/></svg>"};
  // Wtyczka gestureHandling wyłącza przesuwanie na zdarzeniu „mouseout” mapy – a to zdarzenie przychodzi też
  // przy zjechaniu kursorem z drogi lub znacznika. Wtedy mapy nie dało się złapać myszą. Wyłączamy tylko
  // przy faktycznym opuszczeniu kontenera mapy (dotyk dalej: jeden palec przewija stronę, dwa – mapę).
  const napraw = () => { const g = map.gestureHandling; if (g && g.enabled()) { L.DomEvent.off(map, 'mouseout', g._handleMouseOut, g); if (!matchMedia('(pointer: coarse)').matches) map.dragging.enable(); } };
  napraw();
  const stop = el => { L.DomEvent.disableClickPropagation(el); L.DomEvent.disableScrollPropagation(el); return el; };
  // strzałki: przesunięcie o 1/3 widoku, środek = pokaż całość
  const Strz = L.Control.extend({onAdd() {
    const d = stop(L.DomUtil.create('div', 'nav-ctl'));
    const kroki = [['', ''], ['↑', [0, -1]], ['', ''], ['←', [-1, 0]], ['⌂', 'all'], ['→', [1, 0]], ['', ''], ['↓', [0, 1]], ['', '']];
    for (const [z, v] of kroki) {
      if (!z) { d.appendChild(document.createElement('span')); continue; }
      const b = L.DomUtil.create('button', '', d); b.type = 'button'; b.innerHTML = IK[z];
      b.title = b.ariaLabel = v === 'all' ? 'Pokaż całą mapę' : 'Przesuń mapę ' + {'↑': 'w górę', '↓': 'w dół', '←': 'w lewo', '→': 'w prawo'}[z];
      b.onclick = () => { if (v === 'all') calosc(); else { const s = map.getSize(); map.panBy([v[0] * s.x / 3, v[1] * s.y / 3]); } };
    }
    return d;
  }});
  // pełny ekran i moja lokalizacja
  let pelny = false, ja = null;
  const Btn = L.Control.extend({onAdd() {
    const d = stop(L.DomUtil.create('div', 'nav-btns'));
    const fs = L.DomUtil.create('button', '', d); fs.type = 'button'; fs.innerHTML = IK['⛶']; fs.title = fs.ariaLabel = 'Pełny ekran';
    fs.onclick = () => {
      pelny = !pelny; box.classList.toggle('mapa-pelna', pelny); document.body.classList.toggle('ma-pelna', pelny);
      fs.innerHTML = IK[pelny ? '✕' : '⛶']; fs.title = fs.ariaLabel = pelny ? 'Zamknij pełny ekran' : 'Pełny ekran';
      if (map.gestureHandling) { pelny ? map.gestureHandling.disable() : map.gestureHandling.enable(); napraw(); }
      setTimeout(() => map.invalidateSize(), 50);
    };
    if (navigator.geolocation) {
      const g = L.DomUtil.create('button', '', d); g.type = 'button'; g.innerHTML = IK['◎']; g.title = g.ariaLabel = 'Pokaż, gdzie jestem';
      g.onclick = () => navigator.geolocation.getCurrentPosition(p => {
        const ll = [p.coords.latitude, p.coords.longitude];
        if (ja) ja.remove();
        ja = L.circleMarker(ll, {radius: 8, color: '#fff', weight: 3, fillColor: '#1d4ed8', fillOpacity: 1, interactive: false}).addTo(map);
        map.setView(ll, Math.max(map.getZoom(), 15));
      }, () => alert('Nie udało się pobrać lokalizacji.'), {enableHighAccuracy: true, timeout: 15000});
    }
    return d;
  }});
  new Btn({position: 'topright'}).addTo(map);
  new Strz({position: 'bottomright'}).addTo(map);
  document.addEventListener('keydown', e => { if (pelny && e.key === 'Escape') box.querySelector('.nav-btns button').click(); });
  return {wyczyscJa: () => { if (ja) { ja.remove(); ja = null; } }, ja: () => !!ja};
};
