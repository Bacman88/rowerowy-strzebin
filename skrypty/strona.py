"""Statyczna strona projektu (Leaflet) -> out/strona/ + strona.zip"""
import json, os, shutil, zipfile
from PIL import Image
exec(open("trasy_kolory.py").read())
O = "../out"; S = f"{O}/strona"
shutil.rmtree(S, ignore_errors=True); os.makedirs(f"{S}/tabliczki"); os.makedirs(f"{S}/gpx"); os.makedirs(f"{S}/pdf")
shutil.copytree("../vendor/leaflet", f"{S}/lib")
D = json.load(open("signs_prop.json")); MF = json.load(open(f"{O}/tabliczki/manifest.json"))
TRG = json.load(open(f"{O}/drogowskazy_trasy.geojson"))
NAZWY = {"Trójca": "kościół św. Trójcy", "Kalety Unia": "Kalety (stadion Unii)"}
routes = []
for f in TRG["features"]:
    p = f["properties"]; rid = p["id"]
    col, txt, cname = KOLORY[rid.rstrip("a")]
    seq = [str(k) if isinstance(k, int) else NAZWY.get(k, k) for k in p["seq"]]
    pa, gr = round(p["pav"] / p["km"] * 100), round(p.get("grv", 0) / p["km"] * 100)
    routes.append(dict(id=rid, name=p["name"], sub=p.get("sub", ""), col=col, txt=txt, km=round(p["km"], 1), pav=pa, grv=gr, grunt=100 - pa - gr,
                       dw=round(p["dw"] * 1000), seq=seq, alt=bool(p.get("alt")), coords=[[round(c[1], 6), round(c[0], 6)] for c in f["geometry"]["coordinates"]]))
    if not p.get("alt"):
        pts = "\n".join(f'<trkpt lat="{c[1]:.6f}" lon="{c[0]:.6f}"/>' for c in f["geometry"]["coordinates"])
        open(f"{S}/gpx/trasa_{rid}.gpx", "w").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="HUB rowerowy Strzebin" xmlns="http://www.topografix.com/GPX/1/1">'
                                                     f'<trk><name>Trasa {rid}: {p["name"]}</name><trkseg>\n{pts}\n</trkseg></trk></gpx>')
onr = {}
for r in routes:
    if r["alt"]: continue
    for k in r["seq"]:
        if k.isdigit(): onr.setdefault(int(k), []).append(r["id"])
posts = []
for p in D["posts"]:
    imgs = []
    for e in MF.get(str(p["nr"]), []):
        fn = os.path.basename(e["png"]).replace(".png", ".webp")
        Image.open(e["png"]).convert("RGBA").resize((600, 150), Image.LANCZOS).save(f"{S}/tabliczki/{fn}", "WEBP", quality=88)
        imgs.append(fn)
    tab = [dict(d=e["dir"], cat=e["cat"], W=e["W"], e=e.get("ent", [])) for e in MF.get(str(p["nr"]), [])]   # treść tabliczek (edytor węzłów)
    posts.append(dict(nr=p["nr"], lat=round(p["lat"], 6), lon=round(p["lon"], 6), loc=p.get("loc", ""), pole=p["pole"], agree=p.get("agree", []),
                      routes=sorted(set(onr.get(p["nr"], [])), key=int), imgs=imgs, tab=tab))
pois = [dict(name=q["name"], lat=q["lat"], lon=q["lon"], cat=q["cat"], icon=q.get("icon", "")) for q in D.get("pois", []) if q.get("icon") not in ("wc", "service")]
# miejsca odpoczynku i serwisu: planowane stacje napraw + lista ręczna (dane/miejsca.geojson) + OSM (wiaty, piknik, widoki, ławki)
from shapely.geometry import MultiPoint, Point
hull = MultiPoint([(p["lon"], p["lat"]) for p in D["posts"]]).convex_hull.buffer(0.04)
# stacja przy pomniku J. Ligonia: na mapie www ok. 30 m na wschód, żeby nie zasłaniała gwiazdki pomnika
przes = lambda q: 0.0004 if any(o.get("icon") == "heritage" and abs(o["lat"] - q["lat"]) + abs(o["lon"] - q["lon"]) < 1e-4 for o in D.get("pois", [])) else 0
places = [dict(typ="stacja", nazwa="Stacja napraw rowerów", opis="planowana – fundusz sołecki 2027", lat=q["lat"], lon=q["lon"] + przes(q), plan=1)
          for q in D.get("pois", []) if q.get("icon") == "service"]
for f in json.load(open("../dane/miejsca.geojson"))["features"]:
    x, y = f["geometry"]["coordinates"]; places.append(dict(f["properties"], lat=y, lon=x))
for f in json.load(open("../dane/osm2_clean.geojson"))["features"]:
    q = f["properties"]; g = f["geometry"]
    if g["type"] != "Point": continue
    typ = ("wiata" if q.get("amenity") == "shelter" and q.get("shelter_type") in (None, "picnic_shelter", "weather_shelter", "lean_to", "basic_hut") else
           "piknik" if q.get("tourism") == "picnic_site" or q.get("leisure") in ("picnic_table", "firepit") else
           "widok" if q.get("tourism") == "viewpoint" else "lawka" if q.get("amenity") == "bench" else
           "wc" if q.get("amenity") == "toilets" else "woda" if q.get("amenity") == "drinking_water" else
           "zabawa" if q.get("leisure") == "playground" else "stojak" if q.get("amenity") == "bicycle_parking" else None)
    if typ and hull.contains(Point(g["coordinates"])):
        places.append(dict(typ=typ, nazwa=q.get("name", ""), opis="", lat=g["coordinates"][1], lon=g["coordinates"][0], osm=1))
# wspólne odcinki tras: każda trasa dzielona na kawałki o stałym zestawie tras; na stronie rysowane obok siebie (przesunięcie)
import re as _re, collections as _col
_ord = lambda i: (int(_re.match(r"\d+", i).group()), i)
_E = _col.defaultdict(set)
_rc = {r["id"]: [tuple(round(v, 6) for v in c) for c in r["coords"]] for r in routes}
for i, c in _rc.items():
    for a_, b_ in zip(c, c[1:]): _E[frozenset((a_, b_))].add(i)
for r in routes:
    c = _rc[r["id"]]; parts = []; cur = None
    for a_, b_ in zip(c, c[1:]):
        k = tuple(sorted(_E[frozenset((a_, b_))], key=_ord))
        if cur and cur[0] == k: cur[1].append(b_)
        else:
            cur = (k, [a_, b_]); parts.append(cur)
    out = []
    for k, cs in parts:
        if cs[0] > cs[-1]: cs = cs[::-1]   # ten sam kierunek dla wszystkich tras na wspólnym kawałku
        out.append(dict(c=[list(x) for x in cs], k=k.index(r["id"]), n=len(k)))
    r["a"], r["b"] = list(c[0]), list(c[-1])   # początek i koniec (do linku Mapy.com)
    r["parts"] = out; del r["coords"]
# piktogramy dla stron (te same co na tabliczkach) + kilka dodatkowych z Tabler Icons
import glob as _gl
IK = {os.path.basename(f)[:-4]: _re.sub(r"</?svg[^>]*>", "", open(f).read()).strip() for f in _gl.glob("../generator/piktogramy_tabler/*.svg")}
IK.update(pavilion='<path d="M3 21h7v-3a2 2 0 0 1 4 0v3h7"/><path d="M6 21l0 -9"/><path d="M18 21l0 -9"/><path d="M6 12h12a3 3 0 0 0 3 -3a9 8 0 0 1 -9 -6a9 8 0 0 1 -9 6a3 3 0 0 0 3 3"/>',
          campfire='<path d="M4 21l16 -4"/><path d="M20 21l-16 -4"/><path d="M12 15a4 4 0 0 0 4 -4c0 -3 -2 -3 -2 -8c-4 2 -6 5 -6 8a4 4 0 0 0 4 4z"/>',
          star='<path d="M12 17.75l-6.172 3.245l1.179 -6.873l-5 -4.867l6.9 -1l3.086 -6.253l3.086 6.253l6.9 1l-5 4.867l1.179 6.873z"/>',
          droplet='<path d="M7.502 19.423c2.602 2.105 6.395 2.105 8.996 0c2.602 -2.105 3.262 -5.708 1.566 -8.546l-4.89 -7.26c-.42 -.625 -1.287 -.803 -1.936 -.397a1.376 1.376 0 0 0 -.41 .397l-4.893 7.26c-1.695 2.838 -1.035 6.441 1.567 8.546z"/>',
          bike='<path d="M5 18m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"/><path d="M19 18m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"/><path d="M12 19l0 -4l-3 -3l5 -4l2 3l3 0"/><path d="M17 5m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/>')
os.makedirs(f"{S}/lib", exist_ok=True)
open(f"{S}/lib/ikony.js", "w").write("window.IKONY = " + json.dumps(IK, ensure_ascii=False) + ";")
# cele do edytora tabliczek: miejscowości z tabliczek + ciekawe miejsca (z kategorią i piktogramem jak na tabliczkach)
_vill = sorted({pl["name"] for p in D["posts"] for pl in p["plates"] if not pl.get("lr") and not pl.get("poi") and pl["name"] in D["places"]})
cele = [dict(n=v, lat=round(D["places"][v][1], 6), lon=round(D["places"][v][0], 6), cat="blue") for v in _vill]
cele += [dict(n=q["name"], lat=round(q["lat"], 6), lon=round(q["lon"], 6), cat=q["cat"], ico=q.get("icon", "")) for q in D.get("pois", [])
         if not any(c["n"] == q["name"] for c in cele)]
# dane generatora V22 dla podglądu tabliczek w przeglądarce (lib/tabliczka.js): kolory, piktogramy, rower, szerokości liter
_h = open("../generator/generator_drogowskazow.html", encoding="utf-8").read()
from fontTools.ttLib import TTFont as _TT
_f = _TT("../fonts/FiraSansCondensed-SemiBold.ttf"); _cm, _hm, _upm = _f.getBestCmap(), _f["hmtx"], _f["head"].unitsPerEm
TABD = dict(PALETTE=dict(_re.findall(r"(\w+):'(#[0-9A-Fa-f]{6})'", _re.search(r"const PALETTE=\{(.*?)\};", _h).group(1))),
            LENGTHS={k: int(v) for k, v in _re.findall(r"(\w):(\d+)", _re.search(r"const LENGTHS=\{(.*?)\};", _h).group(1))},
            ICONS=json.loads(_re.search(r"const ICONS=(\{.*?\});", _h, _re.S).group(1)),
            BIKE=_re.search(r"g\.innerHTML=`(<circle.*?)`;", _h, _re.S).group(1),
            ADV={chr(c): round(_hm[g][0] / _upm, 4) for c, g in _cm.items() if c < 0x2000},
            ASC=_f["hhea"].ascent / _upm, DESC=-_f["hhea"].descent / _upm,
            KOL={k: v[:2] for k, v in KOLORY.items()})
open(f"{S}/lib/tabliczka-dane.js", "w").write("window.TABD = " + json.dumps(TABD, ensure_ascii=False, separators=(",", ":")) + ";")
os.makedirs(f"{S}/lib/fonts", exist_ok=True); shutil.copy("../fonts/FiraSansCondensed-SemiBold.ttf", f"{S}/lib/fonts/")
open(f"{S}/data.js", "w").write("window.HUB = " + json.dumps(dict(routes=routes, posts=posts, pois=pois, places=places, cele=cele), ensure_ascii=False, separators=(",", ":")) + ";")
print("miejsca:", len(places))
M = lambda a2, base: [("A2", a2), ("A3", f"A3_{base}.pdf"), ("A4", f"A4_{base}.pdf")]
PDFS = [("Projekt – komplet (opis, kosztorys, mapy, katalog)", [("PDF", "Solectwo_Strzebin_jako_HUB_rowerowy.pdf")]),
        ("Opis projektu i kosztorys", [("PDF", "Solectwo_Strzebin_jako_HUB_rowerowy_opis_i_kosztorys.pdf")]),
        ("Mapa tras rowerowych", M("drogowskazy_trasy.pdf", "mapa_trasy")),
        ("Mapa wszystkich słupków", M("drogowskazy_mapa.pdf", "mapa_wszystkie_slupki")),
        ("Mapa Strzebinia – powiększenie", M("drogowskazy_mapa_strzebin.pdf", "mapa_strzebin")),
        ("Stan dróg na trasach", M("drogowskazy_stan_drog.pdf", "mapa_stan_drog")),
        ("Wszystkie mapy w jednym pliku", [("A3", "A3_mapy_komplet.pdf"), ("A4", "A4_mapy_komplet.pdf")]),
        ("Katalog słupków i tabliczek", [("PDF", "drogowskazy_katalog.pdf")]),
        ("Kółka tras – naklejki do doklejania (A4)", [("PDF", "kropki_tras_A4.pdf")])]
for _, fs in PDFS:
    for _, fn in fs: shutil.copy(f"{O}/{fn}", f"{S}/pdf/{fn}")
sz = lambda fn: f"{os.path.getsize(f'{S}/pdf/{fn}') / 1e6:.1f} MB".replace(".", ",")
def dl_item(t, fs):
    if len(fs) == 1:
        fn = fs[0][1]
        return f'<li><a href="pdf/{fn}" download><span class="dl-t">{t}</span><span class="dl-s">PDF · {sz(fn)}</span></a></li>'
    ch = "".join(f'<a href="pdf/{fn}" download title="{sz(fn)}"><b>{lab}</b><span>{sz(fn)}</span></a>' for lab, fn in fs)
    return f'<li class="dl-m"><span class="dl-t">{t}</span><span class="dl-f">{ch}</span></li>'
dl = "\n".join(dl_item(t, fs) for t, fs in PDFS)
# generator tabliczek: wersja do otwarcia online + paczka ZIP
shutil.copy("../generator/generator_drogowskazow.html", f"{S}/generator.html")
os.makedirs(f"{S}/pobierz", exist_ok=True); zp = f"{S}/pobierz/generator_tabliczek_HUB_Strzebin.zip"
if os.path.exists(zp): os.remove(zp)
os.system(f'cd .. && zip -qr "skrypty/{zp}" generator')
zsz = f"{os.path.getsize(zp) / 1e6:.1f} MB".replace(".", ",")
dl += (f'\n<li class="dl-m"><span class="dl-t">Generator tabliczek (wzór „HUB Strzebiń”)</span><span class="dl-f">'
       f'<a href="generator.html" target="_blank" rel="noopener"><b>Otwórz</b><span>online</span></a>'
       f'<a href="pobierz/generator_tabliczek_HUB_Strzebin.zip" download><b>ZIP</b><span>{zsz}</span></a></span></li>')
# mapa stanu dróg ze zgłoszeniami (PHP + baza poza public_html); odcinki dorabia odcinki.py
shutil.copytree("www", S, dirs_exist_ok=True)
n_posts = len(posts); n_pl = sum(len(p["imgs"]) for p in posts)
html = open("strona_template.html").read().replace("{{DOWNLOADS}}", dl).replace("{{NPOSTS}}", str(n_posts)).replace("{{NPLATES}}", str(n_pl)).replace(
    "{{NROUTES}}", str(sum(1 for r in routes if not r["alt"])))
open(f"{S}/index.html", "w").write(html)
z = zipfile.ZipFile(f"{O}/strona.zip", "w", zipfile.ZIP_DEFLATED)
for root, _, files in os.walk(S):
    for f in files: z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), S))
z.close()
print("ok strona", n_posts, n_pl, f"{os.path.getsize(f'{O}/strona.zip') / 1e6:.1f} MB")
