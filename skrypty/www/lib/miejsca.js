// Warstwy miejsc: serwis rowerowy i odpoczynek. Wspólne dla mapy HUB-u (index.html) i mapy wspólnej (stan.html).
// Piktogramy: Tabler Icons (MIT).
window.MIEJSCA = (() => {
  const IK = {
    lawka: '<path d="M16 7l2 9m-10 -9l-2 9m-1 -9h14m2 5h-18"/>',
    wiata: '<path d="M3 21h7v-3a2 2 0 0 1 4 0v3h7"/><path d="M6 21l0 -9"/><path d="M18 21l0 -9"/><path d="M6 12h12a3 3 0 0 0 3 -3a9 8 0 0 1 -9 -6a9 8 0 0 1 -9 6a3 3 0 0 0 3 3"/>',
    piknik: '<path d="M4 21l16 -4"/><path d="M20 21l-16 -4"/><path d="M12 15a4 4 0 0 0 4 -4c0 -3 -2 -3 -2 -8c-4 2 -6 5 -6 8a4 4 0 0 0 4 4z"/>',
    widok: '<path d="M4 16a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"/><path d="M14 16a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"/><path d="M16.346 9.17l-.729 -1.261c-.16 -.248 -1.056 -.203 -1.117 .091l-.177 1.38"/><path d="M19.761 14.813l-2.84 -5.133c-.189 -.31 -.592 -.68 -1.421 -.68c-.828 0 -1.5 .448 -1.5 1v6"/><path d="M7.654 9.17l.729 -1.261c.16 -.249 1.056 -.203 1.117 .091l.177 1.38"/><path d="M4.239 14.813l2.84 -5.133c.189 -.31 .592 -.68 1.421 -.68c.828 0 1.5 .448 1.5 1v6"/><path d="M10 12h4v2h-4l0 -2"/>',
    ciekawe: '<path d="M12 17.75l-6.172 3.245l1.179 -6.873l-5 -4.867l6.9 -1l3.086 -6.253l3.086 6.253l6.9 1l-5 4.867l1.179 6.873z"/>',
    serwis: '<path d="M7 10h3v-3l-3.5 -3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1 -3 3l-6 -6a6 6 0 0 1 -8 -8l3.5 3.5"/>',
  };
  IK.stacja = IK.serwis;
  const TYP = {
    serwis:  {n:'Serwis rowerowy', c:'#505C66', g:'serwis'},
    stacja:  {n:'Stacja napraw rowerów', c:'#505C66', g:'serwis'},
    lawka:   {n:'Ławka', c:'#237647', g:'odpoczynek'},
    wiata:   {n:'Wiata', c:'#237647', g:'odpoczynek'},
    piknik:  {n:'Miejsce na piknik / ognisko', c:'#237647', g:'odpoczynek'},
    widok:   {n:'Punkt widokowy', c:'#237647', g:'odpoczynek'},
    ciekawe: {n:'Ciekawe miejsce', c:'#81552F', g:'odpoczynek'},
  };
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const svg = (t, col = '#fff', size = 15) =>
    `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${col}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IK[t] || IK.ciekawe}</svg>`;

  const css = document.createElement('style');
  css.textContent = `.mj{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.35)}
    .mj.plan{border-style:dashed;border-color:#fff;outline:2px dashed #505C66;outline-offset:-1px;background-clip:padding-box}
    .far .mj{width:11px;height:11px;border-width:1.5px;border-radius:4px}.far .mj svg{display:none}.far .mj.plan{outline:0}
    .mjp h3{margin:0 0 2px;font-size:15px}.mjp .t{font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase}
    .mjp p{margin:4px 0 0;font-size:13.5px;white-space:pre-wrap}.mjp .k{color:#56665c;font-size:12px;margin-top:4px}`;
  document.head.appendChild(css);

  const icon = m => L.divIcon({className:'', html:`<div class="mj${m.plan ? ' plan' : ''}" style="background:${(TYP[m.typ] || TYP.ciekawe).c}">${svg(m.typ)}</div>`,
                               iconSize:[24, 24], iconAnchor:[12, 12], popupAnchor:[0, -10]});
  function popup(m) {
    const t = TYP[m.typ] || TYP.ciekawe;
    const zr = m.nick ? `zgłosił(a): ${esc(m.nick)}${m.data ? ', ' + esc(m.data) : ''}` : m.osm ? 'źródło: OpenStreetMap' : m.plan ? '' : '';
    return `<div class="mjp"><div class="t" style="color:${t.c}">${t.n}</div>${m.nazwa ? `<h3>${esc(m.nazwa)}</h3>` : ''}
      ${m.opis ? `<p>${esc(m.opis)}</p>` : ''}${zr ? `<div class="k">${zr}</div>` : ''}</div>`;
  }

  // Tworzy dwie warstwy i wczytuje miejsca: stałe (data.js) + zatwierdzone zgłoszenia (api/miejsca.php).
  function warstwy(map, stale) {
    const L_ = {serwis: L.layerGroup(), odpoczynek: L.layerGroup()};
    const dodaj = m => { const t = TYP[m.typ]; if (!t) return;
      L.marker([m.lat, m.lon], {icon: icon(m), title: m.nazwa || t.n, zIndexOffset: 200}).bindPopup(popup(m), {maxWidth: 260}).addTo(L_[t.g]); };
    (stale || []).forEach(dodaj);
    fetch((window.HUB_BASE || '') + 'api/miejsca.php', {cache: 'no-store'}).then(r => r.ok ? r.json() : null).then(j => { (j?.miejsca || []).forEach(dodaj); }).catch(() => {});
    return L_;
  }
  return {TYP, IK, svg, icon, popup, warstwy, esc};
})();
