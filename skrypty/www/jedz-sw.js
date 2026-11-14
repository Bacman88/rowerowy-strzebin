// Service worker nawigacji „Jedź”: najpierw sieć, a bez zasięgu – ostatnia zapisana wersja.
// Zapisujemy tylko pliki aplikacji i dane dróg (nie kafelki mapy), więc trasa liczy się też w lesie bez internetu.
const C = 'jedz-v6';
const PLIKI = ['jedz.html', 'lib/jedz/wspolne.js', 'lib/jedz/graf.js', 'lib/jedz/profil.js', 'lib/jedz/manewry.js', 'lib/jedz/podklad.js', 'lib/uwagi.js', 'lib/jedz.js', 'lib/leaflet.js', 'lib/leaflet.css', 'stan/odcinki.js', 'stan/jedz.js', 'stan/wysokosci.js', 'data.js',
  'lib/ikony.js', 'lib/tabliczka-dane.js', 'lib/tabliczka.js', 'lib/fonts/FiraSansCondensed-SemiBold.ttf', 'ikona-192.png', 'favicon.svg'];
// mapa offline (2,8 MB) – tylko gdy użytkownik ją pobierze (przycisk w Jedź); wtedy zapisujemy ją jak resztę plików
const NA_ZYCZENIE = ['stan/podklad.js'];
self.addEventListener('install', e => { e.waitUntil(caches.open(C).then(c => c.addAll(PLIKI)).catch(() => {})); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== C).map(x => caches.delete(x))))); self.clients.claim(); });
self.addEventListener('fetch', e => {
  const u = new URL(e.request.url);
  if (e.request.method !== 'GET' || u.origin !== location.origin) return;
  const nazwa = u.pathname.split('/').pop() || '';
  const nasz = [...PLIKI, ...NA_ZYCZENIE].some(p => u.pathname.endsWith('/' + p) || u.pathname.endsWith(p));
  if (!nasz) return;   // reszta strony bez zmian
  e.respondWith(fetch(e.request).then(r => { if (r.ok) { const k = r.clone(); caches.open(C).then(c => c.put(e.request, k)); } return r; })
    .catch(() => caches.match(e.request, {ignoreSearch: true})));
});
