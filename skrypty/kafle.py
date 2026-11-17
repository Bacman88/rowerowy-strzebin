"""Kafle odcinków dla strony (17.11.2026, etap 1).

Z pełnego stan/odcinki.js (który dalej zostaje dla Jedź, panelu i planera tras) robi:
  stan/przeglad.js        – window.ODCP: wszystkie odcinki w wersji uproszczonej (id, stan z pomiaru, długość, kształt
                            uproszczony do ~15 m, współrzędne różnicowo w 1e-5 stopnia) + window.ODC_ALIASY;
                            wystarcza do rysowania całej mapy, kolorów ocen i sum kilometrów
  stan/kafle/X_Y.json     – pełne dane odcinków (nazwa, typ, nawierzchnia, dokładny kształt) w kaflu ~4,4 × 4,2 km;
                            odcinek należy do kafla, w którym leży jego pierwszy punkt (ten sam w obu wersjach)
Strona dociąga kafle dopiero po przybliżeniu (zoom ≥ 13) albo przy kliknięciu odcinka.
Użycie: python3 kafle.py <katalog strony>
"""
import hashlib, json, os, shutil, sys

from shapely.geometry import LineString

OUT = sys.argv[1]
LAT0, LON0, DLAT, DLON = 50.0, 18.0, 0.04, 0.06   # siatka kafli (stała – nie zależy od obszaru mapy)
TOL = 0.00015                                       # uproszczenie kształtu w warstwie przeglądowej (~15 m)

src = open(os.path.join(OUT, "stan", "odcinki.js"), encoding="utf-8").read()
dec = json.JSONDecoder()
i = src.index("window.ODC=") + len("window.ODC=")
ODC, e = dec.raw_decode(src[i:])
aliasy = {}
j = src.find("window.ODC_ALIASY=")
if j >= 0: aliasy, _ = dec.raw_decode(src[j + len("window.ODC_ALIASY="):])


def kafel(lat, lon):
    return f"{int((lon - LON0) // DLON)}_{int((lat - LAT0) // DLAT)}"


def delta(pts):
    out, pa, pb = [], 0, 0
    for la, lo in pts:
        a, b = round(la * 1e5), round(lo * 1e5)
        out += [a - pa, b - pb]; pa, pb = a, b
    return out


# rdzeń = dotychczasowy obszar mapy (jak w odcinki.py): tam przegląd ma wszystkie odcinki; poza nim (17.11 – powiększenie)
# przegląd ma tylko drogi utwardzone / ocenione / rowerowe, a szare „bez oceny” przychodzą z kafli po przybliżeniu
from shapely.geometry import MultiPoint, Point, shape
from shapely.ops import transform
from pyproj import Transformer
_tf = Transformer.from_crs(4326, 2180, always_xy=True).transform
_D = json.load(open("signs_prop.json"))
rdzen = transform(_tf, MultiPoint([(p["lon"], p["lat"]) for p in _D["posts"]])).convex_hull.buffer(2500)
if os.path.exists("../dane/gmina_koszecin.geojson"):
    rdzen = rdzen.union(transform(_tf, shape(json.load(open("../dane/gmina_koszecin.geojson"))["features"][0]["geometry"])).buffer(3000))
from shapely.prepared import prep
# 17.11.2026: nowe tereny (poza rdzeniem) na razie tylko dla administratora – granica rdzenia dla strony i Jedź (stan/rdzen.js)
# oraz lista odcinków spoza niego dla serwera (api/_odcinki_zewn.json: ocena od kogoś innego niż admin – odrzucona)
_tb = Transformer.from_crs(2180, 4326, always_xy=True).transform
_r = transform(_tb, rdzen.simplify(30)); _polys = list(_r.geoms) if _r.geom_type == "MultiPolygon" else [_r]
with open(os.path.join(OUT, "stan", "rdzen.js"), "w", encoding="utf-8") as f:
    f.write("window.RDZEN=" + json.dumps([[[round(y, 5), round(x, 5)] for x, y in p.exterior.coords] for p in _polys], separators=(",", ":")) + ";\n"
            "window.wRdzeniu=(la,lo)=>window.RDZEN.some(r=>{let w=false;for(let i=0,j=r.length-1;i<r.length;j=i++){const a=r[i],b=r[j];"
            "if((a[0]>la)!==(b[0]>la)&&lo<(b[1]-a[1])*(la-a[0])/(b[0]-a[0])+a[1])w=!w}return w});\n")
rdzen = prep(rdzen)

kafle, prz, zewn, km_rdzen = {}, [], [], 0.0
for s in ODC:
    c = s[7]; pts = [(c[k], c[k + 1]) for k in range(0, len(c), 2)]
    kafle.setdefault(kafel(*pts[0]), []).append(s)
    if rdzen.contains(Point(_tf(pts[0][1], pts[0][0]))): km_rdzen += s[6] / 1000
    else: zewn.append((s[0], [round(min(c[0::2]), 5), round(min(c[1::2]), 5), round(max(c[0::2]), 5), round(max(c[1::2]), 5)]))
    if s[4] == "" and s[5] != "droga rowerowa" and not rdzen.contains(Point(_tf(pts[0][1], pts[0][0]))): continue
    up = list(LineString(pts).simplify(TOL, preserve_topology=False).coords) if len(pts) > 2 else pts
    if up[0] != pts[0]: up[0] = pts[0]           # pierwszy punkt bez zmian – wyznacza kafel
    # [id, stan z pomiaru, długość, droga rowerowa?, kształt]
    prz.append([s[0], s[4], s[6], 1 if s[5] == "droga rowerowa" else 0, delta(up)])

kat = os.path.join(OUT, "stan", "kafle")
shutil.rmtree(kat, ignore_errors=True); os.makedirs(kat)
for k, lista in kafle.items():
    with open(os.path.join(kat, k + ".json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, separators=(",", ":"))

ver = hashlib.sha1(src.encode()).hexdigest()[:8]
suma_km = round(sum(x[6] for x in ODC) / 1000)          # wszystkie drogi (także te tylko w kaflach) – do „Ocenione: … z … km”
dane = {"v": ver, "siatka": [LAT0, LON0, DLAT, DLON], "kafle": sorted(kafle), "km": suma_km, "km_rdzen": round(km_rdzen), "o": prz}
# {id: [lat min, lon min, lat max, lon max]} – serwer sprawdza, czy punkty GPS z oceny leżą przy tym odcinku
json.dump(dict(sorted(zewn)), open(os.path.join(OUT, "api", "_odcinki_zewn.json"), "w"), separators=(",", ":"))
with open(os.path.join(OUT, "stan", "przeglad.js"), "w", encoding="utf-8") as f:
    f.write("window.ODCP=" + json.dumps(dane, ensure_ascii=False, separators=(",", ":")) + ";\n")
    f.write("window.ODC_ALIASY=" + json.dumps(aliasy, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"kafle: {len(ODC)} odcinków w {len(kafle)} kaflach, przegląd {os.path.getsize(os.path.join(OUT, 'stan', 'przeglad.js')) // 1024} kB")
