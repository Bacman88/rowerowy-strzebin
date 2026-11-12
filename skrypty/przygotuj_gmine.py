"""Wycinek OSM całej gminy Koszęcin z okolicą (eksport z overpass-turbo, 12.11.2026) -> lżejszy plik w repozytorium.
Zostają obiekty w granicach gminy powiększonych o 5 km (linie w całości, bez cięcia), tylko potrzebne tagi, współrzędne do 7 miejsc.
Wynik: ../dane/osm_gmina.geojson i ../dane/gmina_koszecin.geojson (granica gminy).
Użycie: python3 przygotuj_gmine.py <eksport.geojson>"""
import json, sys
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer
tf = Transformer.from_crs(4326, 2180, always_xy=True).transform
tb = Transformer.from_crs(2180, 4326, always_xy=True).transform
F = json.load(open(sys.argv[1]))["features"]
gm = next(f for f in F if f["properties"].get("boundary") == "administrative" and f["properties"].get("name") == "gmina Koszęcin")
g = shape(gm["geometry"]); obszar = transform(tb, transform(tf, g).buffer(5000))
KEEP = {"@id", "highway", "name", "ref", "surface", "tracktype", "smoothness", "service", "footway", "access", "bicycle", "foot", "motor_vehicle",
        "railway", "usage", "service", "waterway", "natural", "landuse", "place", "amenity", "tourism", "leisure", "historic", "shop", "religion",
        "shelter_type", "operator", "boundary", "admin_level", "type", "area", "bridge", "tunnel", "layer", "oneway", "cuisine", "population"}
r = lambda c: [round(c[0], 7), round(c[1], 7)] if isinstance(c[0], (int, float)) else [r(x) for x in c]
out = []
for f in F:
    if f["properties"].get("boundary") == "administrative" and f["properties"].get("admin_level") not in ("7",): continue
    try: s = shape(f["geometry"])
    except Exception: continue
    if not s.intersects(obszar): continue
    p = {k: v for k, v in f["properties"].items() if k in KEEP}
    if len(p) <= 1: continue
    out.append({"type": "Feature", "properties": p, "geometry": {"type": f["geometry"]["type"], "coordinates": r(f["geometry"]["coordinates"])}})
json.dump({"type": "FeatureCollection", "features": out}, open("../dane/osm_gmina.geojson", "w"), ensure_ascii=False, separators=(",", ":"))
json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"name": "gmina Koszęcin"}, "geometry": mapping(g.simplify(0.0001))}]},
          open("../dane/gmina_koszecin.geojson", "w"), ensure_ascii=False, separators=(",", ":"))
import os
print("osm_gmina:", len(out), "obiektów,", round(os.path.getsize("../dane/osm_gmina.geojson") / 1e6, 1), "MB; granica gminy:", [round(x, 3) for x in g.bounds])
