"""Compute road distances + bearings from proposed signposts to destinations."""
import json, math, sys, re
import numpy as np, networkx as nx
from pyproj import Transformer
from shapely.geometry import shape, Point, LineString
from shapely.strtree import STRtree

OSM, POSTS, OUT = sys.argv[1:4]
tf = Transformer.from_crs(4326, 2180, always_xy=True)
P = lambda lon, lat: tf.transform(lon, lat)

osm = json.load(open(OSM))["features"]
BAD = {"motorway", "motorway_link", "proposed", "construction", "steps", "platform", "bus_stop", "corridor", "elevator"}
G = nx.Graph()
for f in osm:
    hw = f["properties"].get("highway")
    if not hw or hw in BAD or f["geometry"]["type"] != "LineString": continue
    cs = [tuple(round(v, 7) for v in c) for c in f["geometry"]["coordinates"]]
    for a, b in zip(cs, cs[1:]):
        pa, pb = P(*a), P(*b)
        G.add_edge(a, b, w=math.dist(pa, pb))
print("graph", G.number_of_nodes(), G.number_of_edges())
# keep largest component
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
nodes = list(G.nodes); nxy = np.array([P(*n) for n in nodes])
def snap(lon, lat):
    x, y = P(lon, lat); i = int(np.argmin(((nxy - (x, y)) ** 2).sum(1)))
    return nodes[i], math.dist((x, y), nxy[i])

places = {}
for f in osm:
    p = f["properties"]
    if "place" in p and f["geometry"]["type"] == "Point" and p.get("name"):
        if p["name"] == "Piasek" and p["place"] != "village": continue
        if p["name"] == "Doły": continue
        places.setdefault(p["name"], f["geometry"]["coordinates"])
    if p.get("name") == "Zagroda u Czesi": places["Zagroda u Czesi"] = f["geometry"]["coordinates"]
# Leśno Rajza nodes
lr_m = [LineString([P(*c) for c in part]) for f in osm if f["properties"].get("ref") == "LR" and f["properties"].get("route") == "bicycle"
        for part in f["geometry"]["coordinates"] if len(part) >= 2]
tree = STRtree(lr_m)
lr_nodes = set()
for n, (x, y) in zip(nodes, nxy):
    if tree.query(Point(x, y).buffer(12), predicate="intersects").size: lr_nodes.add(n)
print("LR nodes", len(lr_nodes))

FIX = {"Kurzichowe": "Kurzychowe"}
def bearing(path):
    pts = [P(*n) for n in path]; acc = 0
    for a, b in zip(pts, pts[1:]):
        acc += math.dist(a, b)
        if acc > 80: break
    dx, dy = b[0] - pts[0][0], b[1] - pts[0][1]
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360
dirs8 = ["płn.", "płn.-wsch.", "wsch.", "płd.-wsch.", "płd.", "płd.-zach.", "zach.", "płn.-zach."]

from shapely.ops import unary_union
forest = unary_union([shape(f["geometry"]).buffer(0) for f in osm if f["geometry"]["type"] in ("Polygon", "MultiPolygon")
                      and (f["properties"].get("landuse") == "forest" or f["properties"].get("natural") == "wood")])
from shapely.ops import transform as stransform
forest_m = stransform(lambda x, y, z=None: tf.transform(x, y), forest)
posts = json.load(open(POSTS))["features"]
# słupki dodane poza uMap (Bartosz, 6.11.2026)
posts += [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.87330, 50.62384]},
           "properties": {"Kierunki": "", "Lokalizacja": "Skrzyżowanie DW 906 / J. Ligonia (koło Bistro Moderno)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.892474, 50.622034]},
           "properties": {"Kierunki": "", "Lokalizacja": "Bagno – Kościuszki, zjazd w stronę Piekarnioka", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.898218, 50.61549]},
           "properties": {"Kierunki": "", "Lokalizacja": "Lubliniecka / Kopernika / Dworcowa (w stronę Czesi i Kalet)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.920544, 50.612009]},
           "properties": {"Kierunki": "", "Lokalizacja": "Kosmonautów / Poprzeczna", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8885293, 50.6177229]},
           "properties": {"Kierunki": "", "Lokalizacja": "Krasickiego (DW 906) / Krasińskiego", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.909972, 50.600169]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – skrzyżowanie na północ od słupka 19 (w stronę Piasku)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.941403, 50.594722]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – skrzyżowanie na południe od słupka 22", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.900378, 50.609614]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – początek drogi na południe od słupka 17 (Dubiele)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.898904, 50.597501]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – skrzyżowanie na zachód od słupka 19", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.897806, 50.590735]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – skrzyżowanie na zachód od słupka 18", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8967, 50.584031]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – skrzyżowanie z Leśną Rajzą (zachodnia droga)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.907176, 50.583335]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – skrzyżowanie z Leśną Rajzą (na południe od słupka 18)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.940396, 50.587934]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – skrzyżowanie dalej na południe od słupka 22", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.866065, 50.619955]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – na wschód od Koszęcina (droga do Strzebinia)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.86862, 50.619002]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – droga Koszęcin–Strzebiń", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8747, 50.617594]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – droga Koszęcin–Strzebiń, za DW 906", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.882806, 50.616136]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – droga Koszęcin–Strzebiń, przy Piekarnioku", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.878539, 50.600586]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Leśno Rajza, przy rzece", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.883164, 50.598588]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Leśno Rajza, skręt na południe", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.922319, 50.640787]},
           "properties": {"Kierunki": "", "Lokalizacja": "Kurzychowe – skrzyżowanie", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.919346, 50.63624]},
           "properties": {"Kierunki": "", "Lokalizacja": "Pola między Kurzychowem a Łazami", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.911649, 50.626894]},
           "properties": {"Kierunki": "", "Lokalizacja": "Lipowiec – skrzyżowanie", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.909708, 50.621115]},
           "properties": {"Kierunki": "", "Lokalizacja": "Czajcze Bagno – wyjazd na Lipowiec", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.940963, 50.606873]},
           "properties": {"Kierunki": "", "Lokalizacja": "Bukowiec – Katowicka (DW 906) / Św. Jacka", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.944665, 50.605437]},
           "properties": {"Kierunki": "", "Lokalizacja": "Bukowiec – Katowicka (DW 906) / Łukasiewicza", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.962398, 50.592162]},
           "properties": {"Kierunki": "", "Lokalizacja": "Piasek – koniec ul. Leśnej, wjazd do lasu", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.929901, 50.636074]},
           "properties": {"Kierunki": "", "Lokalizacja": "Łazy – Kołłątaja / J. Chrzciciela (plac zabaw)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8821175, 50.5917851]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 82, na zachód od słupka 32", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8808091, 50.5850324]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 82/83/84, na zachód od słupka 33", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.9606228, 50.5797552]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 75, na zachód od Sośnicy", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.9615789, 50.5865477]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 78, między Sośnicą a Piaskiem", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8754216, 50.6386383]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 35, na wschód od słupka 15", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8834817, 50.6378087]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 35, rozwidlenie (północ)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.8842964, 50.6369002]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 35, rozwidlenie (południe)", "Status": "propozycja"}},
          {"type": "Feature", "geometry": {"type": "Point", "coordinates": [18.9009591, 50.6442701]},
           "properties": {"Kierunki": "", "Lokalizacja": "Las – Dojazd pożarowy 33, na zachód od słupka 13", "Status": "propozycja"}}]
# stan słupków wg Bartosza: istniejący (można podpiąć tabliczki) / nowy (do postawienia)
POLE = {**{n: "istniejący" for n in (2, 3, 10, 11, 12, 16, 17, 20, 21, 23, 24, 25, 27, 49)},
        **{n: "nowy" for n in (1, 6, 7, 8, 9, 26)},
        **{n: "opcjonalny" for n in (*range(28, 49), *range(50, 58))}}
SLUP_JEST = {46, 47}
MOVE = {}
FORCE_WHO = {**{n: "nadl_K" for n in range(36, 42)}, **{n: "gmina" for n in range(42, 48)}, 48: "nadl_K", 49: "gmina", 50: "nadl_K", 51: "nadl_K", 52: "nadl_K", 53: "nadl_K", 54: "nadl_K", 55: "nadl_K", 56: "nadl_K", 57: "nadl_K"}   # 6.11: wg Bartosza   # 6.11: leśne propozycje Bartosza – do ustalenia   # słupki w lesie: zakładamy brak (nowy)
out = []
# 12.11.2026: w której gminie stoi słupek (część słupków leśnych N-ctwa Koszęcin stoi w Kaletach, gm. Woźniki i gm. Boronów)
import os as _os
_GM = []
if _os.path.exists("../dane/osm_gmina.geojson"):
    _GM = [((f["properties"].get("name") or "").replace("gmina ", ""), shape(f["geometry"])) for f in json.load(open("../dane/osm_gmina.geojson"))["features"]
           if f["properties"].get("boundary") == "administrative" and f["properties"].get("admin_level") == "7" and f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
def gmina_of(lon, lat):
    pt = Point(lon, lat)
    return next((n for n, g in _GM if g.contains(pt)), "Koszęcin")
for i, f in enumerate([f for f in posts if f["geometry"]["type"] == "Point"], 1):
    p = f["properties"]; lon, lat = f["geometry"]["coordinates"]
    if i in MOVE: lon, lat = MOVE[i]   # przesunięte na istniejący słup (wg Bartosza)
    src, off = snap(lon, lat)
    dist, paths = nx.single_source_dijkstra(G, src, weight="w")
    raw = [re.sub(r"\s*[-–]?\s*\d+[.,]?\d*\s*km", "", t).strip() for t in re.split(r",(?!\d)", p["Kierunki"])]
    given = {re.sub(r"\s*[-–]?\s*\d+[.,]?\d*\s*km", "", t).strip(): re.findall(r"\d+[.,]?\d*", t) for t in re.split(r",(?!\d)", p["Kierunki"])}
    seen, plates, notes = set(), [], []
    for t in raw:
        if not t: continue
        name = FIX.get(t, t)
        if t in FIX: notes.append(f"„{t}” zapisano jako „{name}”")
        if name in seen: notes.append(f"„{name}” powtórzone w kierunkach"); continue
        seen.add(name)
        if name == "LR":
            tgt = min((n for n in lr_nodes if n in dist), key=lambda n: dist[n], default=None); label = "Leśno Rajza"
            if dist.get(tgt, 1e9) < 60:
                plates.append(dict(name=label, km=None, deg=None, lr=True)); notes.append("słupek stoi na szlaku Leśno Rajza"); continue
        elif name in places:
            tgt, _ = snap(*places[name]); label = name
        else:
            plates.append(dict(name=name, km=None, deg=None)); notes.append(f"brak „{name}” w danych OSM"); continue
        if tgt not in dist:
            plates.append(dict(name=label, km=None, deg=None)); continue
        d = dist[tgt] / 1000
        g = given.get(t)
        if g: notes.append(f"{label}: podano {g[0]} km, po drogach {d:.1f} km".replace(".", ","))
        plates.append(dict(name=label, km=round(d, 1), deg=round(bearing(paths[tgt])) if d > 0.05 else None,
                           lr=name == "LR", path=paths[tgt]))
    st = p.get("Status") or "propozycja"
    uw = p.get("Uwagi", "")
    in_forest = forest_m.distance(Point(P(lon, lat))) < 25 or "Las" == (p.get("Lokalizacja") or "")
    if i in (26, 27): in_forest = False   # Bartosz: Kosmonautów/Poprzeczna – teren gminy, nie las
    # 12.11.2026: Boronów to leśnictwo w Nadleśnictwie Koszęcin – wszystkie lasy w kręgu projektu należą do N-ctwa Koszęcin
    uw = uw.replace("Nadleśnictwem Boronów", "Nadleśnictwem Koszęcin (leśnictwo Boronów)")
    nadl = "nadl_K" if (in_forest or "adleśn" in uw) else None
    if i in FORCE_WHO: nadl = None if FORCE_WHO[i] == "gmina" else FORCE_WHO[i]; in_forest = nadl is not None
    gm = nadl is None   # wszystkie słupki poza lasem uzgadniane z Gminą Koszęcin
    who = nadl or ("gmina" if gm else "—")
    agree = [x for x in [{"nadl_K": "Nadleśnictwo Koszęcin"}.get(nadl), "Gmina Koszęcin" if gm else None] if x]
    # pole: 6.11 – wszystko w lasach opcjonalnie, we współpracy z Nadleśnictwem Koszęcin
    out.append(dict(nr=i, gmina=gmina_of(lon, lat), lon=lon, lat=lat, loc=p.get("Lokalizacja") or "(bez opisu lokalizacji)", n_plates=p.get("Liczba tabliczek"),
                    status=st, pole=("opcjonalny" if nadl else POLE.get(i, "do sprawdzenia")), slup_jest=i in SLUP_JEST, uwagi=uw, who=who, agree=agree, in_forest=bool(in_forest), plates=plates, notes=notes, snap_m=round(off)))
# ---- example local destinations (POI) -> plate on the nearest post only within 3 km ----
POIS = [
    dict(name="Kościół św. Krzyża", lon=18.904095, lat=50.615003, cat="brown", icon="church"),
    dict(name="Piekarniok", lon=18.88972, lat=50.61790, cat="brown", icon="community"),   # wg zaznaczenia Bartosza (Krasińskiego / Lubliniecka)
    dict(name="Zagroda u Czesi", lon=18.899598, lat=50.611657, cat="red", icon="bar"),
    # 5.11.2026 – Bartosz: pomnik (plus code JVFF+MF), stacje napraw z funduszu sołeckiego 2027, Bistro Moderno
    dict(name="Pomnik J. Ligonia", lon=18.873688, lat=50.624188, cat="brown", icon="heritage"),
    dict(name="Stacja napraw", lon=18.873688, lat=50.624188, cat="gray", icon="service", planned=True),
    dict(name="WC", lon=18.891312, lat=50.615687, cat="gray", icon="wc", planned=True, force=[2, 3]),   # przy boisku – jedna tabliczka z „Stacja napraw”
    dict(name="Stacja napraw", lon=18.891312, lat=50.615687, cat="gray", icon="service", planned=True, force=[2, 3]),
    dict(name="Boisko Strzebiń", lon=18.8912, lat=50.6152, cat="orange", icon="football"),   # boisko LKS Victoria
    dict(name="Kapliczka w Łazach", lon=18.93025, lat=50.63627, cat="brown", icon="church"),   # przy placu zabaw „Basia” (wg Bartosza)
    dict(name="Baza", lon=18.908089, lat=50.615593, cat="red", icon="restaurant"),   # Dębowa 11 (biznes-top.pl)
    dict(name="Bistro Moderno", lon=18.87355, lat=50.62385, cat="red", icon="restaurant", approx=True),
    # 11.11.2026 – Bartosz: tylko gwiazdki na mapach (bez tabliczek)
    dict(name="Beczka", lon=18.85172, lat=50.62677, cat="red", icon="bar", approx=True, map_only=True),          # pijalnia piwa, Koszęcin, koniec Cegielnianej
    dict(name="Restauracja w Piasku", lon=18.967894, lat=50.5943001, cat="red", icon="restaurant", map_only=True),   # OSM, bez nazwy
    dict(name="Karczma u Basieńki", lon=18.9698725, lat=50.5765494, cat="red", icon="restaurant", map_only=True),  # Sośnica (OSM)
    dict(name="Pod Pałacem", lon=18.8409429, lat=50.6346597, cat="red", icon="restaurant", map_only=True),        # Koszęcin, restauracja/browar (OSM)
]
post_nodes = {o["nr"]: snap(o["lon"], o["lat"])[0] for o in out if o.get("pole") != "opcjonalny"}   # cele lokalne tylko na słupkach pewnych
for poi in POIS:
    if poi.get("map_only"): poi["posts"] = []; continue
    src, _ = snap(poi["lon"], poi["lat"])
    dist, paths = nx.single_source_dijkstra(G, src, weight="w")
    cand = sorted((dist[n] / 1000, nr) for nr, n in post_nodes.items() if n in dist and 0.15 < dist[n] / 1000 <= 3.0)
    poi["posts"] = []
    FORCE = {"Piekarniok": [24, 27], "Boisko Strzebiń": [2]}
    if poi.get("force"): FORCE = {**FORCE, poi["name"]: poi["force"]}   # Bartosz 6.11: z Bagna i od DW 906 (wyjątek: dwa słupki)
    if poi["name"] in FORCE:
        cand = sorted((dist[post_nodes[nr]] / 1000, nr) for nr in FORCE[poi["name"]] if post_nodes.get(nr) in dist)
    for d, nr in (cand if poi["name"] in FORCE else cand[:1]):   # Bartosz: każde miejsce tylko raz – na najbliższym słupku
        path = list(reversed(paths[post_nodes[nr]]))
        o = next(o for o in out if o["nr"] == nr)
        o["plates"].append(dict(name=poi["name"], km=round(d, 1), deg=round(bearing(path)), path=path, cat=poi["cat"], icon=poi["icon"], poi=True))
        poi["posts"].append(nr)
    print("POI", poi["name"], "-> słupki", poi["posts"], [round(c[0], 1) for c in cand[:3]])

# proposed connectors: village -> nearest point of a bike route
def route_nodes(pred):
    ms = [LineString([P(*c) for c in part]) for f in osm if f["properties"].get("route") == "bicycle" and pred(f["properties"])
          for part in f["geometry"]["coordinates"] if len(part) >= 2]
    t = STRtree(ms); return {n for n, (x, y) in zip(nodes, nxy) if t.query(Point(x, y).buffer(12), predicate="intersects").size}
conns = []
for frm, rname, pred in [("Prądy", "Leśno Rajza", lambda q: q.get("ref") == "LR"),
                         ("Łazy", "Liswarciański Szlak Rowerowy", lambda q: q.get("name") == "Liswarciański Szlak Rowerowy")]:
    src, _ = snap(*places[frm]); dist, paths = nx.single_source_dijkstra(G, src, weight="w")
    rn = route_nodes(pred); tgt = min((n for n in rn if n in dist), key=lambda n: dist[n])
    conns.append(dict(frm=frm, to=rname, km=round(dist[tgt] / 1000, 1), path=paths[tgt]))
    print("connector", frm, "->", rname, round(dist[tgt] / 1000, 2), "km")
json.dump(dict(posts=out, places=places, connectors=conns, pois=POIS), open(OUT, "w"), ensure_ascii=False, indent=1)
for o in out:
    print(o["nr"], o["loc"], "|", "; ".join(f'{pl["name"]} {pl["km"]} {dirs8[int(((pl["deg"] or 0)+22.5)//45)%8] if pl["deg"] is not None else ""}' for pl in o["plates"]), "|", o["notes"], "snap", o["snap_m"])
