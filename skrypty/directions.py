"""Proposed directions per signpost: branch coverage + continuity, compared with the uMap directions."""
import json, math, sys, copy
import numpy as np, networkx as nx
from pyproj import Transformer
from shapely.geometry import LineString, Point

OSM, SIGNS, OUT, REPORT, SURVEY = sys.argv[1:6]
tf = Transformer.from_crs(4326, 2180, always_xy=True); P = lambda lon, lat: tf.transform(lon, lat)
osm = json.load(open(OSM))["features"]; D = json.load(open(SIGNS))
BAD = {"motorway", "motorway_link", "proposed", "construction", "steps", "platform", "bus_stop", "corridor", "elevator"}
# bike-friendly routing cost: prefer paved / good roads, use Bartosz's survey where available
PAVED = {"asphalt", "paved", "concrete", "paving_stones", "sett", "chipseal"}
from shapely.strtree import STRtree
sv = [f for f in json.load(open(SURVEY))["features"] if f["geometry"]["type"] == "LineString"]
sv_l = [LineString([P(*c) for c in f["geometry"]["coordinates"]]) for f in sv]
sv_tree = STRtree(sv_l)
SV_F = {"bardzo dobra": 1.0, "dobra": 1.05, "średnia": 1.35, "trudna": 2.2}
def factor(pr, mid):
    idx = sv_tree.query(mid.buffer(15), predicate="intersects")
    if len(idx): return SV_F.get(sv[int(idx[0])]["properties"].get("Przejezdność ogólna"), 1.1)
    hw, sf, tt = pr.get("highway"), pr.get("surface"), pr.get("tracktype")
    if sf in PAVED or (sf is None and hw in {"primary", "secondary", "tertiary", "residential", "living_street", "unclassified"}): return 1.0
    if hw == "cycleway": return 0.95
    if hw == "service": return 1.1
    if hw == "track": return 1.15 if (tt == "grade1" or sf in {"gravel", "compacted", "fine_gravel"}) else 1.35
    if hw in {"path", "footway", "bridleway"}: return 1.6
    return 1.2
G = nx.Graph()
for f in osm:
    pr = f["properties"]; hw = pr.get("highway")
    if not hw or hw in BAD or f["geometry"]["type"] != "LineString": continue
    cs = [tuple(round(v, 7) for v in c) for c in f["geometry"]["coordinates"]]
    for a, b in zip(cs, cs[1:]):
        pa, pb = P(*a), P(*b); L = math.dist(pa, pb)
        G.add_edge(a, b, w=L, c=L * factor(pr, Point((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)))
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
nodes = list(G.nodes); nxy = np.array([P(*n) for n in nodes])
def snap(lon, lat):
    x, y = P(lon, lat); return nodes[int(np.argmin(((nxy - (x, y)) ** 2).sum(1)))]
def bearing(path):
    pts = [P(*n) for n in path]; acc = 0; b = pts[-1]
    for a_, b_ in zip(pts, pts[1:]):
        acc += math.dist(a_, b_); b = b_
        if acc > 80: break
    return (math.degrees(math.atan2(b[0] - pts[0][0], b[1] - pts[0][1])) + 360) % 360
close = lambda a, b, t=35: abs((a - b + 180) % 360 - 180) <= t

posts = D["posts"]; places = D["places"]
VILLAGES = sorted({pl["name"] for p in posts for pl in p["plates"] if not pl.get("lr") and not pl.get("poi")} & set(places))
MAJOR = {"Koszęcin", "Kalety", "Boronów", "Strzebiń"}
MAXKM, NEAR = 12.0, 0.5
USE_MAJOR = False   # bez dokładania „ważnych celów” – tylko pokrycie kierunków + ciągłość
RADIUS = {"Strzebiń": 1.6, "Koszęcin": 1.5, "Kalety": 1.6, "Boronów": 1.2}
def inside(p, v):
    x, y = P(*places[v]); return math.dist((x, y), P(p["lon"], p["lat"])) / 1000 < RADIUS.get(v, 0.6)
tgt_node = {v: snap(*places[v]) for v in VILLAGES}
post_node = {p["nr"]: snap(p["lon"], p["lat"]) for p in posts}
post_pt = {p["nr"]: Point(P(p["lon"], p["lat"])) for p in posts}
routes = {}
for p in posts:
    cost, paths = nx.single_source_dijkstra(G, post_node[p["nr"]], weight="c")
    plen = lambda pa: sum(G[a][b]["w"] for a, b in zip(pa, pa[1:])) / 1000
    routes[p["nr"]] = {v: (plen(paths[n]), paths[n]) for v, n in tgt_node.items() if n in paths}

def entry(nr, v, why):
    km, path = routes[nr][v]
    return dict(name=v, km=round(km, 1), deg=round(bearing(path)), path=path, why=why)

FORCE_DIRS = {28: ["Piasek", "Bukowiec", "Kalety", "Strzebiń"], 29: ["Piasek", "Bukowiec", "Kalety", "Strzebiń"]}
prop, removed = {}, {}
for p in posts:
    nr = p["nr"]; cur = []; seen = set(); removed[nr] = []
    for pl in p["plates"]:
        if pl.get("lr") or pl.get("poi"): continue
        v = pl["name"]
        if v in seen: continue
        seen.add(v)
        if inside(p, v) or (v in routes[nr] and routes[nr][v][0] < NEAR):
            removed[nr].append((v, "słupek stoi w tej miejscowości")); continue
        cur.append(entry(nr, v, "jest w uMap"))
    # branch coverage: every road branch that leads somewhere gets its nearest locality (+ a main target)
    cand = sorted((km, v) for v, (km, _) in routes[nr].items() if NEAR <= km <= MAXKM and not inside(p, v))
    branches = []
    for km, v in cand:
        d = bearing(routes[nr][v][1])
        for b in branches:
            if close(b["deg"], d): b["items"].append((km, v)); break
        else: branches.append(dict(deg=d, items=[(km, v)]))
    for b in branches:
        names_here = [e["name"] for e in cur if close(e["deg"], b["deg"])]
        if not names_here:
            km, v = b["items"][0]
            cur.append(entry(nr, v, "kierunek drogi bez oznakowania – najbliższa miejscowość"))
            names_here.append(v)
        if USE_MAJOR and not any(n in MAJOR for n in names_here):
            maj = next(((km, v) for km, v in b["items"] if v in MAJOR and km <= 10), None)
            if maj and len(names_here) < 2:
                cur.append(entry(nr, maj[1], "ważny cel w tym kierunku"))
    for v in FORCE_DIRS.get(nr, []):   # kierunki wskazane przez Bartosza
        if v not in tgt_node or v in [e["name"] for e in cur]: continue
        pth = nx.shortest_path(G, post_node[nr], tgt_node[v], weight="w")   # najkrótsza – leśne skróty, o które prosił Bartosz
        km = sum(G[a][b]["w"] for a, b in zip(pth, pth[1:])) / 1000
        cur.append(dict(name=v, km=round(km, 1), deg=round(bearing(pth)), path=pth, why="dodane przez Bartosza"))
    prop[nr] = cur

# continuity: a destination shown upstream must be repeated on posts the route passes through
for _ in range(4):
    added = 0
    for p in posts:
        for e in list(prop[p["nr"]]):
            ln = LineString([P(*c) for c in e["path"]])
            if ln.length < 2: continue
            for q in posts:
                qn = q["nr"]
                if qn == p["nr"] or e["name"] in [x["name"] for x in prop[qn]]: continue
                if e["name"] not in routes[qn] or routes[qn][e["name"]][0] < NEAR or inside(q, e["name"]): continue
                pos = ln.project(post_pt[qn])
                if ln.distance(post_pt[qn]) < 40 and 80 < pos < ln.length - 300:
                    prop[qn].append(entry(qn, e["name"], f"ciągłość – wskazuje go słupek {p['nr']}")); added += 1
    if not added: break

# ręczny przegląd kierunków (6.11.2026) – zastępuje wynik automatu; do potwierdzenia przez Bartosza
MANUAL = {
    54: ["Koszęcin", "Prądy", "Łazy"],
    55: ["Koszęcin", "Prądy", "Łazy", "Boronów"],
    56: ["Prądy", "Koszęcin", "Łazy"],
    57: ["Boronów", "Kurzychowe", "Koszęcin", "Prądy"],
    52: ["Sośnica", "Piasek", "Kalety"],
    53: ["Piasek", "Sośnica", "Bukowiec"],
    50: ["Dubiele", "Strzebiń", "Kalety"],
    51: ["Kalety", "Strzebiń", "Dubiele"],
 1: ["Strzebiń", "Koszęcin", "Boronów"],
 2: ["Dubiele", "Prądy", "Koszęcin", "Bukowiec", "Kalety"],
 3: ["Prądy", "Boronów", "Koszęcin", "Dubiele", "Bukowiec"],
 4: ["Strzebiń", "Dubiele"],
 5: ["Kalety", "Sośnica", "Strzebiń"],
 6: ["Kalety", "Bukowiec", "Dubiele"],
 7: ["Bukowiec", "Psary", "Łazy"],
 8: ["Psary", "Piasek", "Strzebiń", "Łazy"],
 9: ["Koszęcin", "Strzebiń"],
 10: ["Łazy", "Bukowiec", "Psary"],
 11: ["Prądy", "Boronów", "Dubiele"],
 12: ["Strzebiń", "Koszęcin", "Sitki", "Babienica"],
 13: ["Boronów", "Kurzychowe", "Strzebiń", "Koszęcin"],
 14: ["Kurzychowe", "Boronów", "Strzebiń", "Prądy", "Koszęcin"],
 15: ["Prądy", "Koszęcin", "Łazy", "Boronów"],
 16: ["Bukowiec", "Łazy", "Kalety"],
 17: ["Kalety", "Dubiele", "Prądy", "Koszęcin"],
 18: ["Strzebiń", "Kalety", "Piasek"],
 19: ["Strzebiń", "Kalety", "Piasek"],
 20: ["Koszęcin", "Prądy", "Bukowiec", "Kurzychowe", "Kalety"],
 21: ["Łazy", "Psary", "Kurzychowe", "Kalety"],
 22: ["Bukowiec", "Piasek", "Strzebiń", "Kalety"],
 23: ["Strzebiń", "Koszęcin", "Boronów"],
 24: ["Prądy", "Koszęcin"],
 25: ["Kalety", "Kurzychowe", "Łazy"],
 26: ["Łazy", "Kalety"],
 27: ["Prądy", "Koszęcin", "Dubiele", "Boronów"],
 28: ["Strzebiń", "Bukowiec", "Piasek", "Kalety"],
 29: ["Bukowiec", "Piasek", "Strzebiń", "Kalety"],
 30: ["Dubiele", "Kalety"],
 31: ["Strzebiń", "Kalety", "Piasek"],
 32: ["Strzebiń", "Kalety", "Piasek"],
 33: ["Kalety", "Strzebiń", "Dubiele", "Piasek"],
 34: ["Kalety", "Strzebiń", "Dubiele", "Piasek", "Sośnica"],
 35: ["Bukowiec", "Piasek", "Kalety"],
 36: ["Prądy", "Strzebiń", "Koszęcin"],
 37: ["Prądy", "Strzebiń", "Koszęcin"],
 38: ["Prądy", "Strzebiń", "Koszęcin"],
 39: ["Dubiele", "Koszęcin"],
 40: ["Dubiele", "Prądy", "Kalety", "Koszęcin"],
 41: ["Dubiele", "Kalety", "Koszęcin"],
 42: ["Strzebiń", "Łazy", "Sitki", "Boronów", "Koszęcin"],
 43: ["Łazy", "Strzebiń"],
 44: ["Kurzychowe", "Strzebiń"],
 45: ["Kurzychowe", "Łazy"],
 46: ["Piasek", "Psary", "Strzebiń"],
 47: ["Piasek", "Strzebiń", "Kalety"],
 48: ["Bukowiec", "Strzebiń", "Kalety", "Sośnica"],
 49: ["Sitki", "Boronów", "Babienica", "Strzebiń", "Kurzychowe"],
}
VIA = {(48, "Bukowiec"): 29, (48, "Strzebiń"): 29}
SHORT = {(48, "Kalety"), (26, "Bukowiec"), (26, "Psary"), (28, "Piasek"), (28, "Bukowiec")}   # prowadzimy najkrótszą drogą (nie naokoło asfaltem)
for nr, names in MANUAL.items():
    if nr not in prop: continue
    new = []
    for v in names:
        if v not in tgt_node: print("brak celu", v); continue
        if (nr, v) in VIA:   # leśną drogą przez wskazany słupek (omija DW 906)
            m = post_node[VIA[(nr, v)]]
            pth = nx.shortest_path(G, post_node[nr], m, weight="w") + nx.shortest_path(G, m, tgt_node[v], weight="w")[1:]
        elif (nr, v) in SHORT or v not in routes[nr]:
            pth = nx.shortest_path(G, post_node[nr], tgt_node[v], weight="w")
        else:
            pth = routes[nr][v][1]
        km = sum(G[a][b]["w"] for a, b in zip(pth, pth[1:])) / 1000
        new.append(dict(name=v, km=round(km, 1), deg=round(bearing(pth)), path=pth, why="przegląd ręczny"))
    prop[nr] = new

# extra destinations requested by Bartosz for specific posts (weighted routing like the rest)
EXTRA = [
    dict(name="Kościół św. Trójcy", lon=18.843296, lat=50.62077, cat="brown", icon="church", posts=[2]),
    dict(name="GOSiR Koszęcin", lon=18.850487, lat=50.620305, cat="orange", icon="swim", posts=[2]),
]
extra_plates = {}
for ex in EXTRA:
    tn = snap(ex["lon"], ex["lat"])
    for nr in ex["posts"]:
        cost, paths = nx.single_source_dijkstra(G, post_node[nr], target=tn, weight="c")
        path = paths; km = sum(G[a][b]["w"] for a, b in zip(path, path[1:])) / 1000
        extra_plates.setdefault(nr, []).append(dict(name=ex["name"], km=round(km, 1), deg=round(bearing(path)), path=path,
                                                    cat=ex["cat"], icon=ex["icon"], poi=True, why="dodane przez Bartosza"))
        print("EXTRA", ex["name"], "-> słupek", nr, round(km, 2), "km, kier.", round(bearing(path)))
D.setdefault("pois", []).extend([{k: v for k, v in ex.items() if k != "posts"} | {"posts": ex["posts"]} for ex in EXTRA])

# rebuild plates: proposed villages + kept Leśno Rajza / POI plates
out = copy.deepcopy(D)
rep = []
for p in out["posts"]:
    nr = p["nr"]
    keep = [pl for pl in p["plates"] if pl.get("lr") or pl.get("poi")] + extra_plates.get(nr, [])
    vil = sorted(prop[nr], key=lambda e: e["km"])
    p["plates"] = [dict(name=e["name"], km=e["km"], deg=e["deg"], path=e["path"], why=e["why"]) for e in vil] + keep
    old = [pl["name"] for pl in D["posts"][nr - 1]["plates"] if not pl.get("lr") and not pl.get("poi")]
    rep.append(dict(nr=nr, loc=p["loc"], jest=old, prop=[(e["name"], e["km"], e["why"]) for e in vil],
                    removed=removed[nr], extra=[pl["name"] for pl in keep]))
json.dump(out, open(OUT, "w"), ensure_ascii=False)
json.dump(rep, open(REPORT, "w"), ensure_ascii=False, indent=1)
for r in rep:
    add = [f"+{n} ({w})" for n, km, w in r["prop"] if w != "jest w uMap"]
    rem = [f"-{n} ({w})" for n, w in r["removed"]]
    print(r["nr"], r["loc"][:28], "| jest:", ", ".join(r["jest"]), "|", "; ".join(add + rem) or "bez zmian")
