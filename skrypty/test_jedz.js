// Testy nawigacji „Jedź” bez przeglądarki: ładuje dane strony i moduły lib/jedz/*.js, liczy znane trasy
// i sprawdza, czy wyniki są w rozsądnych granicach (długość, przebieg, czas, ostrzeżenia).
// Użycie: node test_jedz.js ../out/strona
const path = require('path'), fs = require('fs');
const OUT = path.resolve(process.argv[2] || '../out/strona');
global.window = global; global.document = {getElementById: () => null, querySelector: () => null};
global.localStorage = {getItem: () => null, setItem() {}};
for (const f of ['stan/odcinki.js', 'stan/jedz.js', 'stan/wysokosci.js', 'data.js']) { const p = path.join(OUT, f); if (fs.existsSync(p)) (0, eval)(fs.readFileSync(p, 'utf8')); }
for (const m of ['wspolne', 'graf', 'profil', 'manewry']) (0, eval)(fs.readFileSync(path.join(__dirname, 'www/lib/jedz', m + '.js'), 'utf8'));
const JZ = window.JZ, H = window.HUB;
let bledy = 0;
const ok = (war, opis) => { console.log((war ? '  ok   ' : '  BŁĄD ') + opis); if (!war) bledy++; };
const cel = n => { const c = H.cele.find(c => c.n === n); return [c.lat, c.lon]; };
const STRZEBIN = [50.6164, 18.9056];
const slupki = T => H.posts.filter(q => T.ll.some(x => JZ.dist(x, [q.lat, q.lon]) < 30)).map(q => q.nr);
const nieutw = T => { let m = 0; for (let i = 0; i < T.seg.length; i++) { const st = JZ.stOdc(T.seg[i]); if (st === 'srednia' || st === 'trudna' || st === 'brak') m += T.cum[i + 1] - T.cum[i]; } return m; };
const trasa = (a, b, tryb) => { const T = JZ.trasuj(a, b, {tryb}); if (!T.blad) T.prof = JZ.profil(T); return T; };

console.log('Strzebiń → GOSiR Koszęcin');
const g = trasa(STRZEBIN, cel('GOSiR Koszęcin'), 'bezp');
ok(!g.blad && g.m > 3800 && g.m < 5200, `Bezpieczna: ${(g.m / 1000).toFixed(2)} km (3,8–5,2)`);
ok(slupki(g).length >= 4, `przez słupki przy cmentarzu / w lesie: ${slupki(g).join(', ')}`);
const gs = trasa(STRZEBIN, cel('GOSiR Koszęcin'), 'szosa');
ok(nieutw(gs) < nieutw(g) / 3, `Szosowa omija drogi nieutwardzone: ${Math.round(nieutw(gs))} m wobec ${Math.round(nieutw(g))} m`);
console.log('Strzebiń → Kalety');
const k = trasa(STRZEBIN, cel('Kalety'), 'bezp');
ok(!k.blad && k.m > 6000 && k.m < 9500, `Bezpieczna: ${(k.m / 1000).toFixed(2)} km (6–9,5)`);
ok(k.prof.wys && k.prof.czas > 15 * 60 && k.prof.czas < 45 * 60, `czas ${Math.round(k.prof.czas / 60)} min (15–45), profil wysokości: ${k.prof.wys}`);
const kk = trasa(STRZEBIN, cel('Kalety'), 'krotko');
ok(kk.m <= k.m + 1, `Najkrótsza nie dłuższa od Bezpiecznej: ${(kk.m / 1000).toFixed(2)} km`);
console.log('Start poza drogą');
const P0 = [50.6150, 18.9020], pr = JZ.przyczep(P0);
ok(pr && pr.d < 200, `dojazd prostopadle do najbliższej drogi: ${pr && Math.round(pr.d)} m`);
console.log('Rodzaj roweru (czas tej samej trasy)');
const czas = r => { JZ.ST.RT = r; JZ.ST.R = JZ.ROWERY[r]; return JZ.profil(g).czas; };
const cm = czas('miejski'), cs = czas('szosa'), cg = czas('gorski'); czas('miejski');
ok(cg < cm && cs > cg, `GOSiR lasem: górski ${Math.round(cg / 60)} min < miejski ${Math.round(cm / 60)} min, szosowy ${Math.round(cs / 60)} min`);
console.log('Manewry');
const M = JZ.manewry(g);
ok(M.length > 2 && M[M.length - 1].typ === 'cel', `${M.length} manewrów, ostatni = cel`);
console.log(bledy ? `\n${bledy} błąd(y)` : '\nWszystkie testy przeszły');
process.exit(bledy ? 1 : 0);
