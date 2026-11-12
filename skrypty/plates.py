"""Production SVGs for every plate, built 1:1 with Bartosz's generator V22 TRASY (HUB Strzebiń).

V22: numery tras w kółkach przy celu (maks. 4) – wg przebiegu tras pokazowych (drogowskazy_trasy.geojson).

Length policy agreed with Bartosz:
  * only the generator's lengths (800 / 950 / 1100 mm),
  * one post = one length (all plates on a post get the longest one needed there),
  * a single long name goes to two lines before the plate is made longer.
"""
import json, math, re, sys, os, csv, subprocess, shutil
from xml.sax.saxutils import escape
from fontTools.ttLib import TTFont

SIGNS, GEN_HTML, OUTDIR = sys.argv[1:4]
SINGLE = "--single" in sys.argv
PLATE = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--plate=")), "contour")   # V21: contour | rect | roundrect
def outline(d, W, stroke="#B8C1C7", fill="white", sw=2.5, dash=""):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    if PLATE in ("rect", "roundrect"):
        return f'<rect x="0" y="0" width="{W}" height="200" rx="{24 if PLATE == "roundrect" else 1}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>'
    return f'<path d="{path_left(W) if d == "left" else path_right(W)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>'
html = open(GEN_HTML, encoding="utf-8").read()
ICONS = json.loads(re.search(r"const ICONS=(\{.*?\});", html, re.S).group(1))
PALETTE = dict(re.findall(r"(\w+):'(#[0-9A-Fa-f]{6})'", re.search(r"const PALETTE=\{(.*?)\};", html).group(1)))
LENGTHS = {k: int(v) for k, v in re.findall(r"(\w):(\d+)", re.search(r"const LENGTHS=\{(.*?)\};", html).group(1))}
FAM = re.search(r"const fontFamily='([^']+)'", html).group(1)
BIKE_INNER = re.search(r"g\.innerHTML=`(<circle.*?)`;", html, re.S).group(1)
BB = dict(minX=39, minY=69, w=324, h=212)
# generator v16 defaults (sliders)
RT_D, RT_GAP, RT_AFTER = 31, 7, 10   # V22: średnica kółka trasy, odstęp, odstęp od nazwy/piktogramu [mm]
FONT, FONT_MIN, ICON, BIKE, TEXTGAP, BIKEBOXW, NAMESHIFT, DINSET, DSHIFT, MINGAP = 44, 32, 36, 100, 24, 128, 0, 28, 0, 18

font = TTFont("../fonts/FiraSansCondensed-SemiBold.ttf")
cmap, hmtx, upm = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
ASC, DESC = font["hhea"].ascent / upm, -font["hhea"].descent / upm
def width(t, size): return sum(hmtx[cmap[ord(c)]][0] if ord(c) in cmap else upm * 0.5 for c in t) / upm * size

def path_left(W): return f"M 94,8 H {W-35} Q {W-10},8 {W-10},33 V 167 Q {W-10},192 {W-35},192 H 94 Q 79,192 69,178 L 7,113 Q -3,100 7,87 L 69,22 Q 79,8 94,8 Z"
def path_right(W): return f"M 35,8 H {W-94} Q {W-79},8 {W-69},22 L {W-7},87 Q {W+3},100 {W-7},113 L {W-69},178 Q {W-79},192 {W-94},192 H 35 Q 10,192 10,167 V 33 Q 10,8 35,8 Z"
BG_INSET, MOUNT_ZONE, HOLE_INSET, HOLE_D = 7, 60, 30, 6        # V20 defaults, wariant 'overlay'
BASELINE_OFF = 15.327 / 44                                       # V20: centrowanie bryły tekstu (z przykładu generatora)
def f_(v): return f"{v:g}"
def color_shape_left(W, inset=BG_INSET):
    top, bottom, tip = 8 + inset, 192 - inset, 7 + inset + 7
    shoulder, flat, right = 69 + inset, 94 + inset, W - 10 - inset
    r, sT, sB = 25 - inset / 3, 22 + inset, 178 - inset
    return (f"M {f_(flat)} {f_(top)} H {f_(right-r)} Q {f_(right)} {f_(top)} {f_(right)} {f_(top+r)} V {f_(bottom-r)} Q {f_(right)} {f_(bottom)} {f_(right-r)} {f_(bottom)} "
            f"H {f_(flat)} Q {f_(flat-15)} {f_(bottom)} {f_(shoulder)} {f_(sB)} L {f_(tip)} 113 Q {f_(tip-10)} 100 {f_(tip)} 87 L {f_(shoulder)} {f_(sT)} Q {f_(flat-15)} {f_(top)} {f_(flat)} {f_(top)} Z")
def color_bg(d, W, color):
    cx = ((14 + BG_INSET) + (W - 10 - BG_INSET)) / 2
    tr = f' transform="translate({W} 0) scale(-1 1)"' if d == "right" else ""
    return (f'<g id="kolorowe_tlo" transform="translate({cx:.3f} 100.000) scale(1.000000 1.000000) translate({-cx:g} -100)">'
            f'<path id="ksztalt_kolorowego_tla" d="{color_shape_left(W)}" fill="{color}"{tr}/></g>')

def geometry(d, W):
    fx = 154 if d == "left" else 54; fw = W - 208
    inner_l, inner_r = fx + 12, fx + fw - 12
    bike_box = (inner_l, 19 + 8, BIKEBOXW, 162 - 16)
    name_x = inner_l + BIKEBOXW + TEXTGAP + NAMESHIFT
    km_r = inner_r - (DINSET - 12) - DSHIFT
    return fx, fw, bike_box, name_x, km_r

def layout(d, W, entries, size, two_line):
    """entries: [(name, km_text, icon)] -> (ok, drawing items). Mirrors render() checks of v16."""
    fx, fw, bike_box, name_x, km_r = geometry(d, W)
    items, ok = [], True
    multi = two_line and len(entries) == 1
    for i, (name, km, ico, rts) in enumerate(entries):
        if multi:
            w_ = name.split(" ")
            l1, l2 = min(((" ".join(w_[:k]), " ".join(w_[k:])) for k in range(1, len(w_))), key=lambda t: max(width(t[0], size), width(t[1], size)))
            lines, bases, ky = [l1, l2], [83, 148], 102 + BASELINE_OFF * size
        else:
            lines, bases = [name], [(102 if len(entries) == 1 else (67 if i == 0 else 133)) + BASELINE_OFF * size]
            ky = bases[0]
        tb = [(name_x, b - ASC * size, width(t, size), (ASC + DESC) * size) for t, b in zip(lines, bases)]
        icon = None
        if ico:
            t = tb[-1]; px = t[0] + t[2] + 10; py = t[1] + (t[3] - ICON) / 2; icon = (px, py)
        name_right = max(t[0] + t[2] for t in tb)
        if icon: name_right = max(name_right, icon[0] + ICON)
        dots = None
        if rts:   # V22: kółka tras za nazwą (za piktogramem, jeśli jest); w nazwie dwuwierszowej za linią 2 albo 1
            D_ = RT[0]; t = tb[0] if (RT[1] == "first" and len(tb) > 1) else tb[-1]
            px = (icon[0] + ICON if (icon and t is tb[-1]) else t[0] + t[2]) + RT_AFTER
            dots = (px, t[1] + (t[3] - D_) / 2, D_); name_right = max(name_right, px + len(rts) * D_ + (len(rts) - 1) * RT_GAP)
        dist_left = km_r - width(km, size)
        # V20: strefa montażowa (wariant overlay, nasada po stronie przeciwnej do grotu)
        if (d == "left" and km_r > W - MOUNT_ZONE) or (d == "right" and name_x < MOUNT_ZONE): ok = False
        if name_right + GAP[0] > dist_left + 0.5: ok = False
        for t in tb:
            if t[1] < 19 + 7 - 3 or t[1] + t[3] > 19 + 162 - 7 + 3: ok = False
        items.append(dict(lines=list(zip(lines, bases)), km=km, ky=ky, ico=ico, icon=icon, rts=rts, dots=dots))
    return ok, items

GAP = [18]
RT = [RT_D, "last"]
def best_layout(d, W, entries):
    """V22: przy kółkach tras najpierw pełna średnica 31 mm, potem kółka za 1. linią nazwy, potem mniejsze (26, 22 mm) – zanim tabliczka się wydłuży."""
    opts = [(RT_D, "last"), (RT_D, "first"), (26, "last"), (26, "first"), (22, "last"), (22, "first")] if any(e[3] for e in entries) else [(RT_D, "last")]
    for o in opts:
        RT[:] = o; r = _best_layout(d, W, entries)
        if r: r["rt"] = o; RT[:] = [RT_D, "last"]; return r
    RT[:] = [RT_D, "last"]; return None
def _best_layout(d, W, entries):
    """Prefer one line, then two lines (single target), at standard font."""
    for gap in (MINGAP, 14, 12):   # generator pozwala zejść z odstępem do 12 mm (suwak „minimalny odstęp”)
        GAP[0] = gap
        for two in ([False, True] if len(entries) == 1 and " " in entries[0][0] else [False]):
            ok, it = layout(d, W, entries, FONT, two)
            if ok: GAP[0] = MINGAP; return dict(ok=True, items=it, size=FONT, two=two)
    GAP[0] = MINGAP
    for size in (42, 40, 39, 38):   # jak generator: mniejsza czcionka, zanim tabliczka się wydłuży (np. „WC / Stacja napraw”)
        ok, it = layout(d, W, entries, size, False)
        if ok: return dict(ok=True, items=it, size=size, two=False)
    return None

def svg_plate(d, W, color, lay):
    fx, fw, bb, name_x, km_r = geometry(d, W)
    arrow = ("M 54 100 L 112 50 L 112 83 L 146 83 L 146 117 L 112 117 L 112 150 Z" if d == "left" else
             f"M {W-52} 100 L {W-107} 50 L {W-107} 83 L {W-146} 83 L {W-146} 117 L {W-107} 117 L {W-107} 150 Z")
    size = lay["size"]; parts = []
    for i, it in enumerate(lay["items"], 1):
        for j, (t, b) in enumerate(it["lines"]):
            parts.append(f'<text id="miejscowosc_{i}{"_linia2" if j else ""}" x="{name_x}" y="{b:.3f}" font-size="{size}" font-family="{FAM}" font-weight="600" fill="{color}">{escape(t)}</text>')
        parts.append(f'<text id="odleglosc_{i}" x="{km_r}" y="{it["ky"]:.3f}" text-anchor="end" font-size="{size}" font-family="{FAM}" font-weight="600" fill="{color}">{escape(it["km"])}</text>')
        if it["ico"]:
            px, py = it["icon"]
            parts.append(f'<g id="piktogram_{i}" data-icon="{it["ico"]}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
                         f'stroke-linejoin="round" transform="translate({px:.3f} {py:.3f}) scale({ICON / 24:.5f})">{ICONS[it["ico"]]}</g>')
        if it["rts"]:   # V22 addRouteBadges: kółko z białą obwódką 1,4 mm i numerem
            px, py, D_ = it["dots"]; g_ = []
            for j, r_ in enumerate(it["rts"]):
                cx, cy = px + D_ / 2 + j * (D_ + RT_GAP), py + D_ / 2; col, txt = KOL.get(r_, ("#555", "white"))[:2]
                fs = D_ * (.66 if len(r_) == 1 else .49)
                g_.append(f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{D_/2:g}" fill="{col}" stroke="white" stroke-width="1.4"/>'
                          f'<text x="{cx:.3f}" y="{cy + fs * .36:.3f}" text-anchor="middle" fill="{txt}" font-family="Arial, sans-serif" font-size="{fs:.2f}" font-weight="700">{r_}</text>')
            parts.append(f'<g id="trasy_{i}" data-type="route-badges">{"".join(g_)}</g>')
    s = BIKE / BB["w"]; dw, dh = BB["w"] * s, BB["h"] * s
    tx = bb[0] + (bb[2] - dw) / 2 - BB["minX"] * s; ty = bb[1] + (bb[3] - dh) / 2 - BB["minY"] * s
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="200mm" viewBox="0 0 {W} 200">'
            f'{outline(d, W)}'
            f'{color_bg(d, W, color)}'
            f'<rect x="{fx}" y="19" width="{fw}" height="162" rx="15" fill="white" stroke="{color}" stroke-width="5"/>'
            f'<path d="{arrow}" fill="white"/>'
            f'<g id="teksty_edytowalne">{"".join(parts)}</g>'
            f'<g id="symbol_roweru" transform="translate({tx:.2f} {ty:.2f}) scale({s:.4f})" fill="none" stroke="{color}" stroke-width="10.5" '
            f'stroke-linecap="round" stroke-linejoin="round">{BIKE_INNER}</g></svg>')

def svg_tech(d, W):
    hx = W - HOLE_INSET if d == "left" else HOLE_INSET; zx = W - MOUNT_ZONE if d == "left" else 0
    holes = "".join(f'<circle cx="{hx}" cy="{y}" r="{HOLE_D/2:g}" fill="white" stroke="#c44949" stroke-width="1.4"/>'
                    f'<path d="M {hx-12} {y} H {hx+12} M {hx} {y-12} V {y+12}" fill="none" stroke="#c44949" stroke-width="0.9" stroke-dasharray="3 2"/>' for y in (50, 150))
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="200mm" viewBox="0 0 {W} 200">'
            f'{outline(d, W, "#273746", "white", 1)}'
            f'<rect x="0" y="0" width="{W}" height="200" fill="#e2edf5" fill-opacity=".25" stroke="#5d7183" stroke-width="1" stroke-dasharray="8 4"/>'
            f'<g id="warstwa_techniczna_niedrukowana" data-layer="technical" pointer-events="none">'
            f'{outline(d, W, "#0099aa", "none", 1.5, "7 4")}'
            f'<rect x="{zx}" y="0" width="{MOUNT_ZONE}" height="200" fill="#7a56c0" fill-opacity=".15" stroke="#7a56c0" stroke-width="1.5" stroke-dasharray="5 4"/>{holes}</g>'
            f'<metadata>Warstwa techniczna: nie drukować na znaku. Średnica i odległości otworów wymagają zatwierdzenia przez producenta mocowania.</metadata></svg>')

def category(pl):
    if pl.get("lr"): return "green", "route"
    if pl.get("cat"): return pl["cat"], pl.get("icon")
    return "blue", None
def side(pl):
    d_ = pl.get("deg"); return "right" if (d_ is not None and (math.sin(math.radians(d_)) > 0.34 or (abs(math.sin(math.radians(d_))) <= 0.34 and math.cos(math.radians(d_)) > 0))) else "left"   # wsch. →, zach. ←; płn. →, płd. ← (żeby przeciwne kierunki nie miały tej samej strzałki)
def close(a, b, tol=35): return a is not None and b is not None and abs((a - b + 180) % 360 - 180) <= tol
def cluster_dirs(plates_):
    cl = []
    for pl in plates_:
        if not pl.get("lr") and pl.get("km") is not None:
            for c in cl:
                h = c[0]
                if not h.get("lr") and category(h)[0] == category(pl)[0] and side(h) == side(pl) and close(h.get("deg"), pl.get("deg")):
                    c.append(pl); break
            else: cl.append([pl])
        else: cl.append([pl])
    out = []
    for c in cl:
        s_ = sorted(c, key=lambda q: q["km"] or 0); out += [s_[i:i + 2] for i in range(0, len(s_), 2)]
    return out
def groups(p): return [[pl] for pl in p["plates"]] if SINGLE else cluster_dirs(p["plates"])
DIR8 = ["płn.", "płn.-wsch.", "wsch.", "płd.-wsch.", "płd.", "płd.-zach.", "zach.", "płn.-zach."]
CATNAME = {"blue": "niebieska – miejscowości", "green": "zielona – przyroda i szlaki", "brown": "brązowa – zabytki i kultura",
           "red": "ciemnoczerwona – gastronomia", "gray": "grafitowa – infrastruktura", "orange": "pomarańczowa – sport"}
ORDER = sorted(LENGTHS, key=LENGTHS.get)            # S, M, L

D = json.load(open(SIGNS))
# V22: które trasy pokazowe prowadzą w kierunku tabliczki – trasa idzie razem ze ścieżką do celu od słupka
# przez co najmniej min(1 km, 60% drogi do celu); cele bliżej niż 1 km bez kółek. Wariant 1a liczy się jako trasa 1.
exec(open("trasy_kolory.py").read()); KOL = KOLORY
_TR = os.path.join(os.path.dirname(OUTDIR.rstrip("/")), "drogowskazy_trasy.geojson")
from pyproj import Geod
_geod = Geod(ellps="WGS84")
_RE = {}
if os.path.exists(_TR):
    for f in json.load(open(_TR))["features"]:
        rid = f["properties"]["id"].rstrip("a"); c = [tuple(round(v, 7) for v in q) for q in f["geometry"]["coordinates"]]
        for a_, b_ in zip(c, c[1:]): _RE.setdefault(frozenset((a_, b_)), set()).add(rid)
else: print("UWAGA: brak", _TR, "– tabliczki bez numerów tras (uruchom najpierw trasy.py)")
def plate_routes(pl):
    path = [tuple(round(v, 7) for v in q) for q in (pl.get("path") or [])]
    if len(path) < 2 or not _RE or (pl.get("km") or 0) < 1.0: return []   # bliskie cele (< 1 km) bez kółek – to nie „kierunek trasy”
    seg = [(_RE.get(frozenset((a_, b_)), set()), _geod.inv(a_[0], a_[1], b_[0], b_[1])[2]) for a_, b_ in zip(path, path[1:])]
    total = sum(m for _, m in seg); need = min(1000, 0.6 * total); out = []
    for r_ in sorted(set().union(*[s_ for s_, _ in seg]), key=lambda x: int(x)):
        run = 0
        for s_, m in seg:
            if r_ not in s_: break
            run += m
        if run >= need - 1: out.append(r_)
    return out[:4]

svgdir = os.path.join(OUTDIR, "svg"); pngdir = os.path.join(OUTDIR, "png"); techdir = os.path.join(OUTDIR, "svg_montaz")
shutil.rmtree(OUTDIR, ignore_errors=True); os.makedirs(svgdir); os.makedirs(pngdir); os.makedirs(techdir)
rows, manifest, stats = [], {}, {k: 0 for k in ORDER}
for p in D["posts"]:
    plates = []
    gl = []
    for grp in groups(p):
        # a 2-target plate that would force a longer plate is split into two standard ones
        if len(grp) == 2:
            d0 = side(grp[0])
            ent = lambda g_: [(q["name"], (f"{q['km']:.1f}".replace(".", ",") + " km") if q.get("km") is not None else "0,0 km", category(q)[1], plate_routes(q)) for q in g_]
            if not best_layout(d0, LENGTHS[ORDER[0]], ent(grp)) and all(best_layout(d0, LENGTHS[ORDER[0]], ent([q])) for q in grp):
                gl += [[grp[0]], [grp[1]]]; continue
        gl.append(grp)
    for grp in gl:
        d = side(grp[0]); cat = category(grp[0])[0]
        entries = [(pl["name"], (f"{pl['km']:.1f}".replace(".", ",") + " km") if pl.get("km") is not None else "0,0 km", category(pl)[1], plate_routes(pl)) for pl in grp]
        need = next((k for k in ORDER if best_layout(d, LENGTHS[k], entries)), None)
        plates.append(dict(grp=grp, d=d, cat=cat, entries=entries, need=need))
    # one post = one length
    pole = max((pl["need"] or ORDER[-1] for pl in plates), key=lambda k: LENGTHS[k]) if plates else ORDER[0]
    W = LENGTHS[pole]; manifest[p["nr"]] = []
    for k, pl in enumerate(plates, 1):
        lay = best_layout(pl["d"], W, pl["entries"]); note = ""
        if lay is None:                                  # last resort: smaller font on the longest plate
            for sz in range(FONT - 1, FONT_MIN - 1, -1):
                for two in [False, True]:
                    ok, it = layout(pl["d"], W, pl["entries"], sz, two)
                    if ok: lay = dict(ok=True, items=it, size=sz, two=two); break
                if lay: break
            note = f"czcionka zmniejszona do {lay['size']} mm" if lay else "nie mieści się – do ręcznej korekty"
            if not lay: _, it = layout(pl["d"], W, pl["entries"], FONT_MIN, False); lay = dict(items=it, size=FONT_MIN, two=False)
        if lay.get("two"): note = (note + "; " if note else "") + "nazwa w dwóch liniach"
        if lay.get("rt") and lay["rt"] != (RT_D, "last"): note = (note + "; " if note else "") + f"kółka tras {lay['rt'][0]} mm" + (" za 1. linią" if lay["rt"][1] == "first" else "")
        color = PALETTE[pl["cat"]]
        fn = f"S{p['nr']:02d}_T{k}_{'lewo' if pl['d'] == 'left' else 'prawo'}_{W}"
        open(os.path.join(svgdir, fn + ".svg"), "w", encoding="utf-8").write(svg_plate(pl["d"], W, color, lay))
        tn = f"montaz_{PLATE}_{'lewo' if pl['d'] == 'left' else 'prawo'}_{W}x200.svg"
        if not os.path.exists(os.path.join(techdir, tn)): open(os.path.join(techdir, tn), "w", encoding="utf-8").write(svg_tech(pl["d"], W))
        subprocess.run(["rsvg-convert", "-w", str(int(1200 * W / 800)), "-o", os.path.join(pngdir, fn + ".png"), os.path.join(svgdir, fn + ".svg")], check=True)
        deg = pl["grp"][0].get("deg"); stats[pole] += 1
        manifest[p["nr"]].append(dict(png=os.path.join(pngdir, fn + ".png"), deg=deg, dir=pl["d"], note=note, size=lay["size"], cat=pl["cat"], W=W,
                                      routes=[e[3] for e in pl["entries"]], ent=[list(e) for e in pl["entries"]]))
        flat = [x for e in pl["entries"] for x in e[:2]]
        trs = " / ".join(",".join(e[3]) for e in pl["entries"])
        why = "; ".join(sorted({g.get("why", "") for g in pl["grp"] if g.get("why") and g.get("why") != "jest w uMap"}))
        rows.append([p["nr"], k, fn + ".svg", f"{W} × 200", "←" if pl["d"] == "left" else "→", DIR8[int((deg + 22.5) // 45) % 8] if deg is not None else "",
                     CATNAME.get(pl["cat"], pl["cat"]), *flat, *([""] * (4 - len(flat))), lay["size"], ", ".join(p["agree"]), p["loc"],
                     f"{p['lat']:.6f}", f"{p['lon']:.6f}", p.get("pole", "do sprawdzenia"), trs if trs.strip(" /") else ""])
with open(os.path.join(OUTDIR, "wykaz_tabliczek.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["Słupek", "Tabliczka", "Plik SVG", "Wymiar [mm]", "Zwrot", "Kierunek kompasowy", "Typ tabliczki", "Cel 1", "Odległość 1", "Cel 2",
                "Odległość 2", "Czcionka [mm]", "Uzgodnienie", "Lokalizacja", "Szer.", "Dł.", "Słupek (istniejący/nowy)", "Kółka tras (cel 1 / cel 2)"])
    w.writerows(rows)
json.dump(manifest, open(os.path.join(OUTDIR, "manifest.json"), "w"), ensure_ascii=False)
print("plates", len(rows), "by length", {LENGTHS[k]: v for k, v in stats.items()}, "z kółkami tras", sum(1 for r in rows if r[-1]),
      "kółek", sum(len(x) for r in rows for x in r[-1].replace(" / ", ",").split(",") if x))
for r in rows:
    pass
