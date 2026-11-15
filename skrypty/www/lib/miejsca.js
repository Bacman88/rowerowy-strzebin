// Warstwy miejsc (odpoczynek, rower i udogodnienia, jedzenie i nocleg, ciekawe miejsca).
// Wspólne dla obu map na stronie i panelu. Piktogramy: te same co na tabliczkach (Tabler Icons, MIT) – lib/ikony.js.
window.MIEJSCA = (() => {
  const IK = window.IKONY || {};
  const C = {zielony:'#237647', grafit:'#505C66', czerwony:'#902B38', braz:'#81552F', pomar:'#B96516', aed:'#00853F'};
  // piktogramy tylko na mapie (tabliczki zostają przy swoich): huśtawka zamiast „roller coastera”, serce z błyskawicą (AED), koszyk (sklep)
  const IKM = {
    hustawka: '<path d="M3 4h18"/><path d="M6 4l-3 16"/><path d="M18 4l3 16"/><path d="M10 4v9"/><path d="M14 4v9"/><path d="M9 13h6v2h-6z"/>',
    aed: '<path d="M19.5 12.572l-7.5 7.428l-7.5 -7.428a5 5 0 1 1 7.5 -6.566a5 5 0 1 1 7.5 6.572"/><path d="M12.5 8.5l-2 3.5h3l-2 3.5"/>',
    apteka: '<path d="M9 3h6v6h6v6h-6v6h-6v-6h-6v-6h6z"/>',
    sklep: '<path d="M6 19m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M17 19m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0"/><path d="M17 17h-11v-14h-2"/><path d="M6 5l14 1l-1 7h-13"/>',
  };
  // g = warstwa: odpoczynek | serwis (rower i udogodnienia) | ciekawe (ciekawe miejsca, jedzenie i nocleg)
  const TYP = {
    lawka:    {n:'Ławka', i:'rest', c:C.zielony, g:'odpoczynek'},
    wiata:    {n:'Wiata', i:'pavilion', c:C.zielony, g:'odpoczynek'},
    piknik:   {n:'Piknik / ognisko', i:'campfire', c:C.zielony, g:'odpoczynek'},
    widok:    {n:'Punkt widokowy', i:'view', c:C.zielony, g:'odpoczynek'},
    zabawa:   {n:'Plac zabaw', i:'hustawka', c:C.pomar, g:'odpoczynek'},
    woda:     {n:'Woda pitna', i:'droplet', c:C.zielony, g:'odpoczynek'},
    serwis:   {n:'Serwis rowerowy', i:'service', c:C.grafit, g:'serwis'},
    stacja:   {n:'Stacja napraw rowerów', i:'service', c:C.grafit, g:'serwis'},
    stojak:   {n:'Stojak na rowery', i:'bike', c:C.grafit, g:'serwis'},
    wypozycz: {n:'Wypożyczalnia rowerów', i:'rental', c:C.grafit, g:'serwis'},
    wc:       {n:'WC', i:'wc', c:C.grafit, g:'serwis'},
    parking:  {n:'Parking', i:'parking', c:C.grafit, g:'serwis'},
    aed:      {n:'Defibrylator AED', i:'aed', c:C.aed, g:'serwis'},
    apteczka: {n:'Pierwsza pomoc', i:'firstaid', c:C.grafit, g:'serwis'},
    apteka:   {n:'Apteka', i:'apteka', c:C.zielony, g:'serwis'},
    info:     {n:'Tablica informacyjna', i:'information', c:C.grafit, g:'serwis'},
    jedzenie: {n:'Restauracja / jedzenie', i:'restaurant', c:C.czerwony, g:'ciekawe'},
    kawa:     {n:'Kawiarnia', i:'coffee', c:C.czerwony, g:'ciekawe'},
    bar:      {n:'Bar / piwo', i:'bar', c:C.czerwony, g:'ciekawe'},
    sklep:    {n:'Sklep spożywczy', i:'sklep', c:C.czerwony, g:'ciekawe'},
    nocleg:   {n:'Nocleg', i:'bed', c:C.czerwony, g:'ciekawe'},
    ciekawe:  {n:'Ciekawe miejsce', i:'star', c:C.braz, g:'ciekawe'},
    zabytek:  {n:'Zabytek / pomnik', i:'heritage', c:C.braz, g:'ciekawe'},
    kosciol:  {n:'Kościół / kapliczka', i:'church', c:C.braz, g:'ciekawe'},
    przyroda: {n:'Przyroda', i:'tree', c:C.zielony, g:'ciekawe'},
    sport:    {n:'Sport i rekreacja', i:'sport', c:C.pomar, g:'ciekawe'},
  };
  // kolejność i grupy w formularzu
  const GRUPY = [
    ['Odpoczynek', ['lawka', 'wiata', 'piknik', 'widok', 'zabawa', 'woda']],
    ['Rower i udogodnienia', ['serwis', 'stojak', 'wypozycz', 'wc', 'parking', 'aed', 'apteczka', 'apteka', 'info']],
    ['Jedzenie i nocleg', ['jedzenie', 'kawa', 'bar', 'sklep', 'nocleg']],
    ['Ciekawe miejsca', ['ciekawe', 'zabytek', 'kosciol', 'przyroda', 'sport']],
  ];
  const WARSTWY = {odpoczynek:'odpoczynek', serwis:'rower i udogodnienia', ciekawe:'ciekawe miejsca, jedzenie, nocleg'};

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  // ik – opcjonalnie własny piktogram miejsca (np. basen przy typie „sport”)
  const NAPIS = {wc: ['WC', 15, 17.4], parking: ['P', 19, 19]};   // piktogram jako napis (WC, P)
  const svg = (t, col = '#fff', size = 15, ik = null) => NAPIS[t] && !ik
    ? `<svg viewBox="0 0 24 24" width="${size}" height="${size}" aria-hidden="true"><text x="12" y="${NAPIS[t][2]}" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="${NAPIS[t][1]}" font-weight="800" letter-spacing="-0.6" fill="${col}">${NAPIS[t][0]}</text></svg>`
    : `<svg viewBox="0 0 24 24" width="${size}" height="${size}" fill="none" stroke="${col}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IK[ik] || IKM[(TYP[t] || TYP.ciekawe).i] || IK[(TYP[t] || TYP.ciekawe).i] || IK.star || ''}</svg>`;

  const css = document.createElement('style');
  css.textContent = `.mj{width:24px;height:24px;border-radius:7px;display:grid;place-items:center;border:2px solid #fff;box-shadow:0 1px 3px rgba(0,0,0,.35)}
    .mj.plan{outline:2px dashed #505C66;outline-offset:1px}
    .far .mj{width:11px;height:11px;border-width:1.5px;border-radius:4px}.far .mj svg{display:none}.far .mj.plan{outline:0}
    .mjp .t{font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase}
    .mjp h3{margin:0 0 2px;font-size:15px}.mjp p{margin:4px 0 0;font-size:13.5px;white-space:pre-wrap}.mjp .k{color:#56665c;font-size:12px;margin-top:4px}`;
  document.head.appendChild(css);

  const icon = m => L.divIcon({className:'', html:`<div class="mj${m.plan ? ' plan' : ''}" style="background:${(TYP[m.typ] || TYP.ciekawe).c}">${svg(m.typ, '#fff', 15, m.ik)}</div>`,
                               iconSize:[24, 24], iconAnchor:[12, 12], popupAnchor:[0, -10]});
  // godziny otwarcia z OpenStreetMap (opening_hours) – prosty odczyt najczęstszych zapisów: „24/7”, „Mo-Fr 08:00-18:00; Sa 08:00-14:00; Su off”
  const DNI = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'], DPL = ['pn', 'wt', 'śr', 'cz', 'pt', 'sob', 'nd'];
  function godziny(h, teraz = new Date()) {
    if (!h) return null; h = String(h).trim();
    if (h === '24/7') return {txt: 'całą dobę', otwarte: true};
    // dni bez godzin w zapisie OSM są nieczynne; „Su[-1]” – ostatnia niedziela miesiąca (niedziela handlowa)
    const tyg = DNI.map(() => []), ost = {}; let ok = true;
    const D = '(?:Mo|Tu|We|Th|Fr|Sa|Su)';
    const RE = new RegExp(`^((?:${D}(?:\\[-1\\])?(?:-${D})?,?)+)\\s+(off|closed|(?:\\d{1,2}:\\d{2}-\\d{1,2}:\\d{2},?)+)$`);
    for (const reg of h.split(/;|(?<=\d),\s*(?=(?:Mo|Tu|We|Th|Fr|Sa|Su)\b)/).filter(x => x && !/^(Mo|Tu|We|Th|Fr|Sa|Su)$/.test(x)).map(x => x.trim().replace(/,\s*PH\b|\bPH\s*,/g, '').replace(/,\s+/g, ',')).filter(Boolean)) {
      const m = reg.match(RE);
      if (!m) { if (/^PH\b/.test(reg)) continue; ok = false; break; }
      const prz = /off|closed/.test(m[2]) ? [] : m[2].split(',').filter(Boolean).map(x => x.split('-').map(t => { const [g, mi] = t.split(':'); return +g * 60 + +mi; }));
      for (const z of m[1].split(',').filter(Boolean)) {
        if (/\[-1\]/.test(z)) { ost[DNI.indexOf(z.slice(0, 2))] = prz; continue; }
        const [a, b] = z.split('-'); const i = DNI.indexOf(a), j = b ? DNI.indexOf(b) : i;
        for (let k = i; ; k = (k + 1) % 7) { tyg[k] = prz; if (k === j) break; } }
    }
    const fmt = x => Math.floor(x / 60) + ':' + String(x % 60).padStart(2, '0');
    if (!ok) return {txt: h, otwarte: null};
    const opis = [], kl = d => tyg[d].map(p => fmt(p[0]) + '–' + fmt(p[1])).join(', ') || 'nieczynne';
    for (let d = 0; d < 7;) { let e = d; while (e < 6 && kl(e + 1) === kl(d)) e++; opis.push((e > d ? DPL[d] + '–' + DPL[e] : DPL[d]) + ' ' + kl(d)); d = e + 1; }
    for (const [d, p] of Object.entries(ost)) opis.push('ostatnia ' + DPL[d] + ' miesiąca ' + (p.map(q => fmt(q[0]) + '–' + fmt(q[1])).join(', ') || 'nieczynne'));
    const dz = (teraz.getDay() + 6) % 7, min = teraz.getHours() * 60 + teraz.getMinutes();
    const ostatni = teraz.getDate() + 7 > new Date(teraz.getFullYear(), teraz.getMonth() + 1, 0).getDate();
    const dzis = ost[dz] && ostatni ? ost[dz] : tyg[dz];
    const otw = dzis.some(([a, b]) => b > a ? min >= a && min < b : min >= a || min < b);
    let dopisek = ''; if (otw) { const p = dzis.find(([a, b]) => min >= a && min < b); if (p && p[1] - min <= 60) dopisek = ' – zamyka o ' + fmt(p[1]); }
    return {txt: opis.join(' · '), otwarte: otw, dopisek};
  }
  const godzHTML = m => { const g = godziny(m.h); if (!g) return '';
    const st = g.otwarte === true ? `<b style="color:#1E6B3A">otwarte teraz${g.dopisek || ''}</b> · ` : g.otwarte === false ? '<b style="color:#902B38">teraz zamknięte</b> · ' : '';
    return `<div class="k" style="font-size:12.5px;color:#3d4a43">${st}${esc(g.txt)}</div>`; };
  function popup(m) {
    const t = TYP[m.typ] || TYP.ciekawe;
    const zr = m.nick ? `dodał(a): ${esc(m.nick)}${m.data ? ', ' + esc(m.data) : ''}` : m.osm ? 'źródło: OpenStreetMap' : '';
    return `<div class="mjp"><div class="t" style="color:${t.c}">${t.n}</div>${m.nazwa ? `<h3>${esc(m.nazwa)}</h3>` : ''}
      ${m.opis ? `<p>${esc(m.opis)}</p>` : ''}${godzHTML(m)}${zr ? `<div class="k">${zr}</div>` : ''}</div>`;
  }

  // Tworzy warstwy i wczytuje miejsca: stałe (data.js) + zatwierdzone zgłoszenia (api/miejsca.php).
  // korekta z panelu administratora: {u:1} = ukryte, inaczej nadpisane pola (t – rodzaj, n – nazwa, o – opis, lat, lon)
  function popraw(m, K) {
    const k = m.k && K[m.k]; if (!k) return m; if (k.u) return null;
    const z = {...m}; if (k.t) { z.typ = k.t; if (k.t !== m.typ) delete z.ik; } if (k.n !== undefined) z.nazwa = k.n; if (k.o !== undefined) z.opis = k.o;
    if (k.lat != null) { z.lat = k.lat; z.lon = k.lon; } return z;
  }
  function warstwy(map, stale) {
    const L_ = {odpoczynek: L.layerGroup(), serwis: L.layerGroup(), ciekawe: L.layerGroup()};
    const dodaj = m => { if (!m) return; const t = TYP[m.typ]; if (!t) return;
      L.marker([m.lat, m.lon], {icon: icon(m), title: m.nazwa || t.n, zIndexOffset: 200}).bindPopup(popup(m), {maxWidth: 260}).addTo(L_[t.g]); };
    (stale || []).forEach(dodaj);
    fetch((window.HUB_BASE || '') + 'api/miejsca.php', {cache: 'no-store'}).then(r => r.ok ? r.json() : null)
      .then(j => { if (!j) return; const K = j.korekty || {};
        if (Object.keys(K).length) { Object.values(L_).forEach(l => l.clearLayers()); (stale || []).forEach(m => dodaj(popraw(m, K))); }
        (j.miejsca || []).forEach(m => dodaj(popraw(m, K))); }).catch(() => {});
    return L_;
  }
  return {TYP, GRUPY, WARSTWY, svg, icon, popup, warstwy, popraw, esc, godziny};
})();
