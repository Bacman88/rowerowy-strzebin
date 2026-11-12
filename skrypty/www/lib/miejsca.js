// Warstwy miejsc (odpoczynek, rower i udogodnienia, jedzenie i nocleg, ciekawe miejsca).
// Wspólne dla obu map na stronie i panelu. Piktogramy: te same co na tabliczkach (Tabler Icons, MIT) – lib/ikony.js.
window.MIEJSCA = (() => {
  const IK = window.IKONY || {};
  const C = {zielony:'#237647', grafit:'#505C66', czerwony:'#902B38', braz:'#81552F', pomar:'#B96516'};
  // g = warstwa: odpoczynek | serwis (rower i udogodnienia) | ciekawe (ciekawe miejsca, jedzenie i nocleg)
  const TYP = {
    lawka:    {n:'Ławka', i:'rest', c:C.zielony, g:'odpoczynek'},
    wiata:    {n:'Wiata', i:'pavilion', c:C.zielony, g:'odpoczynek'},
    piknik:   {n:'Piknik / ognisko', i:'campfire', c:C.zielony, g:'odpoczynek'},
    widok:    {n:'Punkt widokowy', i:'view', c:C.zielony, g:'odpoczynek'},
    zabawa:   {n:'Plac zabaw', i:'playground', c:C.pomar, g:'odpoczynek'},
    woda:     {n:'Woda pitna', i:'droplet', c:C.zielony, g:'odpoczynek'},
    serwis:   {n:'Serwis rowerowy', i:'service', c:C.grafit, g:'serwis'},
    stacja:   {n:'Stacja napraw rowerów', i:'service', c:C.grafit, g:'serwis'},
    stojak:   {n:'Stojak na rowery', i:'bike', c:C.grafit, g:'serwis'},
    wypozycz: {n:'Wypożyczalnia rowerów', i:'rental', c:C.grafit, g:'serwis'},
    wc:       {n:'WC', i:'wc', c:C.grafit, g:'serwis'},
    parking:  {n:'Parking', i:'parking', c:C.grafit, g:'serwis'},
    apteczka: {n:'Pierwsza pomoc / AED', i:'firstaid', c:C.grafit, g:'serwis'},
    info:     {n:'Tablica informacyjna', i:'information', c:C.grafit, g:'serwis'},
    jedzenie: {n:'Restauracja / jedzenie', i:'restaurant', c:C.czerwony, g:'ciekawe'},
    kawa:     {n:'Kawiarnia', i:'coffee', c:C.czerwony, g:'ciekawe'},
    bar:      {n:'Bar / piwo', i:'bar', c:C.czerwony, g:'ciekawe'},
    nocleg:   {n:'Nocleg', i:'bed', c:C.czerwony, g:'ciekawe'},
    ciekawe:  {n:'Ciekawe miejsce', i:'star', c:C.braz, g:'ciekawe'},
    zabytek:  {n:'Zabytek / pomnik', i:'heritage', c:C.braz, g:'ciekawe'},
    kosciol:  {n:'Kościół / kapliczka', i:'church', c:C.braz, g:'ciekawe'},
    przyroda: {n:'Przyroda', i:'tree', c:C.zielony, g:'ciekawe'},
  };
  // kolejność i grupy w formularzu
  const GRUPY = [
    ['Odpoczynek', ['lawka', 'wiata', 'piknik', 'widok', 'zabawa', 'woda']],
    ['Rower i udogodnienia', ['serwis', 'stojak', 'wypozycz', 'wc', 'parking', 'apteczka', 'info']],
    ['Jedzenie i nocleg', ['jedzenie', 'kawa', 'bar', 'nocleg']],
    ['Ciekawe miejsca', ['ciekawe', 'zabytek', 'kosciol', 'przyroda']],
  ];
  const WARSTWY = {odpoczynek:'odpoczynek', serwis:'rower i udogodnienia', ciekawe:'ciekawe miejsca, jedzenie, nocleg'};

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const svg = (t, col = '#fff', size = 15) =>
    `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${col}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IK[(TYP[t] || TYP.ciekawe).i] || IK.star || ''}</svg>`;

  const css = document.createElement('style');
  css.textContent = `.mj{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.35)}
    .mj.plan{outline:2px dashed #505C66;outline-offset:1px}
    .far .mj{width:11px;height:11px;border-width:1.5px;border-radius:4px}.far .mj svg{display:none}.far .mj.plan{outline:0}
    .mjp .t{font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase}
    .mjp h3{margin:0 0 2px;font-size:15px}.mjp p{margin:4px 0 0;font-size:13.5px;white-space:pre-wrap}.mjp .k{color:#56665c;font-size:12px;margin-top:4px}`;
  document.head.appendChild(css);

  const icon = m => L.divIcon({className:'', html:`<div class="mj${m.plan ? ' plan' : ''}" style="background:${(TYP[m.typ] || TYP.ciekawe).c}">${svg(m.typ)}</div>`,
                               iconSize:[24, 24], iconAnchor:[12, 12], popupAnchor:[0, -10]});
  function popup(m) {
    const t = TYP[m.typ] || TYP.ciekawe;
    const zr = m.nick ? `dodał(a): ${esc(m.nick)}${m.data ? ', ' + esc(m.data) : ''}` : m.osm ? 'źródło: OpenStreetMap' : '';
    return `<div class="mjp"><div class="t" style="color:${t.c}">${t.n}</div>${m.nazwa ? `<h3>${esc(m.nazwa)}</h3>` : ''}
      ${m.opis ? `<p>${esc(m.opis)}</p>` : ''}${zr ? `<div class="k">${zr}</div>` : ''}</div>`;
  }

  // Tworzy warstwy i wczytuje miejsca: stałe (data.js) + zatwierdzone zgłoszenia (api/miejsca.php).
  function warstwy(map, stale) {
    const L_ = {odpoczynek: L.layerGroup(), serwis: L.layerGroup(), ciekawe: L.layerGroup()};
    const dodaj = m => { const t = TYP[m.typ]; if (!t) return;
      L.marker([m.lat, m.lon], {icon: icon(m), title: m.nazwa || t.n, zIndexOffset: 200}).bindPopup(popup(m), {maxWidth: 260}).addTo(L_[t.g]); };
    (stale || []).forEach(dodaj);
    fetch((window.HUB_BASE || '') + 'api/miejsca.php', {cache: 'no-store'}).then(r => r.ok ? r.json() : null)
      .then(j => { (j?.miejsca || []).forEach(dodaj); }).catch(() => {});
    return L_;
  }
  return {TYP, GRUPY, WARSTWY, svg, icon, popup, warstwy, esc};
})();
