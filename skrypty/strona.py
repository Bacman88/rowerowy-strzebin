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
    posts.append(dict(nr=p["nr"], lat=round(p["lat"], 6), lon=round(p["lon"], 6), loc=p.get("loc", ""), pole=p["pole"], agree=p.get("agree", []), gmina=p.get("gmina", "Koszęcin"), os=p.get("os", 340),
                      routes=sorted(set(onr.get(p["nr"], [])), key=int), imgs=imgs, tab=tab))
pois = [dict(name=q["name"], lat=q["lat"], lon=q["lon"], cat=q["cat"], icon=q.get("icon", "")) for q in D.get("pois", []) if q.get("icon") not in ("wc", "service")]
# miejsca odpoczynku i serwisu: planowane stacje napraw + lista ręczna (dane/miejsca.geojson) + OSM (wiaty, piknik, widoki, ławki)
from shapely.geometry import MultiPoint, Point
hull = MultiPoint([(p["lon"], p["lat"]) for p in D["posts"]]).convex_hull.buffer(0.04)
# cała gmina Koszęcin z okolicą: granica gminy na mapach strony i miejsca z OSM w całej gminie
from shapely.geometry import shape as _shape
GMINA = json.load(open("../dane/gmina_koszecin.geojson"))["features"][0]["geometry"]
hull = hull.union(_shape(GMINA).buffer(0.04))
_gb = _shape(GMINA).exterior if GMINA["type"] == "Polygon" else max(_shape(GMINA).geoms, key=lambda x: x.area).exterior
gmina_ll = [[round(y, 5), round(x, 5)] for x, y in _gb.coords]
# stacja przy pomniku J. Ligonia: na mapie www ok. 30 m na wschód, żeby nie zasłaniała piktogramu pomnika
przes = lambda q: 0.0004 if any(o.get("icon") == "heritage" and abs(o["lat"] - q["lat"]) + abs(o["lon"] - q["lon"]) < 1e-4 for o in D.get("pois", [])) else 0
# k – stały klucz miejsca: panel administratora może je przesunąć, poprawić albo ukryć (tabela korekty_miejsc)
places = [dict(k=f"stacja:{q['lat']:.5f},{q['lon']:.5f}", typ="stacja", nazwa="Stacja napraw rowerów", opis="planowana – fundusz sołecki 2027", lat=q["lat"], lon=q["lon"] + przes(q), plan=1)
          for q in D.get("pois", []) if q.get("icon") == "service"]
# cele lokalne (wcześniej gwiazdki) jako miejsca z piktogramami – 12.11.2026 wg Bartosza: bar, restauracja, kościół, zabytek, sport
TYP_POI = {"church": ("kosciol", None), "heritage": ("zabytek", None), "community": ("zabytek", None), "bar": ("bar", None),
           "restaurant": ("jedzenie", None), "football": ("sport", "football"), "swim": ("sport", "swim")}
for q in D.get("pois", []):
    if q.get("icon") in TYP_POI:
        t_, ik_ = TYP_POI[q["icon"]]
        places.append(dict(k=f"poi:{q['name']}", typ=t_, nazwa=q["name"], opis="", lat=q["lat"], lon=q["lon"], **({"ik": ik_} if ik_ else {})))
for f in json.load(open("../dane/miejsca.geojson"))["features"]:
    x, y = f["geometry"]["coordinates"]; places.append(dict(f["properties"], k=f"stale:{f['properties'].get('typ', '')}:{f['properties'].get('nazwa', '')}"[:80], lat=y, lon=x))
for f in json.load(open("../dane/osm_gmina.geojson"))["features"]:
    q = f["properties"]; g = f["geometry"]
    if g["type"] != "Point": continue
    typ = ("wiata" if q.get("amenity") == "shelter" and q.get("shelter_type") in (None, "picnic_shelter", "weather_shelter", "lean_to", "basic_hut") else
           "piknik" if q.get("tourism") == "picnic_site" or q.get("leisure") in ("picnic_table", "firepit") else
           "widok" if q.get("tourism") == "viewpoint" else "lawka" if q.get("amenity") == "bench" else
           "wc" if q.get("amenity") == "toilets" else "woda" if q.get("amenity") == "drinking_water" else
           "zabawa" if q.get("leisure") == "playground" else "stojak" if q.get("amenity") == "bicycle_parking" else None)
    if typ and hull.contains(Point(g["coordinates"])):
        places.append(dict(k=f"osm:{q.get('@id', '')}", typ=typ, nazwa=q.get("name", ""), opis="", lat=g["coordinates"][1], lon=g["coordinates"][0], osm=1))
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
# ikonka strony: niebieski rower z generatora w białym kółku (SVG + PNG dla starszych przeglądarek i ekranu głównego telefonu)
def _fav(tlo_kolo=True, sw=17):
    sc = 46 / 324; tx, ty = 32 - (39 + 162) * sc, 32 - (69 + 106) * sc
    tlo = '<circle cx="32" cy="32" r="30.5" fill="#fff" stroke="#0759A7" stroke-width="2.2"/>' if tlo_kolo else '<rect width="64" height="64" fill="#fff"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{tlo}<g transform="translate({tx:.2f} {ty:.2f}) scale({sc:.4f})" fill="none" '
            f'stroke="#0759A7" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{TABD["BIKE"]}</g></svg>')
open(f"{S}/favicon.svg", "w").write(_fav())
open(f"{S}/_fav_apple.svg", "w").write(_fav(False))
import subprocess as _sp
_sp.run(["rsvg-convert", "-w", "32", "-h", "32", f"{S}/favicon.svg", "-o", f"{S}/favicon-32.png"], check=True)
_sp.run(["rsvg-convert", "-w", "180", "-h", "180", f"{S}/_fav_apple.svg", "-o", f"{S}/apple-touch-icon.png"], check=True)
os.remove(f"{S}/_fav_apple.svg")
open(f"{S}/lib/tabliczka-dane.js", "w").write("window.TABD = " + json.dumps(TABD, ensure_ascii=False, separators=(",", ":")) + ";")
os.makedirs(f"{S}/lib/fonts", exist_ok=True); shutil.copy("../fonts/FiraSansCondensed-SemiBold.ttf", f"{S}/lib/fonts/")
open(f"{S}/data.js", "w").write("window.HUB = " + json.dumps(dict(routes=routes, posts=posts, pois=pois, places=places, cele=cele, gmina=gmina_ll), ensure_ascii=False, separators=(",", ":")) + ";")
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
# 12.11.2026: sekcja „Dlaczego nie znaki R-4” – teksty wspólne z opisem PDF (teksty.py)
import html as _h, sys as _sy
_sy.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import teksty as TX
_e = _h.escape
R4 = (f'''<section id="r4" class="msec">
  <h2><span class="num">6</span>Dlaczego własne drogowskazy, a nie znaki R-4</h2>
  <p class="r4-eyebrow">{_e(TX.R4_TYTUL)}</p>
  {"".join(f'<p class="lead2">{_e(t)}</p>' for t in TX.R4_WSTEP)}
  <div class="card" style="margin-top:14px"><h3>Dlaczego nie stosujemy oznakowania R-4?</h3><p>{_e(TX.R4_DLACZEGO)}</p>
  <ol class="r4-list">{"".join(f"<li><b>{_e(h)}</b>{_e(t)}</li>" for h, t in TX.R4_ZALOZENIA)}</ol></div>
  <div class="r4-dol">
    <div class="card"><h3>Charakter projektowanego oznakowania</h3>{"".join(f"<p>{_e(t)}</p>" for t in TX.R4_CHARAKTER)}</div>
    <div class="r4-pod"><h3>Podsumowanie</h3><p>{_e(TX.R4_PODSUMOWANIE)}</p></div>
  </div>
  <h3 class="sub" id="kolka" style="font-size:19px;margin:34px 0 4px">Kółka z numerami tras na tabliczkach</h3>
  <p class="r4-eyebrow">{_e(TX.KOLKA_TYTUL)}</p>
  {"".join(f'<p class="lead2">{_e(t)}</p>' for t in TX.KOLKA_WSTEP)}
  <ol class="r4-list">{"".join(f"<li><b>{_e(h)}</b>{_e(t)}</li>" for h, t in TX.KOLKA_ZASADY)}</ol>
  <div class="r4-pod" style="margin-top:14px"><h3>W skrócie</h3><p>{_e(TX.KOLKA_PODSUMOWANIE)}</p></div>
</section>''')
html = html.replace("{{R4}}", R4).replace("{{FB}}", _e(TX.FB_URL))
open(f"{S}/index.html", "w").write(html)
z = zipfile.ZipFile(f"{O}/strona.zip", "w", zipfile.ZIP_DEFLATED)
for root, _, files in os.walk(S):
    for f in files: z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), S))
z.close()
print("ok strona", n_posts, n_pl, f"{os.path.getsize(f'{O}/strona.zip') / 1e6:.1f} MB")
