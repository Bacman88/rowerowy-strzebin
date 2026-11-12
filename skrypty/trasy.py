"""Unchecked road segments on signpost routes: GeoJSON for uMap + A2 map."""
import json, math, sys, collections
import numpy as np, geopandas as gpd
from shapely.geometry import LineString, MultiLineString, box, shape
from shapely.ops import linemerge, unary_union
from pyproj import Transformer
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.patches import Rectangle, Polygon as MP
from matplotlib.colors import LinearSegmentedColormap

OSM, SURVEY, SIGNS, OUT = sys.argv[1:5]
OBJ = "--objazd" in sys.argv
INF = "--infra" in sys.argv or OBJ
import glob as _g
from matplotlib import font_manager as _fmr
for _f in _g.glob("../fonts/Inter-*.ttf"): _fmr.fontManager.addfont(_f)
plt.rcParams.update({"font.family": "Inter", "pdf.fonttype": 42})
tf = Transformer.from_crs(4326, 2180, always_xy=True); P = lambda c: tf.transform(*c)
osm = json.load(open(OSM))["features"]; D = json.load(open(SIGNS))


MM = 1 / 25.4; lw = lambda mm: mm / 25.4 * 72
import networkx as nx
from shapely.geometry import Point
from shapely.strtree import STRtree
# --- graf jak w directions.py (preferencja dróg rowerowo przyjaznych) ---
BAD = {"motorway", "motorway_link", "proposed", "construction", "steps", "platform", "bus_stop", "corridor", "elevator"}
PAVED = {"asphalt", "paved", "concrete", "paving_stones", "sett", "chipseal"}
svf = [f for f in json.load(open(SURVEY))["features"] if f["geometry"]["type"] == "LineString"]
sv_l = [LineString([P(c) for c in f["geometry"]["coordinates"]]) for f in svf]; sv_tree = STRtree(sv_l)
SV_F = {"bardzo dobra": 1.0, "dobra": 1.05, "średnia": 1.35, "trudna": 2.2}
def factor(pr, mid):
    idx = sv_tree.query(mid.buffer(15), predicate="intersects")
    if len(idx): return SV_F.get(svf[int(idx[0])]["properties"].get("Przejezdność ogólna"), 1.1)
    hw_, sf, tt = pr.get("highway"), pr.get("surface"), pr.get("tracktype")
    if sf in PAVED or (sf is None and hw_ in {"primary", "secondary", "tertiary", "residential", "living_street", "unclassified"}): return 1.0
    if hw_ == "cycleway": return 0.95
    if hw_ == "service": return 1.1
    if hw_ == "track": return 1.15 if (tt == "grade1" or sf in {"gravel", "compacted", "fine_gravel"}) else 1.35
    if hw_ in {"path", "footway", "bridleway"}: return 1.6
    return 1.2
G = nx.Graph()
for f in osm:
    pr = f["properties"]; h = pr.get("highway")
    if not h or h in BAD or f["geometry"]["type"] != "LineString": continue
    cs = [tuple(round(v, 7) for v in c) for c in f["geometry"]["coordinates"]]
    for a, b in zip(cs, cs[1:]):
        pa, pb = P(a), P(b); L = math.dist(pa, pb)
        G.add_edge(a, b, w=L, c=L * factor(pr, Point((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)), pr=pr)
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
nodes = list(G.nodes); nxy = np.array([P(n) for n in nodes])
def snap(lon, lat):
    x, y = P((lon, lat)); return nodes[int(np.argmin(((nxy - (x, y)) ** 2).sum(1)))]
PO = {p["nr"]: p for p in D["posts"]}; PL = D["places"]
TROJCA = (18.843296, 50.62077)
MAINR = {"primary", "secondary", "tertiary", "trunk"}
def _edge_of(k, frm):
    """Koniec trasy przy wsi: pierwszy węzeł drogi głównej na drodze od słupka do wsi (bez wjazdu do centrum)."""
    p = nx.shortest_path(G, snap(PO[frm]["lon"], PO[frm]["lat"]), snap(*PL[k]), weight="c")
    for n in p:
        if any(G[n][m]["pr"].get("highway") in MAINR for m in G[n]): return n
    return p[-1]
EDGE = {"Sośnica": 52}
def ep(k):
    if isinstance(k, int): return snap(PO[k]["lon"], PO[k]["lat"])
    if k == "Trójca": return snap(*TROJCA)
    if k == "Kalety Unia": return snap(18.9034997, 50.5589968)   # Fabryczna przy stadionie Unii Kalety (wg Bartosza)
    if k in EDGE: return _edge_of(k, EDGE[k])   # koniec przy drodze do wsi (Koszęcińska), bez zawracania
    return snap(*PL[k])
exec(open("trasy_kolory.py").read())
ROUTES = [
    ("1", "Rowerowa obwodnica DW 906", "Sośnica – Piasek – Bukowiec – Strzebiń – Prądy", ["Sośnica", 52, 53, 48, 29, 22, 47, 46, 8, 7, 10, 21, 25, 3, 11, 24, 1, 23, 9], KOLORY["1"][0]),
    ("2", "Kalety (stadion Unii) – Strzebiń – Łazy – Hucisko", "przez Sitki", ["Kalety Unia", 5, 34, 18, 19, 28, 6, 16, 26, 10, 49, "Hucisko"], KOLORY["2"][0]),
    ("3", "Kalety – Strzebiń – Boronów", "", ["Kalety", 4, 33, 32, 31, 30, 17, 25, 3, 11, 14, 13, "Boronów"], KOLORY["3"][0]),
    ("4", "Bukowiec – Koszęcin (kościół św. Trójcy)", "", [47, 46, 8, 7, 10, 21, 25, 3, 2, 39, 38, 37, 36, "Trójca"], KOLORY["4"][0]),
    ("5", "Babienica – Łazy – Koszęcin", "", ["Babienica", 49, 12, 42, 13, 14, 15, "Koszęcin"], KOLORY["5"][0]),
    ("6", "Psary – Bukowiec – Koszęcin (kościół św. Trójcy)", "", ["Psary", 8, 7, 10, 21, 25, 3, 2, 39, 38, 37, 36, "Trójca"], KOLORY["6"][0]),
    ("7", "Drutarnia – Dubiele – Strzebiń", "", ["Drutarnia", 40, 41, 17], KOLORY["7"][0]),
    ("8", "Kalety (stadion Unii) – Sośnica", "przejezdność do sprawdzenia", ["Kalety Unia", 5, 34, 52, "Sośnica"], KOLORY["8"][0]),
    ("9", "Sośnica – Koszęcin (kościół św. Trójcy)", "trasa dodatkowa, lasem i Leśną Rajzą", ["Sośnica", 52, 34, 33, 51, 50, 41, 40, "Trójca"], KOLORY["9"][0]),
    ("1a", "Wariant trasy 1 drogą rowerową wzdłuż DW 906", "", [7, 26, 16, 6, 20, 25], KOLORY["1"][0])]
def is_paved(pr):
    sf, h = pr.get("surface"), pr.get("highway")
    return sf in PAVED or (sf is None and h in {"primary", "secondary", "tertiary", "residential", "living_street", "unclassified"})
GRAVEL = {"gravel", "compacted", "fine_gravel", "pebblestone", "unhewn_cobblestone"}
def is_gravel(pr):
    return not is_paved(pr) and (pr.get("surface") in GRAVEL or (pr.get("surface") is None and pr.get("tracktype") == "grade1"))
n906 = [n for n in G.nodes if any(G[n][m]["pr"].get("ref") == "906" for m in G[n])]
n906xy = np.array([P(n) for n in n906])
def snap906(k):
    x, y = P((PO[k]["lon"], PO[k]["lat"])); return n906[int(np.argmin(((n906xy - (x, y)) ** 2).sum(1)))]
def on906(a, b):
    H = G.edge_subgraph([(u, v) for u, v in G.edges if G[u][v]["pr"].get("ref") == "906"])
    p = nx.shortest_path(H, a, b, weight="w"); return [frozenset(e) for e in zip(p, p[1:])]
INFRA = {"droga": on906(snap906(25), snap906(16)), "chodnik": on906(snap906(27), snap906(25))}   # wg Bartosza 10.11
SAFE = set(INFRA["droga"]) | set(INFRA["chodnik"])
RES = []
for rid, name, sub, seq, c in ROUTES:
    path = [ep(seq[0])]
    for a, b in zip(seq, seq[1:]): path += nx.shortest_path(G, ep(a), ep(b), weight="c")[1:]
    km = pav = dw = 0
    for u, v in zip(path, path[1:]):
        e_ = G[u][v]; km += e_["w"]
        if is_paved(e_["pr"]): pav += e_["w"]
        if e_["pr"].get("ref") == "906" and frozenset((u, v)) not in SAFE: dw += e_["w"]
    if seq[-1] == "Hucisko":   # koniec na skrzyżowaniu z drogą przez Hucisko (bez zawracania do punktu wsi)
        i = max(range(len(path)), key=lambda j: path[j][1]); path = path[:i + 1]
        km = sum(G[u][v]["w"] for u, v in zip(path, path[1:])); pav = sum(G[u][v]["w"] for u, v in zip(path, path[1:]) if is_paved(G[u][v]["pr"]))
    grv = sum(G[u][v]["w"] for u, v in zip(path, path[1:]) if is_gravel(G[u][v]["pr"]))
    RES.append(dict(id=rid, name=name, sub=sub, seq=seq, c=c, path=path, km=km / 1000, pav=pav / 1000, grv=grv / 1000, dw=dw / 1000, alt=rid.endswith("a")))
    print(rid, f"{km/1000:.1f} km, utwardz. {pav/km*100:.0f}%, DW906 {dw:.0f} m")
json.dump([{k: v for k, v in r.items() if k != "path"} for r in RES], open(OUT + "_trasy.json", "w"), ensure_ascii=False, indent=1)
json.dump({"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {k: v for k, v in r.items() if k != "path"},
    "geometry": {"type": "LineString", "coordinates": [list(n) for n in r["path"]]}} for r in RES]}, open(OUT + "_trasy.geojson", "w"), ensure_ascii=False)
PW, PH, PANEL, SCALE = 594, 420, 150, 33000
cx, cy = tf.transform(18.9065, 50.6185)
vw, vh = (PW - PANEL) / 1000 * SCALE, PH / 1000 * SCALE
x0, x1, y0, y1 = cx - vw / 2 - PANEL / 1000 * SCALE, cx + vw / 2, cy - vh / 2, cy + vh / 2
clip = box(x0, y0, x1, y1)
g = gpd.read_file(OSM).to_crs(2180); g["geometry"] = g.geometry.make_valid()
g = g[g.intersects(clip)].copy(); g["geometry"] = g.geometry.intersection(clip)
col = lambda k: g[k] if k in g else gpd.pd.Series([None] * len(g), index=g.index)
hw, lu, nat, ww, rw, rt = (col(k) for k in ["highway", "landuse", "natural", "waterway", "railway", "route"])
area = g.geometry.geom_type.isin(["Polygon", "MultiPolygon"]); line = g.geometry.geom_type.isin(["LineString", "MultiLineString"])
fig = plt.figure(figsize=(PW * MM, PH * MM))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off(); ax.set_aspect("equal")
ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="#f4f1e8", zorder=0))
def poly(m, fc, z):
    s = g[m & area]
    if len(s): s.plot(ax=ax, fc=fc, ec="none", zorder=z)
def lines(m, c, w, z, **k):
    s = g[m & line]
    if len(s): s.plot(ax=ax, color=c, lw=lw(w), zorder=z, capstyle="round", **k)
poly(lu.isin(["residential"]), "#e6dccd", 1.2); poly(lu.isin(["forest"]) | nat.isin(["wood"]), "#cfe0c0", 1.5)
poly(nat.isin(["water"]), "#bcd8ec", 1.7)
lines(hw.isin(["track", "path", "footway", "cycleway"]), "#b9a88f", 0.25, 3, linestyle=(0, (4, 2)))
lines(hw.isin(["residential", "unclassified", "service", "living_street"]), "#ffffff", 0.8, 4,
      path_effects=[pe.Stroke(linewidth=lw(1.15), foreground="#b8ae9f"), pe.Normal()])
lines(hw.isin(["tertiary", "secondary", "primary"]), "#f3d9a0", 1.4, 4.5)
exec(open("rails.py").read()); _RL = rail_lines(g)
if len(_RL): _RL.plot(ax=ax, color="#8a8a8a", lw=lw(0.6), zorder=5, capstyle="butt")
RCOL = {"green": "#1f9a4a", "blue": "#2a62c9", "red": "#d6342c"}
for _, r in g[rt.isin(["bicycle"])].iterrows():
    gpd.GeoSeries([r.geometry]).plot(ax=ax, color=RCOL.get(r.get("colour"), "#7a5aa6"), lw=lw(2.2), alpha=0.22, zorder=6)
# DW 906 podkreślona
lines(rt.isin(["__none__"]), "#000", 0, 0)
dwm = hw.isin(["secondary"]) & (col("ref") == "906")
from shapely.ops import linemerge, substring
L906 = linemerge([LineString([P(u), P(v)]) for u, v in G.edges if G[u][v]["pr"].get("ref") == "906"])
L906 = max(L906.geoms, key=lambda g_: g_.length) if L906.geom_type == "MultiLineString" else L906
def piece(a, b):
    pa, pb = [L906.project(Point(P((PO[k]["lon"], PO[k]["lat"])))) for k in (a, b)]
    return substring(L906, min(pa, pb), max(pa, pb))
for (a, b), col, ls in (((25, 16), "#1f7a3f", "-"), ((27, 25), "#4b5563", (0, (2, 1.2)))):
    gpd.GeoSeries([piece(a, b)]).plot(ax=ax, color=col, lw=lw(0.8), zorder=7.5, linestyle=ls, capstyle="butt")
# trasy – wspólne odcinki rysowane cienkimi, stykającymi się paskami na osi drogi
m2u = lambda mm_: mm_ / 1000 * SCALE
USE = collections.defaultdict(set)
for r in RES:
    for u, v in zip(r["path"], r["path"][1:]): USE[frozenset((u, v))].add(r["id"])
W1, WS = 1.5, 0.85          # mm: trasa pojedyncza / pasek na wspólnym odcinku
drawn = set()
for r in RES:
    pth = r["path"]; runs = []; cur = [pth[0]]; cs = None
    for u, v in zip(pth, pth[1:]):
        s = frozenset(USE[frozenset((u, v))])
        if cs is not None and s != cs: runs.append((cs, cur)); cur = [u]
        cur.append(v); cs = s
    runs.append((cs, cur)); r["runs"] = runs
    for s, nodes_ in runs:
        if len(nodes_) < 2: continue
        a, b = nodes_[0], nodes_[-1]
        if (a, b) > (b, a): nodes_ = nodes_[::-1]          # kierunek kanoniczny – ten sam dla wszystkich tras
        ln = LineString([P(n) for n in nodes_])
        k = len(s); ids = sorted(s); i = ids.index(r["id"])
        key = (frozenset(s), nodes_[0], nodes_[-1], len(nodes_))
        if key not in drawn:
            drawn.add(key)
            tot = W1 if k == 1 else WS * k
            if not INF: gpd.GeoSeries([ln]).plot(ax=ax, color="white", lw=lw(tot + 0.6), zorder=8, capstyle="round", joinstyle="round")
        if k == 1:
            g2, w_ = ln, W1
        else:
            o = (i - (k - 1) / 2) * m2u(WS)
            try:
                g2 = ln.offset_curve(o, join_style=1) if abs(o) > 0 else ln
                if g2.is_empty: g2 = ln
            except Exception: g2 = ln
            w_ = WS
        gpd.GeoSeries([g2]).plot(ax=ax, color=r["c"], lw=lw(w_ * (0.75 if INF else 1)), zorder=9, capstyle="butt", joinstyle="round",
                                 linestyle=(0, (2.2, 1.1)) if r["alt"] else "-", alpha=0.38 if INF else 1)
for r in RES:
    full = LineString([P(n) for n in r["path"]])
    # numer trasy na odcinkach, gdzie trasa biegnie sama (jeśli są)
    solo = [LineString([P(n) for n in ns]) for s, ns in r["runs"] if len(s) == 1 and len(ns) > 1]
    cand = solo or [full]
    PXY = np.array([tf.transform(p["lon"], p["lat"]) for p in D["posts"]])
    pts = [g_.interpolate(t, normalized=True) for g_ in cand for t in np.linspace(0.05, 0.95, 40)]
    dist = lambda m: np.min(np.hypot(PXY[:, 0] - m.x, PXY[:, 1] - m.y))
    E0, E1 = full.coords[0], full.coords[-1]
    endd = lambda m: min(math.hypot(m.x - E0[0], m.y - E0[1]), math.hypot(m.x - E1[0], m.y - E1[1]))
    pts = [m for m in pts if endd(m) > 1200] or pts
    dist0 = dist
    dist = lambda m: min(dist0(m), 1500)
    pts.sort(key=lambda m: -dist(m))          # najdalej od słupków i od końców trasy
    spots = [pts[0]]
    for m in pts[1:]:
        if dist(m) < 450: break
        if min(math.hypot(m.x - q.x, m.y - q.y) for q in spots) > 3500: spots.append(m)
        if len(spots) == 2: break
    for m in ([] if (r["alt"] or INF) else spots):
        ax.text(m.x, m.y, r["id"], ha="center", va="center", fontsize=10, weight="bold", color=KOLORY[r["id"]][1], zorder=21,
                bbox=dict(boxstyle="round,pad=0.35", fc=r["c"], ec="white", lw=1.5))
on = {k for r in RES for k in r["seq"] if isinstance(k, int)}
for p in D["posts"]:
    x, y = tf.transform(p["lon"], p["lat"]); hit = p["nr"] in on
    ax.text(x, y, str(p["nr"]), ha="center", va="center", fontsize=8.5 if hit else 7, weight="bold", color="white", zorder=22,
            bbox=dict(boxstyle="circle,pad=0.3", fc="#00838F" if hit else "#8a9399", ec="white", lw=1.2))
PLACE_T = []
for name, (lon, lat) in D["places"].items():
    x, y = tf.transform(lon, lat)
    if not (x0 + PANEL / 1000 * SCALE + 150 < x < x1 - 150 and y0 + 150 < y < y1 - 350): continue
    big = name in ["Strzebiń", "Koszęcin", "Kalety", "Boronów", "Psary", "Babienica", "Piasek", "Hucisko"]
    PLACE_T.append((2 if big else 1, ax.text(x, y + 260, name.upper() if big else name, ha="center", fontsize=12 if big else 8, weight="bold" if big else "medium",
            color="#3a3630", zorder=12, path_effects=[pe.withStroke(linewidth=3, foreground="#f4f1e8")])))
x, y = P(TROJCA); ax.text(x, y - 330, "kościół\nśw. Trójcy", ha="center", va="top", fontsize=8, color="#5a3a1a", zorder=12,
                          path_effects=[pe.withStroke(linewidth=3, foreground="#f4f1e8")])
ax.plot([x], [y], marker="P", ms=9, color="#81552F", mec="white", zorder=13)
if OBJ:
    exec(open("objazd_layer.py").read()); raise SystemExit
if INF:
    exec(open("infra_layer.py").read()); raise SystemExit
# panel
pan = fig.add_axes([0, 0, PANEL / PW, 1]); pan.set_axis_off(); pan.set_xlim(0, PANEL); pan.set_ylim(0, PH)
pan.add_patch(Rectangle((0, 0), PANEL, PH, color="#f7f4ec")); pan.plot([PANEL - 0.6, PANEL - 0.6], [0, PH], color="#1d3b30", lw=lw(0.8))
T = lambda x, y, s, **k: pan.text(x, y, s, color=k.pop("color", "#1d2a23"), **k)
M = 12
T(M, 398, "SOŁECTWO STRZEBIŃ · HUB ROWEROWY", fontsize=12, weight="bold", color="#8a5300")
T(M, 390, "Proponowane\ntrasy rowerowe", fontsize=27, weight="bold", va="top", linespacing=1.05)
T(M, 356, "Trasy po drogach oznakowanych drogowskazami. Kółka z numerami na mapie\nto słupki (węzły) – wystarczy jechać od numeru do numeru.", fontsize=9.2,
  va="top", color="#4b5d53", linespacing=1.45)
y = 338
import textwrap
R1, R1a = RES[0], next((r for r in RES if r["alt"]), None)
def seg_km(path, a, b):
    i, j = path.index(ep(a)), path.index(ep(b)); i, j = min(i, j), max(i, j)
    return sum(G[u][v]["w"] for u, v in zip(path[i:j], path[i + 1:j + 1])) / 1000
for r in RES:
    if r["alt"]: continue
    pan.add_patch(Rectangle((M, y - 7.5), 9, 9, color=r["c"])); T(M + 4.5, y - 3, r["id"], fontsize=12, weight="bold", ha="center", va="center", color=KOLORY[r["id"]][1])
    T(M + 13, y - 3, r["name"], fontsize=12.5, weight="bold", va="center")
    y -= 9.5
    chk = r["sub"].startswith("przejezdność")
    if r["sub"]: T(M + 13, y, "przejezdność do sprawdzenia w terenie" if chk else r["sub"], fontsize=9, va="center", color="#8a5300"); y -= 6.3
    pa, gr = r['pav'] / r['km'] * 100, r['grv'] / r['km'] * 100
    stats = (f"{r['km']:.1f}".replace(".", ",") + f" km · asfalt/kostka {pa:.0f}% · szuter {gr:.0f}% · gruntowe {100 - pa - gr:.0f}% · po DW 906* {r['dw']*1000:.0f} m")
    T(M + 13, y, stats, fontsize=8.6, va="center", color="#2c3a32")
    y -= 6.2

    if r is R1 and R1a:
        y -= 1.5
        pan.plot([M + 13, M + 21], [y, y], color=R1a["c"], lw=lw(0.85), linestyle=(0, (2.2, 1.1)))
        T(M + 24, y, "wariant 1a: przez Strzebiń drogą rowerową wzdłuż DW 906", fontsize=8.6, va="center", color="#8a5300"); y -= 5.6
        k1, k2 = R1a["km"], seg_km(R1["path"], 7, 25)
        cmp_ = "tyle samo co ulicą 1 Maja" if abs(k1 - k2) < 0.15 else f"zamiast {k2:.1f} km ulicą 1 Maja"
        T(M + 24, y, f"{k1:.1f} km, {cmp_}".replace(".", ","), fontsize=8.6, va="center", color="#2c3a32"); y -= 5.6
    y -= 2
y -= 1
T(M, y - 0, "Nawierzchnia wg OpenStreetMap: asfalt/kostka – asfalt, beton, kostka (oraz ulice bez opisu);\n   szuter – drogi z kruszywa i dobre drogi leśne; gruntowe – pozostałe drogi polne i leśne.", fontsize=8.2, va="top", color="#2c3a32", linespacing=1.45)
y -= 14
T(M, y, "* „po DW 906” – tylko odcinki jazdy jezdnią wojewódzkiej. Nie obejmuje istniejącej\n   drogi rowerowej (słupki 25–16) ani chodnika (27–25) wzdłuż DW 906.", fontsize=8.6, va="top", color="#8a5300", linespacing=1.45)
y -= 18
pan.plot([M, M + 10], [y, y], color="#f3d9a0", lw=lw(1.4)); T(M + 14, y, "drogi wojewódzkie i powiatowe (m.in. DW 906)", fontsize=9, va="center"); y -= 8
pan.plot([M, M + 10], [y, y], color="#f3d9a0", lw=lw(1.4)); pan.plot([M, M + 10], [y, y], color="#1f7a3f", lw=lw(0.7))
T(M + 14, y, "istniejąca droga rowerowa wzdłuż DW 906", fontsize=9, va="center"); y -= 8
pan.plot([M, M + 10], [y, y], color="#f3d9a0", lw=lw(1.4)); pan.plot([M, M + 10], [y, y], color="#6b7280", lw=lw(0.7), linestyle=(0, (2, 1.2)))
T(M + 14, y, "bezpieczny chodnik wzdłuż DW 906", fontsize=9, va="center"); y -= 8
pan.text(M + 5, y, "7", ha="center", va="center", fontsize=8, weight="bold", color="white", bbox=dict(boxstyle="circle,pad=0.3", fc="#00838F", ec="white", lw=1))
T(M + 14, y, "słupek / węzeł na trasie", fontsize=9, va="center"); y -= 8
pan.text(M + 5, y, "7", ha="center", va="center", fontsize=7, weight="bold", color="white", bbox=dict(boxstyle="circle,pad=0.3", fc="#8a9399", ec="white", lw=1))
T(M + 14, y, "pozostałe słupki", fontsize=9, va="center"); y -= 10
T(M, y, "Trasy przebiegające wspólnym odcinkiem narysowano obok siebie.\nPrzebieg do potwierdzenia w terenie (mapa stanu dróg).", fontsize=8, va="top", color="#4b5d53", linespacing=1.45)
T(M, 6, "Dane mapy © autorzy OpenStreetMap (ODbL)", fontsize=7.5, color="#4b5d53")
exec(open("labels.py").read()); declutter(fig, ax, PLACE_T)
fig.savefig(OUT + "_trasy.pdf"); fig.savefig(OUT + "_trasy_podglad.png", dpi=60)
print("ok")
