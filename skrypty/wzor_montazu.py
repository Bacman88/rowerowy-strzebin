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
NR2 = 31                                              # nowy słupek w lesie (bez nazw ulic), tabliczki po obu stronach, trasa 3
post2 = next(p for p in D["posts"] if p["nr"] == NR2)
TAB2 = [dict(d=e["dir"], cat=e.get("cat", "blue"), e=e["ent"]) for e in M[str(NR2)]]
ROUTES2 = sorted({r for e in M[str(NR2)] for rr in e["routes"] for r in rr}, key=lambda x: (len(x), x))
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
.rys{{position:relative;border:.3mm solid #e2dccb;border-radius:3mm;background:#faf8f2;height:96mm;overflow:hidden}}
.uw{{font-size:7.7pt;color:#4b5d53;margin-top:3mm;columns:2;column-gap:7mm}}.uw ul{{margin:0;padding-left:4mm}}.uw li{{margin-bottom:1.2mm;break-inside:avoid}}.uw b{{color:#1d2a23}}
.foot{{position:absolute;left:14mm;right:14mm;bottom:8mm;font-size:7.4pt;color:#6b7a70;display:flex;justify-content:space-between;border-top:.3mm solid #e2dccb;padding-top:2mm}}
</style></head><body><div class="pg">
<p class="k">Załącznik · HUB rowerowy Strzebiń – lokalny system informacji kierunkowej dla rowerzystów</p>
<h1>Wzór drogowskazu i montaż na słupku</h1>
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

<h2>2. Montaż: a) na istniejącym słupku z nazwami ulic, b) na nowym słupku w lesie</h2>
<div class="rys"><svg id="rys" viewBox="0 0 182 96" width="182mm" height="96mm"></svg></div>
<div class="uw"><ul>
<li><b>a) Istniejące słupki:</b> tylko słupki z nazwami ulic (białe tabliczki z niebieskim napisem i herbem gminy), na których nie ma znaków drogowych. Drogowskazy wiszą tuż pod nazwami ulic i ich nie zasłaniają.</li>
<li><b>Mocowanie</b>: obejmy stalowe dobrane do średnicy rury (do zmierzenia w terenie, typowo Ø 48–60 mm) – tak jak dziś przykręcone są nazwy ulic; śruby nierdzewne M6/M8 z podkładkami EPDM; 2 otwory Ø 6 mm w strefie mocowania (60 mm od nasady).</li>
<li><b>Tabliczki</b> po obu stronach rury, każda ustawiona wzdłuż swojej drogi.</li>
<li><b>Materiał</b>: płyta kompozytowa (dibond) 3 mm cięta po obrysie, druk z obu stron na folii odpornej na UV.</li>
<li><b>Naklejka węzła</b> z numerem słupka i <b>paski tras</b> (te same kolory i numery co kółka) na wysokości ok. 1,7 m.</li>
<li><b>Wysokości</b> oszacowane ze zdjęć (rura ok. 3 m, nazwy ulic na szczycie, dolna krawędź ok. 2,8 m); pod nimi dwa rzędy drogowskazów do ok. 2,3 m – do zmierzenia i uzgodnienia z zarządcą drogi.</li>
<li>Stan techniczny, nośność i własność każdego słupka – do potwierdzenia przed montażem.</li>
<li><b>b) Nowe słupki</b> (w lasach i tam, gdzie nie ma słupka z nazwą ulicy): rura stalowa ocynkowana Ø 60 mm, ok. 3,5 m, z kotwą lub fundamentem, ok. 2,8 m nad ziemią; lokalizacja i sposób osadzenia do uzgodnienia z zarządcą terenu (w lasach – Nadleśnictwo Koszęcin).</li>
</ul></div>
<div class="foot"><span>Propozycja do uzgodnienia · wzór „HUB Strzebiń” (generator V22) · listopad 2026</span><span>rowerowy-strzebin.smart-ant.pl</span></div>
</div>
<script src="file://{os.path.abspath(S + '/lib/tabliczka-dane.js')}"></script>
<script src="file://{os.path.abspath(H + '/www/lib/tabliczka.js')}"></script>
<script>
const TAB = {json.dumps(TAB, ensure_ascii=False)}, TAB2 = {json.dumps(TAB2, ensure_ascii=False)}, ROUTES2 = {json.dumps(ROUTES2)}, NR2 = {NR2}, EX = {json.dumps(EX, ensure_ascii=False)}, KOL = {json.dumps(KOL)}, ROUTES = {json.dumps(ROUTES)}, NR = {NR};
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
  // 2. rysunki montażu – skala ok. 1:32, ziemia na dole; a) istniejący słupek z nazwami ulic, b) nowy słupek w lesie
  const svg = document.getElementById('rys'), NS = 'http://www.w3.org/2000/svg', S_ = 1 / 37, G = 88;
  const y = m => G - m * 1000 * S_;
  const el = (t, a, txt) => {{ const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (txt != null) e.textContent = txt; svg.appendChild(e); return e; }};
  el('rect', {{x: 0, y: G, width: 182, height: 8, fill: '#e8e1cf'}}); el('line', {{x1: 0, x2: 182, y1: G, y2: G, stroke: '#9a9078', 'stroke-width': .4}});
  const pw = 800 * S_, ph = 200 * S_;
  function slupek(X, tab, ulice, nr, routes, gora, etykieta) {{
    el('rect', {{x: X - 1, y: y(gora), width: 2, height: G - y(gora), fill: '#9aa3a8'}});
    let rz = 2.6;                                     // górna krawędź pierwszego rzędu drogowskazów
    if (ulice.length) {{
      // nazwy ulic jak w Strzebiniu: białe, niebieski napis i obwódka, strzałka na zewnątrz, herb przy rurze; na szczycie rury po obu stronach
      ulice.forEach((u, i) => {{ const top = y(gora - .02), w = 650 * S_, h = 160 * S_, x = i ? X + 1 : X - 1 - w, lewa = !i;
        el('rect', {{x, y: top, width: w, height: h, rx: .25, fill: '#fff', stroke: '#1f4fa0', 'stroke-width': .3}});
        el('path', {{d: lewa ? `M ${{x + .8}} ${{top + h / 2}} l 1.2 -.95 v 1.9 z` : `M ${{x + w - .8}} ${{top + h / 2}} l -1.2 -.95 v 1.9 z`, fill: '#1f4fa0'}});
        const hx = lewa ? x + w - 2.3 : x + .7;
        el('path', {{d: `M ${{hx}} ${{top + 1}} h 1.6 v 1.5 q 0 1.1 -.8 1.6 q -.8 -.5 -.8 -1.6 z`, fill: '#1f4fa0'}});
        const tx = el('text', {{x: x + w / 2 + (lewa ? -.6 : .6), y: top + 3.4, 'text-anchor': 'middle', fill: '#1f4fa0', 'font-size': 1.9, 'font-family': 'Arial', 'font-weight': 700}}, u);
        if (tx.getComputedTextLength() > w - 5.5) {{ tx.setAttribute('textLength', w - 5.5); tx.setAttribute('lengthAdjust', 'spacingAndGlyphs'); }}
        el('rect', {{x: X - 1.6, y: top + 2, width: 3.2, height: 1.1, rx: .25, fill: '#3b4448'}}); }});
      rz = gora - .02 - .16 - .05;
    }}
    const L_ = tab.filter(t => t.d === 'left'), R_ = tab.filter(t => t.d === 'right'), rows = Math.max(L_.length, R_.length);
    for (let r = 0; r < rows; r++) {{
      const top = y(rz - r * .23);
      for (const [t, side] of [[L_[r], 'l'], [R_[r], 'r']]) {{
        if (!t) continue;
        const x = side === 'l' ? X - 1 - pw : X + 1;
        const f = document.createElementNS(NS, 'foreignObject'); f.setAttribute('x', x); f.setAttribute('y', top); f.setAttribute('width', pw); f.setAttribute('height', ph + .2);
        f.innerHTML = '<div xmlns="http://www.w3.org/1999/xhtml" class="pl" style="width:' + pw + 'px">' + T.svg(t.d, 800, t.cat, t.e).svg + '</div>'; svg.appendChild(f);
        for (const dy of [.22, .66]) el('rect', {{x: X - 1.6, y: top + ph * dy, width: 3.2, height: 1.1, rx: .25, fill: '#3b4448'}});
      }}
    }}
    const dol = rz - (rows - 1) * .23 - .2;
    const yn = y(1.72); el('rect', {{x: X - 2, y: yn, width: 4, height: 2.7, fill: '#fff', stroke: '#c9c1ad', 'stroke-width': .2}});
    el('circle', {{cx: X, cy: yn + 1.35, r: 1.1, fill: '#00838F'}}); el('text', {{x: X, y: yn + 1.85, 'text-anchor': 'middle', fill: '#fff', 'font-size': 1.3, 'font-family': 'Arial', 'font-weight': 700}}, nr);
    routes.forEach((r, i) => {{ const k = KOL[r] || ['#555', 'white'], yb = yn + 2.9 + i * 1.1;
      el('rect', {{x: X - 1, y: yb, width: 2, height: 1, fill: k[0]}}); el('text', {{x: X, y: yb + .8, 'text-anchor': 'middle', fill: k[1], 'font-size': .85, 'font-family': 'Arial', 'font-weight': 700}}, r); }});
    el('text', {{x: X + 3, y: yn + 2, fill: '#4b5d53', 'font-size': 2.2, 'font-family': 'Arial'}}, '← węzeł ' + nr + ' i paski tras');
    el('text', {{x: X, y: G + 4.8, 'text-anchor': 'middle', fill: '#1d3b30', 'font-size': 2.8, 'font-family': 'Arial', 'font-weight': 700}}, etykieta);
    return dol;
  }}
  const d1 = slupek(46, TAB, ['ul. Wojska Polskiego', 'ul. Kościuszki'], NR, ROUTES, 3.0, 'a) istniejący słupek z nazwami ulic – nr ' + NR);
  const d2 = slupek(132, TAB2, [], NR2, ROUTES2, 2.8, 'b) nowy słupek w lesie – nr ' + NR2);
  // wymiary (orientacyjne, wg zdjęć) – z prawej
  const dim = (m, t) => {{ el('line', {{x1: 165, x2: 169, y1: y(m), y2: y(m), stroke: '#a0700f', 'stroke-width': .25}}); el('text', {{x: 170, y: y(m) + 1, fill: '#a0700f', 'font-size': 2.5, 'font-family': 'Arial'}}, t); }};
  dim(3.0, '3,0 m'); dim(2.6, '2,6 m'); dim(Math.min(d1, d2), (Math.round(Math.min(d1, d2) * 10) / 10).toFixed(1).replace('.', ',') + ' m'); dim(1.72, '1,7 m'); dim(0, '0');
  el('text', {{x: 89, y: G - 7, 'text-anchor': 'middle', fill: '#4b5d53', 'font-size': 2.3, 'font-family': 'Arial'}}, 'skala ok. 1:37 · tabliczki 800 × 200 mm');
  el('text', {{x: 89, y: G - 4, 'text-anchor': 'middle', fill: '#4b5d53', 'font-size': 2.3, 'font-family': 'Arial'}}, 'wysokości orientacyjne, do zmierzenia w terenie');
  el('text', {{x: 89, y: y(1.2), 'text-anchor': 'middle', fill: '#4b5d53', 'font-size': 2.3, 'font-family': 'Arial'}}, 'strzałka w lewo – po lewej stronie rury,');
  el('text', {{x: 89, y: y(1.2) + 3, 'text-anchor': 'middle', fill: '#4b5d53', 'font-size': 2.3, 'font-family': 'Arial'}}, 'w prawo – po prawej');
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
