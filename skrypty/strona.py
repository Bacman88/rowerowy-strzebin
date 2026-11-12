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
    posts.append(dict(nr=p["nr"], lat=round(p["lat"], 6), lon=round(p["lon"], 6), loc=p.get("loc", ""), pole=p["pole"], agree=p.get("agree", []),
                      routes=sorted(set(onr.get(p["nr"], [])), key=int), imgs=imgs))
pois = [dict(name=q["name"], lat=q["lat"], lon=q["lon"], cat=q["cat"], icon=q.get("icon", "")) for q in D.get("pois", []) if q.get("icon") not in ("wc", "service")]
# miejsca odpoczynku i serwisu: planowane stacje napraw + lista ręczna (dane/miejsca.geojson) + OSM (wiaty, piknik, widoki, ławki)
from shapely.geometry import MultiPoint, Point
hull = MultiPoint([(p["lon"], p["lat"]) for p in D["posts"]]).convex_hull.buffer(0.04)
places = [dict(typ="stacja", nazwa="Stacja napraw rowerów", opis="planowana – fundusz sołecki 2027", lat=q["lat"], lon=q["lon"], plan=1)
          for q in D.get("pois", []) if q.get("icon") == "service"]
for f in json.load(open("../dane/miejsca.geojson"))["features"]:
    x, y = f["geometry"]["coordinates"]; places.append(dict(f["properties"], lat=y, lon=x))
for f in json.load(open("../dane/osm2_clean.geojson"))["features"]:
    q = f["properties"]; g = f["geometry"]
    if g["type"] != "Point": continue
    typ = ("wiata" if q.get("amenity") == "shelter" and q.get("shelter_type") in (None, "picnic_shelter", "weather_shelter", "lean_to", "basic_hut") else
           "piknik" if q.get("tourism") == "picnic_site" or q.get("leisure") in ("picnic_table", "firepit") else
           "widok" if q.get("tourism") == "viewpoint" else "lawka" if q.get("amenity") == "bench" else None)
    if typ and hull.contains(Point(g["coordinates"])):
        places.append(dict(typ=typ, nazwa=q.get("name", ""), opis="", lat=g["coordinates"][1], lon=g["coordinates"][0], osm=1))
open(f"{S}/data.js", "w").write("window.HUB = " + json.dumps(dict(routes=routes, posts=posts, pois=pois, places=places), ensure_ascii=False, separators=(",", ":")) + ";")
print("miejsca:", len(places))
M = lambda a2, base: [("A2", a2), ("A3", f"A3_{base}.pdf"), ("A4", f"A4_{base}.pdf")]
PDFS = [("Projekt – komplet (opis, kosztorys, mapy, katalog)", [("PDF", "Solectwo_Strzebin_jako_HUB_rowerowy.pdf")]),
        ("Opis projektu i kosztorys", [("PDF", "Solectwo_Strzebin_jako_HUB_rowerowy_opis_i_kosztorys.pdf")]),
        ("Mapa tras rowerowych", M("drogowskazy_trasy.pdf", "mapa_trasy")),
        ("Mapa wszystkich słupków", M("drogowskazy_mapa.pdf", "mapa_wszystkie_slupki")),
        ("Mapa Strzebinia – powiększenie", M("drogowskazy_mapa_strzebin.pdf", "mapa_strzebin")),
        ("Stan dróg na trasach", M("drogowskazy_stan_drog.pdf", "mapa_stan_drog")),
        ("Wszystkie mapy w jednym pliku", [("A3", "A3_mapy_komplet.pdf"), ("A4", "A4_mapy_komplet.pdf")]),
        ("Katalog słupków i tabliczek", [("PDF", "drogowskazy_katalog.pdf")])]
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
