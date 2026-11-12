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
pois = [dict(name=q["name"], lat=q["lat"], lon=q["lon"], cat=q["cat"], icon=q.get("icon", "")) for q in D.get("pois", []) if q.get("icon") != "wc"]
open(f"{S}/data.js", "w").write("window.HUB = " + json.dumps(dict(routes=routes, posts=posts, pois=pois), ensure_ascii=False, separators=(",", ":")) + ";")
PDFS = [("Solectwo_Strzebin_jako_HUB_rowerowy.pdf", "Projekt – komplet (opis, kosztorys, mapy, katalog)"),
        ("Solectwo_Strzebin_jako_HUB_rowerowy_opis_i_kosztorys.pdf", "Opis projektu i kosztorys"),
        ("drogowskazy_trasy.pdf", "Mapa tras rowerowych (A2)"), ("drogowskazy_mapa.pdf", "Mapa wszystkich słupków (A2)"),
        ("drogowskazy_mapa_strzebin.pdf", "Mapa Strzebinia – powiększenie (A2)"), ("drogowskazy_stan_drog.pdf", "Stan dróg na trasach (A2)"),
        ("A4_mapy_komplet.pdf", "Wszystkie mapy do druku na A4"), ("drogowskazy_katalog.pdf", "Katalog słupków i tabliczek")]
for fn, _ in PDFS: shutil.copy(f"{O}/{fn}", f"{S}/pdf/{fn}")
sz = lambda fn: f"{os.path.getsize(f'{S}/pdf/{fn}') / 1e6:.1f} MB".replace(".", ",")
dl = "\n".join(f'<li><a href="pdf/{fn}" download><span class="dl-t">{t}</span><span class="dl-s">PDF · {sz(fn)}</span></a></li>' for fn, t in PDFS)
n_posts = len(posts); n_pl = sum(len(p["imgs"]) for p in posts)
html = open("strona_template.html").read().replace("{{DOWNLOADS}}", dl).replace("{{NPOSTS}}", str(n_posts)).replace("{{NPLATES}}", str(n_pl)).replace(
    "{{NROUTES}}", str(sum(1 for r in routes if not r["alt"])))
open(f"{S}/index.html", "w").write(html)
z = zipfile.ZipFile(f"{O}/strona.zip", "w", zipfile.ZIP_DEFLATED)
for root, _, files in os.walk(S):
    for f in files: z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), S))
z.close()
print("ok strona", n_posts, n_pl, f"{os.path.getsize(f'{O}/strona.zip') / 1e6:.1f} MB")
