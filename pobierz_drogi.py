"""Drogi i obiekty OSM dla mapy wspólnej i nawigacji „Jedź” (17.11.2026) – to samo, co wcześniej ręczny eksport z overpass-turbo
(przygotuj_gmine.py), ale dla powiększonego obszaru i automatycznie. Wynik: osm_obszar.geojson w formacie dane/osm_gmina.geojson
(płaskie tagi + "@id", tylko potrzebne tagi, współrzędne do 7 miejsc)."""
import json, sys, time, requests
import osm2geojson

S, W, N, E = 50.43, 18.60, 50.80, 19.18   # Blachownia – Tarnowskie Góry, Lubliniec – Woźniki
BB = f"{S},{W},{N},{E}"
Q = f"""[out:json][timeout:900][maxsize:2000000000];
(
  way["highway"]({BB});
  way["railway"]({BB}); way["waterway"]({BB});
  way["landuse"]({BB}); way["natural"]({BB}); way["leisure"]({BB}); way["amenity"]({BB}); way["tourism"]({BB});
  node["amenity"]({BB}); node["tourism"]({BB}); node["leisure"]({BB}); node["historic"]({BB}); node["shop"]({BB});
  node["place"]({BB}); node["natural"]({BB}); node["railway"]({BB});
  relation["boundary"="administrative"]["admin_level"="7"]({BB});
);
out geom;"""
KEEP = {"highway", "name", "ref", "surface", "tracktype", "smoothness", "service", "footway", "access", "bicycle", "foot", "motor_vehicle",
        "railway", "usage", "waterway", "natural", "landuse", "place", "amenity", "tourism", "leisure", "historic", "shop", "religion",
        "shelter_type", "operator", "boundary", "admin_level", "type", "area", "bridge", "tunnel", "layer", "oneway", "cuisine", "population"}
LOG = open("log_drogi.txt", "w")
def log(*a): s = " ".join(map(str, a)); print(s); LOG.write(s + "\n"); LOG.flush()

dane = None
for url in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]:
    for proba in range(3):
        try:
            r = requests.post(url, data={"data": Q}, timeout=1200, headers={"User-Agent": "HUB-rowerowy-Strzebin/1.0 (github.com/Bacman88/rowerowy-strzebin)"})
            log(url, r.status_code, len(r.content))
            if r.status_code == 200: dane = r.json(); break
        except Exception as e: log(url, "err", e)
        time.sleep(30)
    if dane: break
if not dane: sys.exit("brak danych z Overpass")
log("elementów:", len(dane["elements"]))
gj = osm2geojson.json2geojson(dane)
r7 = lambda c: [round(c[0], 7), round(c[1], 7)] if isinstance(c[0], (int, float)) else [r7(x) for x in c]
out = []
for f in gj["features"]:
    pr = f.get("properties") or {}; t = pr.get("tags") or {}; g = f.get("geometry")
    if not g or not g.get("coordinates"): continue
    p = {"@id": f"{pr.get('type')}/{pr.get('id')}"}
    p.update({k: v for k, v in t.items() if k in KEEP})
    if len(p) <= 1: continue
    out.append({"type": "Feature", "properties": p, "geometry": {"type": g["type"], "coordinates": r7(g["coordinates"])}})
json.dump({"type": "FeatureCollection", "features": out}, open("osm_obszar.geojson", "w"), ensure_ascii=False, separators=(",", ":"))
log("obiektów:", len(out))
