// „Jedź” – pogoda i światło dnia (17.11.2026).
//  • wschód i zachód słońca liczone w telefonie (wzór NOAA, bez internetu) – czy zdążysz przed zmrokiem;
//  • prognoza godzinowa z Open-Meteo (api.open-meteo.com, bez klucza): start (teraz), punkty po drodze co ~10 km
//    (na godzinę, o której tam będziesz) i cel (na godzinę przyjazdu); wiatr względem kierunku jazdy (w twarz / w plecy / z boku).
//  Do Open-Meteo wysyłamy tylko współrzędne zaokrąglone do 0,01° (ok. 1 km) – bez danych o osobie. Bez internetu: samo słońce.
(() => {
  'use strict';
  const JZ = window.JZ = window.JZ || {};
  const {rad, brg, esc, LS} = JZ;
  // 18.11.2026: przełącznik „Prognoza pogody” (domyślnie wł.) – wyłączona: nic nie idzie do Open-Meteo, zostaje samo słońce (liczone w telefonie)
  const wlaczona = () => LS.get('pogoda', true);
  // ---------- słońce ----------
  function slonce(lat, lon, kiedy = new Date()) {
    const dzien = new Date(kiedy); dzien.setHours(12, 0, 0, 0);
    const Jd = dzien.getTime() / 864e5 + 2440587.5, n = Math.ceil(Jd - 2451545 + 0.0008), Js = n - lon / 360;
    const M = (357.5291 + 0.98560028 * Js) % 360, Mr = M * rad;
    const C = 1.9148 * Math.sin(Mr) + 0.02 * Math.sin(2 * Mr) + 0.0003 * Math.sin(3 * Mr);
    const l = ((M + C + 180 + 102.9372) % 360) * rad;
    const Jt = 2451545 + Js + 0.0053 * Math.sin(Mr) - 0.0069 * Math.sin(2 * l);
    const sd = Math.sin(l) * Math.sin(23.4397 * rad), cd = Math.cos(Math.asin(sd));
    const cw = (Math.sin(-0.833 * rad) - Math.sin(lat * rad) * sd) / (Math.cos(lat * rad) * cd);
    if (cw > 1 || cw < -1) return null;
    const w = Math.acos(cw) / rad / 360, nadate = J => new Date((J - 2440587.5) * 864e5);
    return {wsch: nadate(Jt - w), zach: nadate(Jt + w)};
  }
  const hm = d => d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
  const dl = ms => { const m = Math.round(Math.abs(ms) / 6e4); return m < 60 ? m + ' min' : Math.floor(m / 60) + ' h' + (m % 60 ? ' ' + m % 60 + ' min' : ''); };
  // jedno zdanie o świetle dnia dla jazdy od teraz przez czas (s)
  function swiatlo(lat, lon, czas) {
    const S = slonce(lat, lon); if (!S) return '';
    const t0 = Date.now(), t1 = t0 + czas * 1000, wz = `🌅 wschód ${hm(S.wsch)} · 🌇 zachód ${hm(S.zach)}`;
    if (t0 < S.wsch.getTime()) return `${wz} – jeszcze ciemno, włącz światła.`;
    if (t0 > S.zach.getTime()) return `${wz} – już po zmroku, jedź ze światłami.`;
    if (t1 > S.zach.getTime()) return `${wz} – dojedziesz ok. ${hm(new Date(t1))}, ostatnie ${dl(t1 - S.zach.getTime())} po zmroku – weź światła.`;
    return `${wz} – zdążysz za dnia (zapas ${dl(S.zach.getTime() - t1)}).`;
  }
  // ---------- prognoza ----------
  const KOD = c => c === 0 ? ['☀️', 'pogodnie'] : c <= 2 ? ['🌤', 'małe zachmurzenie'] : c === 3 ? ['☁️', 'pochmurno'] : c <= 48 ? ['🌫', 'mgła']
    : c <= 57 ? ['🌦', 'mżawka'] : c <= 67 ? ['🌧', c >= 66 ? 'marznący deszcz' : 'deszcz'] : c <= 77 ? ['🌨', 'śnieg'] : c <= 82 ? ['🌦', 'przelotny deszcz']
    : c <= 86 ? ['🌨', 'przelotny śnieg'] : ['⛈', 'burza'];
  const KIER = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'], KIERPL = {N: 'płn.', NE: 'płn.-wsch.', E: 'wsch.', SE: 'płd.-wsch.', S: 'płd.', SW: 'płd.-zach.', W: 'zach.', NW: 'płn.-zach.'};
  const pam = new Map();   // klucz współrzędnych → {t, d} (30 min)
  async function pobierz(pkt) {
    if (!wlaczona()) throw new Error('pogoda wyłączona');
    const kl = [...new Set(pkt.map(p => p[0].toFixed(2) + ',' + p[1].toFixed(2)))], brak = kl.filter(k => !(pam.get(k) && Date.now() - pam.get(k).t < 18e5));
    if (brak.length) {
      const u = 'https://api.open-meteo.com/v1/forecast?latitude=' + brak.map(k => k.split(',')[0]).join(',') + '&longitude=' + brak.map(k => k.split(',')[1]).join(',')
        + '&hourly=temperature_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m'
        + '&timezone=GMT&timeformat=unixtime&forecast_days=3&wind_speed_unit=kmh';
      const r = await fetch(u); if (!r.ok) throw new Error('pogoda ' + r.status);
      let j = await r.json(); if (!Array.isArray(j)) j = [j];
      brak.forEach((k, i) => pam.set(k, {t: Date.now(), d: j[i].hourly}));
    }
    return pkt.map(p => { const h = pam.get(p[0].toFixed(2) + ',' + p[1].toFixed(2)).d, ts = p[2] / 1000;
      let i = 0, bd = Infinity; h.time.forEach((t, k) => { const d = Math.abs(t - ts); if (d < bd) { bd = d; i = k; } });
      return {temp: h.temperature_2m[i], odcz: h.apparent_temperature[i], pp: h.precipitation_probability[i], op: h.precipitation[i], kod: h.weather_code[i],
        wiatr: h.wind_speed_10m[i], kw: h.wind_direction_10m[i], por: h.wind_gusts_10m[i]}; });
  }
  // wiatr względem kierunku jazdy b (stopnie): kw – skąd wieje
  function wiatrOpis(w, b) {
    if (w.wiatr < 8) return 'słaby wiatr';
    const k = KIER[Math.round(w.kw / 45) % 8], roz = Math.abs(((w.kw - b) % 360 + 540) % 360 - 180);
    const wzgl = b == null ? '' : roz < 50 ? ', w twarz' : roz > 130 ? ', w plecy' : ', z boku';
    return `wiatr ${Math.round(w.wiatr)} km/h z ${KIERPL[k]}${w.por > w.wiatr + 15 ? ' (porywy ' + Math.round(w.por) + ')' : ''}${wzgl}`;
  }
  const linia = w => { const [ik, op] = KOD(w.kod); return `${ik} <b>${Math.round(w.temp)}°C</b> ${op}${w.pp >= 20 ? `, opady ${w.pp}%` : ''}`; };
  // punkty trasy do prognozy: start, co ~10 km (najwyżej 4), cel – [lat, lon, czas ms, opis, kierunek jazdy]
  function punkty(T) {
    const czas = d => JZ.czasDo(T, d), t0 = Date.now(), M = T.m, n = Math.min(4, Math.floor(M / 10000)), out = [];
    const kier = d => brg(JZ.wDal(T, Math.max(0, Math.min(M - 1, d - 150))), JZ.wDal(T, Math.min(M, d + 150)));
    out.push([...T.ll[0], t0, 'Start, teraz', kier(0)]);
    for (let k = 1; k <= n; k++) { const d = M * k / (n + 1); out.push([...JZ.wDal(T, d), t0 + czas(d) * 1000, `po ${Math.round(d / 1000)} km, ok. ${hm(new Date(t0 + czas(d) * 1000))}`, kier(d)]); }
    out.push([...T.ll[T.ll.length - 1], t0 + czas(M) * 1000, `Na miejscu, ok. ${hm(new Date(t0 + czas(M) * 1000))}`, kier(M)]);
    return out;
  }
  // blok w podglądzie trasy: światło dnia od razu, prognoza po pobraniu
  async function blok(el, T) {
    if (!el) return; const [la, lo] = T.ll[0];
    el.innerHTML = `<div class="sek">Pogoda i światło dnia</div><div class="pg-sl">${esc(swiatlo(la, lo, T.prof.czas))}</div><div class="pg-lista"><div class="pg-m">Pobieram prognozę…</div></div>`;
    const prz = `<label class="pg-prz"><input type="checkbox" id="pg-wl"${wlaczona() ? ' checked' : ''}> Prognoza pogody <span>(wysyła do Open-Meteo kilka punktów trasy, zaokrąglonych do ok. 1 km)</span></label>`;
    el.insertAdjacentHTML('beforeend', prz);
    el.querySelector('#pg-wl').onchange = e => { LS.set('pogoda', e.target.checked); blok(el, T); };
    if (!wlaczona()) { el.querySelector('.pg-lista').innerHTML = '<div class="pg-m">Prognoza wyłączona – nic nie wysyłamy. Wschód i zachód słońca liczymy w telefonie.</div>'; return; }
    if (!navigator.onLine) { el.querySelector('.pg-lista').innerHTML = '<div class="pg-m">Prognoza pogody potrzebuje internetu.</div>'; return; }
    try {
      const P = punkty(T), W = await pobierz(P); if (!el.isConnected) return;
      const deszcz = W.some(w => w.pp >= 60 || w.op >= 0.5), mroz = W.some(w => w.temp <= 0);
      el.querySelector('.pg-lista').innerHTML = P.map((p, i) => `<div class="pg-w"><span class="pg-k">${esc(p[3])}</span><span>${linia(W[i])}</span><span class="pg-m">${esc(wiatrOpis(W[i], p[4]))}${Math.abs(W[i].odcz - W[i].temp) >= 3 ? ` · odczuwalna ${Math.round(W[i].odcz)}°C` : ''}</span></div>`).join('')
        + (deszcz ? '<div class="pg-uw">☔ Na trasie spore szanse na deszcz – weź kurtkę przeciwdeszczową.</div>' : '')
        + (mroz ? '<div class="pg-uw">🧊 Temperatura w okolicy zera – uwaga na oblodzenie, zwłaszcza na mostkach i w lesie.</div>' : '')
        + '<div class="pg-m" style="margin-top:4px">Prognoza: Open-Meteo.com</div>';
    } catch (e) { if (el.isConnected) el.querySelector('.pg-lista').innerHTML = '<div class="pg-m">Nie udało się pobrać prognozy – spróbuj za chwilę.</div>'; }
  }
  // w trakcie jazdy: krótka informacja dla miejsca, w którym będziesz za ~30 min (deszcz, zmrok)
  async function wJezdzie(T, wzdluz) {
    const M = T.m, t0 = Date.now(), cz = d => JZ.czasDo(T, d), d30 = (() => { let d = wzdluz; while (d < M && cz(d) - cz(wzdluz) < 1800) d += 250; return Math.min(d, M); })();
    const tu = JZ.wDal(T, wzdluz), tam = JZ.wDal(T, d30), t30 = t0 + (cz(d30) - cz(wzdluz)) * 1000;
    const S = slonce(tu[0], tu[1]), doCelu = (cz(M) - cz(wzdluz)) * 1000;
    let zmrok = ''; if (S && t0 < S.zach.getTime() && t0 + doCelu > S.zach.getTime()) zmrok = ` · 🌇 zachód ${hm(S.zach)}`;
    if (!navigator.onLine || !wlaczona()) return {txt: zmrok.slice(3), zach: S && S.zach};
    try {
      const [a, b] = await pobierz([[...tu, t0], [...tam, t30]]);
      const [ik] = KOD(a.kod); let txt = `${ik} ${Math.round(a.temp)}°C`;
      if (b.pp >= 60 && a.pp < 60) txt += ` · deszcz za ok. ${dl(t30 - t0)} (${b.pp}%)`; else if (a.pp >= 60) txt += ` · opady ${a.pp}%`;
      return {txt: txt + zmrok, zach: S && S.zach};
    } catch (e) { console.warn("pogoda", e); return {txt: zmrok.slice(3), zach: S && S.zach}; }
  }
  Object.assign(JZ, {pogoda: {slonce, swiatlo, blok, wJezdzie, pobierz}});
})();
