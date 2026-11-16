// Test interfejsu „Jedź” w przeglądarce (Playwright), w dwóch trybach: strona i udawana aplikacja na Androida
// (window.Capacitor) – błąd, który wywraca tylko aplikację, wyjdzie tutaj. Wymaga serwera z out/strona:
//   (cd out/strona && python3 -m http.server 8799) & node skrypty/test_jedz_ui.js http://127.0.0.1:8799/
const {chromium, devices} = require('playwright');
const URL = (process.argv[2] || 'http://127.0.0.1:8799/') + 'jedz.html';
(async () => {
  let bledy = 0; const b = await chromium.launch();
  for (const tryb of ['strona', 'aplikacja']) {
    const c = await b.newContext({...devices['Pixel 7'], geolocation: {latitude: 50.6164, longitude: 18.9056}, permissions: ['geolocation']});
    const p = await c.newPage(), err = []; p.on('pageerror', e => err.push(e.message));
    await p.route(/tile\.openstreetmap|fonts\.(googleapis|gstatic)/, r => r.abort());
    if (tryb === 'aplikacja') await p.addInitScript(() => { window.Capacitor = {isNativePlatform: () => true, Plugins: {}, registerPlugin: () => null}; });
    await p.goto(URL); await p.waitForTimeout(1500);
    const ok = (w, o) => { console.log(`  ${w ? 'ok  ' : 'BŁĄD'} [${tryb}] ${o}`); if (!w) bledy++; };
    ok(await p.$$eval('#chipy button', x => x.length) >= 5, 'szybki wybór');
    await p.click('#pobl-chipy button[data-k=apteka]');
    ok(await p.waitForSelector('#pobl-lista:not(.hide) button', {timeout: 8000}).then(() => true, () => false), 'w pobliżu: najbliższe apteki');
    await p.click('#pobl-chipy button[data-k=apteka]');
    await p.fill('#szukaj', '49'); await p.waitForTimeout(300);
    ok(/Węzeł 49/.test(await p.textContent('#wyniki > :first-child')), 'szukanie węzła po numerze („49”)');
    await p.fill('#szukaj', 'Liswar'); await p.waitForTimeout(300);
    ok(/Liswarciański/.test(await p.textContent('#wyniki > :first-child')), 'szlak w wyszukiwarce');
    await p.fill('#szukaj', ''); await p.waitForTimeout(200);
    await p.fill('#szukaj', 'GOSiR'); await p.waitForTimeout(500);
    ok(await p.$$eval('#wyniki > *', x => x.length) > 0, 'wyniki wyszukiwania');
    await p.locator('#wyniki button, #wyniki li, #wyniki div').first().click();
    ok(await p.waitForSelector('.staty', {timeout: 15000}).then(() => true, () => false), 'podgląd trasy');
    ok(await p.$eval('.manew', e => e.getBoundingClientRect().height) > 100, 'lista „Po drodze” widoczna');
    await p.click('#b-poi'); ok(await p.$$eval('#poiu .poik input', x => x.length) >= 10, 'wybór miejsc na mapie');
    await p.click('#poi-none'); ok(await p.$$eval('.leaflet-marker-pane .mj', x => x.length) === 0, 'miejsca ukryte po „Żadne”');
    await p.click('#poi-all'); await p.click('#poi-ok');
    await p.click('#b-symstart'); await p.waitForTimeout(3000);
    ok(/km/.test(await p.textContent('#j-zost')), 'jazda (symulacja)');
    // ocena drogi w trakcie jazdy: gwiazdka → 4 przyciski → podziękowanie, ocena w kolejce do wysłania
    await p.route('**/api/zglos.php', r => r.fulfill({contentType: 'application/json', body: '{"ok":true,"id":1}'}));
    await p.click('#b-ocen'); ok(await p.isVisible('#ocs .oc4 button[data-k=trudna]'), 'ocena drogi w trakcie jazdy – przyciski');
    await p.click('#ocs .oc4 button[data-k=trudna]'); ok(/Dziękujemy/.test(await p.textContent('#ocs')), 'ocena drogi w trakcie jazdy – zapisana');
    await p.waitForTimeout(1900);
    // przybliżanie z animacją w trakcie jazdy nie może rozjechać trasy i mapy (kreska trasy przechodzi przez znacznik „ja”)
    for (let i = 0; i < 4; i++) { await p.mouse.move(206, 500); await p.mouse.wheel(0, i % 2 ? 300 : -300); await p.waitForTimeout(350); }
    await p.waitForTimeout(1500);
    const odl = await p.evaluate(() => { const j = document.querySelector('.ja'); if (!j) return 999; const r = j.getBoundingClientRect(), cx = r.x + r.width / 2, cy = r.y + r.height / 2; let best = 1e9;
      document.querySelectorAll('.leaflet-overlay-pane path').forEach(el => { const L = el.getTotalLength(); if (L < 50) return; const m = el.getScreenCTM();
        for (let s = 0; s <= L; s += 4) { const q = el.getPointAtLength(s); best = Math.min(best, Math.hypot(m.a * q.x + m.c * q.y + m.e - cx, m.b * q.x + m.d * q.y + m.f - cy)); } }); return Math.round(best); });
    ok(odl <= 8, `trasa zgadza się z mapą po przybliżaniu w trakcie jazdy (${odl} px)`);
    // po „Zakończ” podgląd ma liczyć trasę od miejsca, w którym jesteś (symulacja przejechała kawałek)
    const km0 = await p.evaluate(() => JZ.stan.T.m); await p.click('#b-stop'); await p.waitForSelector('.staty');
    const km1 = await p.evaluate(() => JZ.stan.T.m);
    ok(km1 < km0 - 15, `po zakończeniu trasa od bieżącego miejsca (${Math.round(km0)} m → ${Math.round(km1)} m)`);
    ok(!err.length, 'bez błędów JavaScript' + (err.length ? ': ' + err.join(' | ') : ''));
    await c.close();
  }
  await b.close(); console.log(bledy ? `${bledy} błąd(y)` : 'Interfejs OK'); process.exit(bledy ? 1 : 0);
})();
