"""Załącznik A4: wzór drogowskazu (budowa tabliczki, kółka tras) i przykładowy montaż na istniejącym słupku z nazwą ulicy.
Tabliczki rysuje ten sam kod co strona (www/lib/tabliczka.js + dane generatora V22 z <strona>/lib/tabliczka-dane.js).
Użycie (wywołuje strona.py): python3 wzor_montazu.py <katalog strony> <plik PDF>"""
import json, os, sys
from playwright.sync_api import sync_playwright

S, OUT = sys.argv[1:3]
H = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(f"{H}/../out/tabliczki/manifest.json"))
D = json.load(open(f"{H}/signs_prop.json"))
NR = 11                                               # słupek z nazwami ulic, 4 tabliczki, trasy 1 i 3
post = next(p for p in D["posts"] if p["nr"] == NR)
TAB = [dict(d=e["dir"], cat=e.get("cat", "blue"), e=e["ent"]) for e in M[str(NR)]]
# do opisu budowy: tabliczka z dwoma celami i kółkami przy obu (słupek 3: Bukowiec / Kalety)
_ex = [dict(d=e["dir"], cat=e.get("cat", "blue"), e=e["ent"]) for n in ("3", "25", "11") for e in M.get(n, [])]
EX = next((t for t in _ex if len(t["e"]) == 2 and all(x[3] for x in t["e"])), TAB[0])
ROUTES = sorted({r for e in M[str(NR)] for rr in e["routes"] for r in rr}, key=lambda x: (len(x), x))
from trasy_kolory import KOLORY
KOL = {k: v[:2] for k, v in KOLORY.items()}

html = f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">
<style>
@font-face{{font-family:'Fira Sans Condensed';font-weight:600;src:url(file://{os.path.abspath(H + '/../fonts/FiraSansCondensed-SemiBold.ttf')})}}
@page{{size:A4;margin:0}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:Inter,'DejaVu Sans',Arial,sans-serif;color:#1d2a23;font-size:9.6pt;line-height:1.38}}
.pg{{width:210mm;height:297mm;padding:13mm 14mm 11mm;position:relative}}
.k{{font-size:7.8pt;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#a0700f;margin:0 0 1.5mm}}
h1{{font-size:17pt;line-height:1.15;margin:0 0 1.5mm;color:#1d3b30}}
.sub{{margin:0 0 5mm;color:#4b5d53}}
h2{{font-size:11.5pt;margin:5mm 0 2mm;color:#1d3b30}}
.anat{{display:grid;grid-template-columns:96mm 1fr;gap:6mm;align-items:center}}
.ap{{position:relative}}.ap svg,.pl svg{{width:100%;height:auto;display:block}}
.co{{position:absolute;transform:translate(-50%,-50%);width:5.4mm;height:5.4mm;border-radius:50%;background:#e9b949;color:#1d2a23;font:800 7.5pt/4.4mm Arial,sans-serif;text-align:center;border:.5mm solid #fff}}
ol.key{{list-style:none;margin:0;padding:0;display:grid;gap:1.2mm;font-size:8.6pt;color:#4b5d53}}
ol.key li{{display:grid;grid-template-columns:5.4mm 1fr;gap:2mm}}ol.key .co{{position:static;transform:none}}
ol.key b{{color:#1d2a23}}
.mont{{display:grid;grid-template-columns:118mm 1fr;gap:5mm;align-items:start}}
.rys{{position:relative;border:.3mm solid #e2dccb;border-radius:3mm;background:#faf8f2;height:142mm;overflow:hidden}}
.uw{{font-size:8.4pt;color:#4b5d53}}.uw ul{{margin:0;padding-left:4mm}}.uw li{{margin-bottom:1.4mm}}.uw b{{color:#1d2a23}}
.foot{{position:absolute;left:14mm;right:14mm;bottom:8mm;font-size:7.4pt;color:#6b7a70;display:flex;justify-content:space-between;border-top:.3mm solid #e2dccb;padding-top:2mm}}
</style></head><body><div class="pg">
<p class="k">Załącznik · HUB rowerowy Strzebiń – lokalny system informacji kierunkowej dla rowerzystów</p>
<h1>Wzór drogowskazu i montaż na istniejącym słupku z nazwą ulicy</h1>
<p class="sub">Tabliczka wskazuje kierunek, cel i odległość. Kolorowe kółka z numerami tras są oznaczeniem pomocniczym. Większość tabliczek w Strzebiniu może zawisnąć na stojących już słupkach z nazwami ulic, bez nowych konstrukcji.</p>

<h2>1. Budowa tabliczki (800 × 200 mm)</h2>
<div class="anat"><div class="ap" id="anat"></div>
<ol class="key">
<li><span class="co">1</span><span><b>Strzałka</b> – tabliczka sama jest strzałką; grot wskazuje drogę.</span></li>
<li><span class="co">2</span><span><b>Rower</b> – informacja dla rowerzystów.</span></li>
<li><span class="co">3</span><span><b>Cel</b> – miejscowość lub obiekt.</span></li>
<li><span class="co">4</span><span><b>Kółka tras</b> Ø 31 mm, najwyżej 4 – w tę stronę jadą trasy pokazowe o tych numerach. Naklejki, pomocnicze.</span></li>
<li><span class="co">5</span><span><b>Odległość</b> po drogach, co 0,1 km.</span></li>
<li><span class="co">6</span><span><b>Drugi cel</b> w tym samym kierunku (dalszy pod bliższym).</span></li>
</ol></div>

<h2>2. Przykład: słupek nr {NR} – {post['loc']} (istniejący słupek z nazwami ulic)</h2>
<div class="mont">
<div class="rys"><svg id="rys" viewBox="0 0 118 142" width="118mm" height="142mm"></svg></div>
<div class="uw"><ul>
<li><b>Tylko słupki z nazwami ulic</b> (białe tabliczki z niebieskim napisem i herbem gminy), na których nie ma znaków drogowych. Drogowskazy wiszą tuż pod nazwami ulic i ich nie zasłaniają.</li>
<li><b>Mocowanie</b>: obejmy stalowe dobrane do średnicy rury (do zmierzenia w terenie, typowo Ø 48–60 mm) – tak jak dziś przykręcone są nazwy ulic; śruby nierdzewne M6/M8 z podkładkami EPDM; 2 otwory Ø 6 mm w strefie mocowania (60 mm od nasady).</li>
<li><b>Tabliczki</b> po obu stronach słupka: ze strzałką w lewo – po lewej, w prawo – po prawej; każda ustawiona wzdłuż swojej drogi.</li>
<li><b>Materiał</b>: płyta kompozytowa (dibond) 3 mm cięta po obrysie, druk z obu stron na folii odpornej na UV.</li>
<li><b>Naklejka węzła</b> z numerem słupka i <b>paski tras</b> (te same kolory i numery co kółka) na wysokości ok. 1,7 m.</li>
<li><b>Wysokości</b> oszacowane ze zdjęć istniejących słupków (rura ok. 3 m, nazwy ulic ok. 750 × 250 mm na szczycie rury, ich dolna krawędź ok. 2,7 m) – do zmierzenia w terenie. Pod nazwami ulic mieszczą się dwa rzędy drogowskazów, dolna krawędź ok. 2,2 m; wymagana wysokość do uzgodnienia z zarządcą drogi.</li>
<li>Stan techniczny, nośność i własność każdego słupka – do potwierdzenia przed montażem.</li>
</ul></div>
</div>
<div class="foot"><span>Propozycja do uzgodnienia · wzór „HUB Strzebiń” (generator V22) · listopad 2026</span><span>rowerowy-strzebin.smart-ant.pl</span></div>
</div>
<script src="file://{os.path.abspath(S + '/lib/tabliczka-dane.js')}"></script>
<script src="file://{os.path.abspath(H + '/www/lib/tabliczka.js')}"></script>
<script>
const TAB = {json.dumps(TAB, ensure_ascii=False)}, EX = {json.dumps(EX, ensure_ascii=False)}, KOL = {json.dumps(KOL)}, ROUTES = {json.dumps(ROUTES)}, NR = {NR};
document.fonts.load("600 40px 'Fira Sans Condensed'").then(() => {{
  const T = window.TABLICZKA;
  // 1. budowa: tabliczka z dwoma celami i kółkami (pierwsza z kółkami na obu celach, inaczej dowolna z kółkami)
  const ex = EX;
  const W = 800, lay = T.bestLayout(ex.d, W, ex.e), box = document.getElementById('anat');
  box.innerHTML = T.svg(ex.d, W, ex.cat, ex.e).svg;
  if (lay) {{
    const sz = lay.size, x0 = ex.d === 'left' ? 154 : 54, nameX = x0 + 12 + 128 + 24, kmR = x0 + (W - 208) - 12 - 16, it = lay.items, top0 = it[0].lines[0][1] - sz * .72;
    // znaczniki na górnej i dolnej krawędzi tabliczki, nad opisywanym elementem (nie zasłaniają tekstu)
    const pts = [[ex.d === 'left' ? 100 : W - 100, 34, 1], [x0 + 76, 8, 2], [nameX + 30, 8, 3]];
    const dIt = it.find(x => x.dots); if (dIt) pts.push([dIt.dots[0] + dIt.dots[2] / 2, 8, 4]);
    pts.push([kmR - 45, 8, 5]); if (it[1]) pts.push([nameX + 30, 192, 6]);
    for (const [x, y, n] of pts) {{ const c = document.createElement('span'); c.className = 'co'; c.textContent = n; c.style.left = (x + 2) / (W + 4) * 100 + '%'; c.style.top = (y + 2) / 204 * 100 + '%'; box.appendChild(c); }}
  }}
  // 2. rysunek montażu – skala 1:25 (1 mm rysunku = 25 mm), słupek na środku, ziemia na dole
  const svg = document.getElementById('rys'), NS = 'http://www.w3.org/2000/svg', S_ = 1 / 25, X = 59, G = 134;
  const y = m => G - m * 1000 * S_;            // wysokość w metrach -> y rysunku
  const el = (t, a, txt) => {{ const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (txt != null) e.textContent = txt; svg.appendChild(e); return e; }};
  el('line', {{x1: 4, x2: 114, y1: G, y2: G, stroke: '#9a9078', 'stroke-width': .5}});
  el('rect', {{x: 4, y: G, width: 110, height: 6, fill: '#e8e1cf'}});
  el('rect', {{x: X - 1.2, y: y(3.0), width: 2.4, height: G - y(3.0), fill: '#9aa3a8'}});
  // nazwy ulic (istniejące)
  const ulice = ['ul. Wojska Polskiego', 'ul. Kościuszki'];
  // jak w Strzebiniu: białe tabliczki z niebieską obwódką i napisem, strzałka na zewnętrznym końcu, herb gminy przy słupku;
  // na szczycie rury, po obu stronach (jak ul. Lubliniecka / Sienkiewicza)
  ulice.forEach((u, i) => {{ const top = y(2.98), w = 750 * S_, h = 250 * S_, x = i ? X + 1.2 : X - 1.2 - w, lewa = !i;
    el('rect', {{x, y: top, width: w, height: h, rx: .3, fill: '#fff', stroke: '#1f4fa0', 'stroke-width': .35}});
    el('path', {{d: lewa ? `M ${{x + 1}} ${{top + h / 2}} l 2.2 -1.7 v 3.4 z` : `M ${{x + w - 1}} ${{top + h / 2}} l -2.2 -1.7 v 3.4 z`, fill: '#1f4fa0'}});
    const hx = lewa ? x + w - 3.6 : x + 1;
    el('path', {{d: `M ${{hx}} ${{top + 2}} h 2.6 v 2.6 q 0 2 -1.3 2.8 q -1.3 -.8 -1.3 -2.8 z`, fill: '#1f4fa0'}});
    const tx = el('text', {{x: x + w / 2 + (lewa ? -.8 : .8), y: top + 6, 'text-anchor': 'middle', fill: '#1f4fa0', 'font-size': 3, 'font-family': 'Arial', 'font-weight': 700}}, u);
    if (tx.getComputedTextLength() > w - 10) {{ tx.setAttribute('textLength', w - 10); tx.setAttribute('lengthAdjust', 'spacingAndGlyphs'); }}
    el('rect', {{x: X - 1.9, y: top + 4.4, width: 3.8, height: 1.4, rx: .3, fill: '#3b4448'}}); }});
  el('text', {{x: X, y: y(2.98) - 2, 'text-anchor': 'middle', fill: '#4b5d53', 'font-size': 2.5, 'font-family': 'Arial'}}, 'istniejące nazwy ulic');
  // tabliczki: pary lewa/prawa na tych samych wysokościach
  const L_ = TAB.filter(t => t.d === 'left'), R_ = TAB.filter(t => t.d === 'right'), rows = Math.max(L_.length, R_.length);
  const pw = 800 * S_, ph = 200 * S_;
  for (let r = 0; r < rows; r++) {{
    const top = y(2.68 - r * 0.23);
    for (const [t, side] of [[L_[r], 'l'], [R_[r], 'r']]) {{
      if (!t) continue;
      const g = el('g', {{}}); const x = side === 'l' ? X - 1.2 - pw : X + 1.2;
      const f = document.createElementNS(NS, 'foreignObject'); f.setAttribute('x', x); f.setAttribute('y', top); f.setAttribute('width', pw); f.setAttribute('height', ph + .2);
      f.innerHTML = '<div xmlns="http://www.w3.org/1999/xhtml" class="pl" style="width:' + pw + 'px">' + T.svg(t.d, 800, t.cat, t.e).svg + '</div>'; svg.appendChild(f);
      for (const dy of [.22, .66]) el('rect', {{x: X - 1.9, y: top + ph * dy, width: 3.8, height: 1.4, rx: .3, fill: '#3b4448'}});
    }}
  }}
  // naklejka węzła i paski tras
  const yn = y(1.72); el('rect', {{x: X - 2.4, y: yn, width: 4.8, height: 3.2, fill: '#fff', stroke: '#c9c1ad', 'stroke-width': .2}});
  el('circle', {{cx: X, cy: yn + 1.6, r: 1.3, fill: '#00838F'}}); el('text', {{x: X, y: yn + 2.15, 'text-anchor': 'middle', fill: '#fff', 'font-size': 1.5, 'font-family': 'Arial', 'font-weight': 700}}, NR);
  ROUTES.forEach((r, i) => {{ const k = KOL[r] || ['#555', 'white'], yb = yn + 3.4 + i * 1.3;
    el('rect', {{x: X - 1.2, y: yb, width: 2.4, height: 1.2, fill: k[0]}}); el('text', {{x: X, y: yb + .95, 'text-anchor': 'middle', fill: k[1], 'font-size': 1, 'font-family': 'Arial', 'font-weight': 700}}, r); }});
  // wymiary (orientacyjne)
  const dim = (m, t) => {{ el('line', {{x1: 96, x2: 101, y1: y(m), y2: y(m), stroke: '#a0700f', 'stroke-width': .25}}); el('text', {{x: 102, y: y(m) + 1.2, fill: '#a0700f', 'font-size': 3, 'font-family': 'Arial'}}, t); }};
  dim(3.0, '≈ 3,0 m'); dim(2.73, '≈ 2,7 m'); dim(2.23, '≈ 2,2 m'); dim(1.72, '≈ 1,7 m'); dim(0, '0');
  el('text', {{x: 6, y: G - 3, fill: '#4b5d53', 'font-size': 3, 'font-family': 'Arial'}}, 'skala ok. 1:25 · tabliczki 800 × 200 mm');
  el('text', {{x: X - 3, y: y(2.08), 'text-anchor': 'end', fill: '#4b5d53', 'font-size': 2.7, 'font-family': 'Arial'}}, '← strzałka w lewo: po lewej');
  el('text', {{x: X + 3, y: y(2.08), 'text-anchor': 'start', fill: '#4b5d53', 'font-size': 2.7, 'font-family': 'Arial'}}, 'po prawej: strzałka w prawo →');
  el('text', {{x: X + 3.5, y: yn + 4.5, fill: '#4b5d53', 'font-size': 2.6, 'font-family': 'Arial'}}, '← węzeł ' + NR + ' i paski tras');
  document.body.dataset.ok = 1;
}});
</script></body></html>"""
tmp = os.path.abspath(OUT + ".html")
open(tmp, "w").write(html)
with sync_playwright() as pw_:
    b = pw_.chromium.launch(); p = b.new_page()
    p.goto("file://" + tmp); p.wait_for_selector("body[data-ok]", timeout=15000); p.wait_for_timeout(300)
    p.pdf(path=OUT, format="A4", print_background=True, margin=dict(top="0", bottom="0", left="0", right="0"))
    b.close()
os.remove(tmp)
print("wzór i montaż:", OUT)
