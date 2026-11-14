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
    await p.fill('#szukaj', 'GOSiR'); await p.waitForTimeout(500);
    ok(await p.$$eval('#wyniki > *', x => x.length) > 0, 'wyniki wyszukiwania');
    await p.locator('#wyniki button, #wyniki li, #wyniki div').first().click();
    ok(await p.waitForSelector('.staty', {timeout: 15000}).then(() => true, () => false), 'podgląd trasy');
    ok(await p.$eval('.manew', e => e.getBoundingClientRect().height) > 100, 'lista „Po drodze” widoczna');
    await p.click('#b-symstart'); await p.waitForTimeout(3000);
    ok(/km/.test(await p.textContent('#j-zost')), 'jazda (symulacja)');
    ok(!err.length, 'bez błędów JavaScript' + (err.length ? ': ' + err.join(' | ') : ''));
    await c.close();
  }
  await b.close(); console.log(bledy ? `${bledy} błąd(y)` : 'Interfejs OK'); process.exit(bledy ? 1 : 0);
})();
