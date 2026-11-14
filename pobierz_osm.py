"""Podkład mapy offline dla nawigacji „Jedź”: lasy, wody, zabudowa, budynki, tory i nazwy miejscowości z OpenStreetMap
(Overpass API) dla okolic Koszęcina. Wynik: podklad.json (warstwy uproszczone, współrzędne w 1e-5 stopnia, różnicowo)."""
import json, sys, time, requests
from shapely.geometry import shape, mapping, Polygon, MultiPolygon, LineString, MultiLineString, box
from shapely.ops import unary_union
import osm2geojson

S, W, N, E = 50.486, 18.655, 50.732, 19.013
BB = f"{S},{W},{N},{E}"
Q = f"""[out:json][timeout:600];
(
  way["landuse"="forest"]({BB}); relation["landuse"="forest"]({BB});
  way["natural"="wood"]({BB}); relation["natural"="wood"]({BB});
  way["natural"="water"]({BB}); relation["natural"="water"]({BB});
  way["landuse"~"^(reservoir|basin)$"]({BB});
  way["waterway"~"^(river|stream|canal)$"]({BB});
  way["landuse"~"^(residential|industrial|commercial|retail|farmyard|cemetery|allotments)$"]({BB});
  way["amenity"="grave_yard"]({BB});
  way["landuse"~"^(meadow|grass|recreation_ground)$"]({BB}); way["leisure"~"^(park|pitch|sports_centre)$"]({BB});
  way["building"]({BB}); relation["building"]({BB});
  way["railway"="rail"]({BB});
  node["place"~"^(town|village|hamlet|suburb|neighbourhood|isolated_dwelling|locality)$"]({BB});
);
out geom;"""
LOG = open("log_osm.txt", "w")
def log(*a): s = " ".join(map(str, a)); print(s); LOG.write(s + "\n"); LOG.flush()

dane = None
for url in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]:
    for proba in range(3):
        try:
            r = requests.post(url, data={"data": Q}, timeout=900, headers={"User-Agent": "HUB-rowerowy-Strzebin/1.0 (github.com/Bacman88/rowerowy-strzebin)"})
            log(url, r.status_code, len(r.content))
            if r.status_code == 200: dane = r.json(); break
        except Exception as e: log(url, "err", e)
        time.sleep(30)
    if dane: break
if not dane: sys.exit("brak danych z Overpass")
log("elementów:", len(dane["elements"]))
gj = osm2geojson.json2geojson(dane)
ramka = box(W, S, E, N)

def warstwa(t):
    g = t.get("landuse") or ""; n = t.get("natural") or ""; ww = t.get("waterway") or ""
    if t.get("building"): return "bud"
    if g == "forest" or n == "wood": return "las"
    if n == "water" or g in ("reservoir", "basin"): return "woda"
    if ww: return "rzeki"
    if g in ("cemetery",) or t.get("amenity") == "grave_yard": return "cment"
    if g in ("meadow", "grass", "recreation_ground") or t.get("leisure") in ("park", "pitch", "sports_centre"): return "ziel"
    if g in ("industrial", "commercial", "retail"): return "przem"
    if g in ("residential", "farmyard", "allotments"): return "zab"
    if t.get("railway") == "rail": return "tory"
    return None

TOL = {"las": .00004, "woda": .00002, "zab": .00003, "przem": .00003, "cment": .00002, "ziel": .00003, "bud": .000008, "rzeki": .00003, "tory": .00002}
W_ = {k: [] for k in TOL}; nazwy = []
for f in gj["features"]:
    t = f["properties"].get("tags", {}) or {}
    geom = f.get("geometry")
    if not geom: continue
    if geom["type"] == "Point":
        if t.get("place") and t.get("name"):
            x, y = geom["coordinates"]; rank = {"town": 1, "village": 2, "suburb": 3, "hamlet": 3, "neighbourhood": 4, "isolated_dwelling": 4, "locality": 4}.get(t["place"], 4)
            nazwy.append([round(y, 5), round(x, 5), t["name"], rank])
        continue
    k = warstwa(t)
    if not k: continue
    try:
        g = shape(geom)
        if k in ("rzeki", "tory"):
            if g.geom_type in ("Polygon", "MultiPolygon"): continue
        else:
            if g.geom_type not in ("Polygon", "MultiPolygon"): continue
            if not g.is_valid: g = g.buffer(0)
        g = g.intersection(ramka).simplify(TOL[k], preserve_topology=True)
        if g.is_empty: continue
        W_[k].append(g)
    except Exception as e:
        log("geom err", k, e)

def q(v): return round(v * 1e5)
def koduj(coords):
    out = []; px = py = 0
    for x, y in coords:
        a, b = q(y), q(x); out += [a - py, b - px]; py, px = a, b
    return out
wynik = {"bbox": [S, W, N, E], "nazwy": nazwy}
for k, lst in W_.items():
    if k in ("las", "woda", "zab", "przem", "cment", "ziel"):
        g = unary_union(lst) if lst else None   # scalenie stykających się płatów – mniej krawędzi, mniejszy plik
        polys = [] if g is None else ([g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"])
        wynik[k] = [[koduj(p.exterior.coords)] + [koduj(i.coords) for i in p.interiors] for p in polys if p.area > 2e-9]
    elif k == "bud":
        polys = []
        for g in lst: polys += [g] if g.geom_type == "Polygon" else list(g.geoms)
        wynik[k] = [koduj(p.exterior.coords) for p in polys if p.geom_type == "Polygon"]
    else:
        ls = []
        for g in lst: ls += [g] if g.geom_type == "LineString" else [x for x in getattr(g, "geoms", []) if x.geom_type == "LineString"]
        wynik[k] = [koduj(l.coords) for l in ls]
    log(k, len(wynik[k]))
s = json.dumps(wynik, separators=(",", ":"), ensure_ascii=False)
open("podklad.json", "w").write(s); log("podklad.json", len(s) / 1e6, "MB, nazw", len(nazwy))
