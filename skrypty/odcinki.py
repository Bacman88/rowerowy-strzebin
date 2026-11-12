"""Odcinki dróg do interaktywnej mapy stanu dróg (strona: stan.html).
Wszystkie drogi z OSM w okolicy słupków, cięte na skrzyżowaniach i na kawałki do ~400 m.
Stan początkowy: pomiary Bartosza z warstwy uMap (przejezdność ogólna).
Wynik: <strona>/stan/odcinki.js (dla mapy) i <strona>/api/_odcinki.json (lista id do sprawdzania zgłoszeń).
Id odcinka = skrót z id drogi OSM i końców odcinka – nie zmienia się przy przebudowie, dopóki nie zmieni się droga w OSM."""
import json, sys, hashlib, collections, math, os
from shapely.geometry import LineString, Point, shape, MultiPoint
from shapely.ops import substring, unary_union, transform
from pyproj import Transformer

OSM, SURVEY, SIGNS, OUT = sys.argv[1:5]
MAXLEN = 400   # m
tf = Transformer.from_crs(4326, 2180, always_xy=True); tb = Transformer.from_crs(2180, 4326, always_xy=True)
to2180 = lambda g: transform(tf.transform, g); to4326 = lambda g: transform(tb.transform, g)

SKIP_HW = {"steps", "proposed", "construction", "motorway", "trunk", "bus_guideway", "raceway", "elevator", "platform"}
SKIP_SERVICE = {"driveway", "parking_aisle", "drive-through", "emergency_access"}
SKIP_FOOT = {"sidewalk", "crossing", "traffic_island"}
HW = {"track": "droga leśna/polna", "path": "ścieżka", "footway": "ścieżka piesza", "cycleway": "droga rowerowa", "bridleway": "ścieżka",
      "residential": "ulica", "living_street": "ulica", "unclassified": "droga lokalna", "service": "droga dojazdowa",
      "tertiary": "droga powiatowa/gminna", "tertiary_link": "droga powiatowa/gminna", "secondary": "droga wojewódzka", "primary": "droga krajowa"}
SURF = {"asphalt": "asfalt", "paved": "utwardzona", "concrete": "beton", "paving_stones": "kostka", "sett": "kostka kamienna",
        "gravel": "żwir/tłuczeń", "fine_gravel": "drobny żwir", "compacted": "ubita", "dirt": "ziemia", "ground": "ziemia", "earth": "ziemia",
        "sand": "piach", "grass": "trawa", "unpaved": "nieutwardzona", "mud": "błoto", "pebblestone": "otoczaki"}
PAVED_S = {"asphalt", "paved", "concrete", "paving_stones", "sett", "concrete:plates", "chipseal"}
PAVED_H = {"primary", "secondary", "tertiary", "tertiary_link", "residential", "living_street", "unclassified"}
UNPAVED_S = {"gravel", "fine_gravel", "compacted", "dirt", "ground", "earth", "sand", "grass", "unpaved", "mud", "pebblestone", "wood"}
PAVED_NAMES = {"1 Maja", "Dębowa", "Kosmonautów", "Hugona Kołłątaja"}   # asfalt wg Bartosza
PAVED_IDS = {"way/976663503", "way/587698466", "way/976663504"}
def utwardzona(p):
    s = p.get("surface")
    return (s in PAVED_S or (s is None and p.get("highway") in PAVED_H and p.get("tracktype") not in {"grade3", "grade4", "grade5"})
            or p.get("@id") in PAVED_IDS or p.get("name") in PAVED_NAMES) and s not in UNPAVED_S
BASE = {"bardzo dobra": "dobra", "dobra": "dobra", "średnia": "srednia", "trudna": "trudna"}

osm = json.load(open(OSM))["features"]; D = json.load(open(SIGNS))
area = to2180(MultiPoint([(p["lon"], p["lat"]) for p in D["posts"]])).convex_hull.buffer(2500)

ways = []
for f in osm:
    p = f["properties"]; hw = p.get("highway")
    if not hw or f["geometry"]["type"] != "LineString" or hw in SKIP_HW: continue
    if p.get("service") in SKIP_SERVICE or p.get("footway") in SKIP_FOOT or p.get("area") == "yes": continue
    cs = [tuple(round(v, 7) for v in c) for c in f["geometry"]["coordinates"]]
    if len(cs) < 2 or not area.intersects(to2180(LineString(cs))): continue
    ways.append((p, cs))

# węzły wspólne kilku dróg (lub końce dróg) = miejsca cięcia
cnt = collections.Counter()
for _, cs in ways:
    for c in set(cs): cnt[c] += 1
    cnt[cs[0]] += 1; cnt[cs[-1]] += 1

sv = [(to2180(shape(f["geometry"])), f["properties"]) for f in json.load(open(SURVEY))["features"] if f["geometry"]["type"] == "LineString"]
sv = [(l, l.buffer(15), pr) for l, pr in sv]

segs, ids = [], set()
for p, cs in ways:
    pieces, cur = [], [cs[0]]
    for c in cs[1:]:
        cur.append(c)
        if cnt[c] >= 2 and c != cs[-1]: pieces.append(cur); cur = [c]
    pieces.append(cur)
    for pc in pieces:
        if len(pc) < 2: continue
        g = to2180(LineString(pc))
        if g.length < 3 or not area.intersects(g): continue
        n = max(1, math.ceil(g.length / MAXLEN))
        for i in range(n):
            part = substring(g, g.length * i / n, g.length * (i + 1) / n) if n > 1 else g
            if part.geom_type != "LineString" or part.length < 3: continue
            ll = to4326(part); co = [(round(y, 5), round(x, 5)) for x, y in ll.coords]
            co = [c for j, c in enumerate(co) if j == 0 or c != co[j - 1]]
            if len(co) < 2: continue
            sid = hashlib.sha1(f"{p.get('@id', '')}|{co[0]}|{co[-1]}".encode()).hexdigest()[:10]
            if sid in ids: continue
            ids.add(sid)
            # stan z pomiarów: środek odcinka do 15 m od zmierzonej linii
            mid = part.interpolate(0.5, normalized=True); base = ""; bdate = ""
            # odcinek co najmniej w 60% w pasie 15 m wokół zmierzonej linii (bez krótkich bocznych odnóg)
            near = [(l.distance(mid), pr) for l, buf, pr in sv if l.distance(mid) < 15 and part.intersection(buf).length >= 0.6 * part.length]
            if near:
                pr = min(near, key=lambda t: t[0])[1]; base = BASE.get(pr.get("Przejezdność ogólna") or "", ""); bdate = pr.get("Data") or ""
            if not base and utwardzona(p): base = "osm"   # utwardzona wg OSM – uznajemy za przejezdną
            surf = p.get("surface"); hw = p.get("highway")
            segs.append([sid, HW.get(hw, hw), p.get("name", "") or p.get("ref", ""), SURF.get(surf, surf or ""), base, bdate,
                         round(part.length), [v for c in co for v in c]])

os.makedirs(f"{OUT}/stan", exist_ok=True); os.makedirs(f"{OUT}/api", exist_ok=True)
open(f"{OUT}/stan/odcinki.js", "w").write("window.ODC=" + json.dumps(segs, ensure_ascii=False, separators=(",", ":")) + ";")
json.dump(sorted(ids), open(f"{OUT}/api/_odcinki.json", "w"), separators=(",", ":"))
km = sum(s[6] for s in segs) / 1000
print(f"odcinki: {len(segs)} odcinków, {km:.0f} km, z pomiarów {sum(1 for s in segs if s[4] and s[4] != 'osm')}, utwardzone wg OSM {sum(s[6] for s in segs if s[4] == 'osm') / 1000:.0f} km, "
      f"plik {os.path.getsize(f'{OUT}/stan/odcinki.js') / 1e6:.1f} MB")
