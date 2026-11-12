"""Signpost plan: A2 planning map + A4 catalog with plate mockups."""
import json, math, sys
import numpy as np, geopandas as gpd
from shapely.geometry import box
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import patheffects as pe
from matplotlib.patches import Rectangle, FancyBboxPatch, Polygon as MP, Circle
from matplotlib.backends.backend_pdf import PdfPages

OSM, SURVEY, SIGNS, OUT, MOCK1, MOCK2 = sys.argv[1:7]
import glob as _g
from matplotlib import font_manager as _fmr
for _f in _g.glob("../fonts/Inter-*.ttf"): _fmr.fontManager.addfont(_f)
plt.rcParams.update({"font.family": "Inter", "pdf.fonttype": 42})
D = json.load(open(SIGNS)); posts = D["posts"]
GROUP = "--single" not in sys.argv
from pyproj import Transformer as _T
_tf = _T.from_crs(4326, 2180, always_xy=True)
def _node_at(path, m=150):
    if not path: return None
    acc, prev = 0, _tf.transform(*path[0])
    for n in path[1:]:
        cur = _tf.transform(*n); acc += math.dist(prev, cur); prev = cur
        if acc >= m: return tuple(n)
    return tuple(path[-1])
def _side(pl):
    d_ = pl.get("deg")
    return "R" if (d_ is not None and (math.sin(math.radians(d_)) > 0.34 or (abs(math.sin(math.radians(d_))) <= 0.34 and math.cos(math.radians(d_)) > 0))) else "L"
def _close(a, b, tol=35):
    if a is None or b is None: return False
    return abs((a - b + 180) % 360 - 180) <= tol
def cluster_dirs(plates_):
    """Same arrow side and initial bearing within 35 deg -> same direction (Leśno Rajza always alone)."""
    cl = []
    for pl in plates_:
        if not pl.get("lr") and pl.get("km") is not None:
            for c in cl:
                h = c[0]
                if not h.get("lr") and h.get("cat", "blue") == pl.get("cat", "blue") and _side(h) == _side(pl) and _close(h.get("deg"), pl.get("deg")):
                    c.append(pl); break
            else: cl.append([pl])
        else: cl.append([pl])
    out = []
    for c in cl:
        s_ = sorted(c, key=lambda q: q["km"] or 0)
        out += [s_[i:i + 2] for i in range(0, len(s_), 2)]
    return out
def group_plates(p):
    if not GROUP: return [[pl] for pl in p["plates"]]
    return cluster_dirs(p["plates"])
for p in posts: p["groups"] = group_plates(p)
MM = 1 / 25.4; lw = lambda mm: mm / 25.4 * 72
BLUE, NAVY = "#1f5fb4", "#16325c"
WHO = {"nadl_K": ("#2f6b3a", "uzgodnić z Nadleśnictwem Koszęcin"),
       "gmina": ("#e07b16", "uzgodnić z Gminą Koszęcin"), "—": (BLUE, "bez dodatkowych uzgodnień")}
DIR8 = ["płn.", "płn.-wsch.", "wsch.", "płd.-wsch.", "płd.", "płd.-zach.", "zach.", "płn.-zach."]
kmfmt = lambda v: f"{v:.1f} km".replace(".", ",")

# ======================= MAP (A2 landscape) =======================
ZOOM = "--zoom" in sys.argv
PW, PH, PANEL, SCALE = 594, 420, 150, (15000 if ZOOM else 33000)
KZ = SCALE / 33000   # metre offsets below were tuned for 1:33 000
g = gpd.read_file(OSM).to_crs(2180)
sv = gpd.read_file(SURVEY).to_crs(2180)
pts = gpd.GeoDataFrame(posts, geometry=gpd.points_from_xy([p["lon"] for p in posts], [p["lat"] for p in posts]), crs=4326).to_crs(2180)
cx, cy = gpd.GeoSeries.from_xy([18.9105 if ZOOM else 18.9065], [50.6155 if ZOOM else 50.6185], crs=4326).to_crs(2180).iloc[0].coords[0]
vw, vh = (PW - PANEL) / 1000 * SCALE, PH / 1000 * SCALE
x0, x1, y0, y1 = cx - vw / 2 - PANEL / 1000 * SCALE, cx + vw / 2, cy - vh / 2, cy + vh / 2
vx0 = cx - vw / 2
clip = box(x0, y0, x1, y1)
g["geometry"] = g.geometry.make_valid(); g = g[g.intersects(clip)].copy(); g["geometry"] = g.geometry.intersection(clip)
col = lambda k: g[k] if k in g else gpd.pd.Series([None] * len(g), index=g.index)
hw, lu, nat, ww, rw, rt = (col(k) for k in ["highway", "landuse", "natural", "waterway", "railway", "route"])
area = g.geometry.geom_type.isin(["Polygon", "MultiPolygon"]); line = g.geometry.geom_type.isin(["LineString", "MultiLineString"])

fig = plt.figure(figsize=(PW * MM, PH * MM))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_axis_off(); ax.set_aspect("equal")
ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="#f4f1e8", zorder=0))
def poly(m, fc, z, ec="none", w=0):
    s = g[m & area]
    if len(s): s.plot(ax=ax, fc=fc, ec=ec, lw=lw(w), zorder=z)
def lines(m, c, w, z, **k):
    s = g[m & line]
    if len(s): s.plot(ax=ax, color=c, lw=lw(w), zorder=z, capstyle="round", joinstyle="round", **k)
poly(lu.isin(["farmland"]), "#efe9d6", 1); poly(lu.isin(["meadow"]), "#e3ecc9", 1.1)
poly(lu.isin(["residential"]), "#e6dccd", 1.2)
poly(lu.isin(["forest"]) | nat.isin(["wood"]), "#b7d3a0", 1.5)
poly(nat.isin(["water"]), "#a8cde6", 1.7, "#7fb2d8", 0.2)
lines(ww.notna(), "#7fb2d8", 0.5, 2)
lines(hw.isin(["track", "path", "footway", "cycleway"]) , "#a08360", 0.3, 3, linestyle=(0, (4, 2)))
RW = 1.7 if ZOOM else 1.0
lines(hw.isin(["residential", "unclassified", "service", "living_street"]), "#ffffff", 0.9 * RW, 4,
      path_effects=[pe.Stroke(linewidth=lw(1.3 * RW), foreground="#a89d8c"), pe.Normal()])
lines(hw.isin(["tertiary", "secondary", "primary", "trunk"]), "#f6c766", 1.6, 4.5,
      path_effects=[pe.Stroke(linewidth=lw(2.2), foreground="#c4983f"), pe.Normal()])
lines(hw.isin(["motorway"]), "#e8846b", 2, 4.6)
exec(open("rails.py").read()); _RL = rail_lines(g)
if len(_RL):
    _RL.plot(ax=ax, color="#6b6b6b", lw=lw(0.75), zorder=5, capstyle="butt")
    _RL.plot(ax=ax, color="white", lw=lw(0.38), zorder=5.1, capstyle="butt", linestyle=(0, (6, 6)))

# bike routes
RCOL = {"green": "#1f9a4a", "blue": "#2a62c9", "red": "#d6342c"}
routes = g[rt.isin(["bicycle"])]
leg_routes = []
for _, r in routes.iterrows():
    c = RCOL.get(r.get("colour"), "#7a5aa6")
    gpd.GeoSeries([r.geometry]).plot(ax=ax, color=c, lw=lw(2.4), alpha=0.35, zorder=6, capstyle="round")
    gpd.GeoSeries([r.geometry]).plot(ax=ax, color=c, lw=lw(0.7), zorder=6.1, linestyle=(0, (6, 3)))
    nm = r["name"] + (f" ({r['ref']})" if isinstance(r.get("ref"), str) else "")
    if not any(n == nm for n, _ in leg_routes): leg_routes.append((nm, c))

# surveyed segments
PCOL = {"bardzo dobra": "#1e8c45", "dobra": "#7cb342", "średnia": "#f0a12b", "trudna": "#d43d33"}
svl = sv[sv.geometry.geom_type == "LineString"]
SHOW_P = ()   # 6.11: odcinki do poprawy są na osobnej mapie
for _, r in svl.iterrows():
    if r.get("Przejezdność ogólna") not in SHOW_P: continue
    gpd.GeoSeries([r.geometry]).plot(ax=ax, color=PCOL.get(r.get("Przejezdność ogólna"), "#888"), lw=lw(2.0), zorder=7,
                                     capstyle="round", path_effects=[pe.Stroke(linewidth=lw(2.4), foreground="white"), pe.Normal()])

# places
PLACE_T = []
for name, (lon, lat) in D["places"].items():
    if name == "Zagroda u Czesi": continue
    x, y = gpd.GeoSeries.from_xy([lon], [lat], crs=4326).to_crs(2180).iloc[0].coords[0]
    if not (vx0 + 150 * KZ < x < x1 - 150 * KZ and y0 + 150 * KZ < y < y1 - 350 * KZ): continue
    big = name in ["Strzebiń", "Koszęcin", "Kalety", "Boronów", "Psary", "Babienica", "Piasek", "Hucisko"]
    PLACE_T.append((2 if big else 1, ax.text(x, y + 260 * KZ, name.upper() if big else name, ha="center", va="center", fontsize=(16 if ZOOM else 13) if big else (11 if ZOOM else 9),
            weight="bold" if big else "medium", color="#3a3630", zorder=9,
            path_effects=[pe.withStroke(linewidth=3.5, foreground="#f4f1e8")])))
PCAT = {"brown": "#81552F", "red": "#902B38", "gray": "#505C66", "orange": "#B96516", "green": "#237647"}
import subprocess, os
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
_WR = os.path.join(os.path.dirname(os.path.abspath(OUT)), "_klucz.png")
open(_WR + ".svg", "w").write('<svg xmlns="http://www.w3.org/2000/svg" width="240" height="240" viewBox="-3 -3 30 30">'
    '<circle cx="12" cy="12" r="14" fill="white" stroke="#505C66" stroke-width="1.6"/>'
    '<g transform="translate(3.2 3.2) scale(.733)" fill="none" stroke="#505C66" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M7 10h3v-3l-3.5 -3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1 -3 3l-6 -6a6 6 0 0 1 -8 -8l3.5 3.5"/></g></svg>')
subprocess.run(["rsvg-convert", _WR + ".svg", "-o", _WR], check=True); os.remove(_WR + ".svg")
_wimg = plt.imread(_WR); os.remove(_WR)
from svgpath2mpl import parse_path as _pp
from matplotlib.patches import Circle as _Circ, PathPatch as _PP
from matplotlib.transforms import Affine2D as _Aff
_WPATH = _pp("M7 10h3v-3l-3.5 -3.5a6 6 0 0 1 8 8l6 6a2 2 0 0 1 -3 3l-6 -6a6 6 0 0 1 -8 -8l3.5 3.5")
def wrench(a_, x, y, d_mm, z=21):
    """Wektorowy klucz stacji napraw (białe koło, grafitowa obwódka i piktogram)."""
    bb = a_.get_position(); w_mm = bb.width * PW
    upm = (a_.get_xlim()[1] - a_.get_xlim()[0]) / w_mm          # jednostki osi na 1 mm papieru
    d = d_mm * upm
    a_.add_patch(_Circ((x, y), d / 2, facecolor="white", edgecolor="#505C66", lw=lw(d_mm * 0.065), zorder=z))
    sc = d * 0.62 / 24
    a_.add_patch(_PP(_Aff().translate(-12, -12).scale(sc, -sc).translate(x, y).transform_path(_WPATH), facecolor="none",
                     edgecolor="#505C66", lw=lw(d_mm * 0.62 / 24 * 2.3), capstyle="round", joinstyle="round", zorder=z + 0.5))
post_xy = [(g_.x, g_.y) for g_ in pts.geometry]
R_POST = (5.0 if ZOOM else 4.2) * SCALE / 1000            # post circle radius on paper ≈ 4.2 mm
STATIONS = []
POI_T = []; WRENCH = []
for poi in sorted(D.get("pois", []), key=lambda q: q.get("icon") != "service"):   # najpierw klucze, potem gwiazdki
    nm_, cz = poi["name"], [poi["lon"], poi["lat"]]
    x, y = gpd.GeoSeries.from_xy([cz[0]], [cz[1]], crs=4326).to_crs(2180).iloc[0].coords[0]
    if poi.get("icon") == "wc": continue   # WC przy stacji napraw – na mapie pokazuje go klucz
    if poi.get("icon") == "service":
        near = min(post_xy, key=lambda q: math.dist(q, (x, y)))
        free = lambda px, py: all(math.dist((px, py), q) > 2.2 * R_POST for q in post_xy)
        if not free(x, y):   # pokrywa się ze słupkiem – klucz obok kółka, w pierwszym wolnym miejscu
            a0 = math.degrees(math.atan2(y - near[1], x - near[0])) if math.dist(near, (x, y)) > 1 else 0
            for a_ in sorted(range(0, 360, 30), key=lambda t: abs((t - a0 + 180) % 360 - 180)) + [225]:   # najpierw w stronę faktycznego miejsca
                px, py = near[0] + 2.35 * R_POST * math.cos(math.radians(a_)), near[1] + 2.35 * R_POST * math.sin(math.radians(a_))
                if free(px, py) or a_ == 225: x, y = px, py; break
        wrench(ax, x, y, 7.5 if ZOOM else 6.5); _AB = (AnnotationBbox(OffsetImage(_wimg, zoom=0.001), (x, y),
                                     frameon=False, zorder=21)); STATIONS.append(nm_); WRENCH.append((x, y)); continue
    obst = post_xy + WRENCH
    if not all(math.dist((x, y), q) > 1.5 * R_POST for q in obst):   # gwiazdka pod słupkiem lub kluczem – tuż obok, w wolnym miejscu
        near = min(obst, key=lambda q: math.dist(q, (x, y)))
        a0 = math.degrees(math.atan2(y - near[1], x - near[0])) if math.dist(near, (x, y)) > 1 else 0
        for a_ in sorted(range(0, 360, 30), key=lambda t: abs((t - a0 + 180) % 360 - 180)):
            px, py = near[0] + 1.75 * R_POST * math.cos(math.radians(a_)), near[1] + 1.75 * R_POST * math.sin(math.radians(a_))
            if all(math.dist((px, py), q) > 1.5 * R_POST for q in obst): x, y = px, py; break
    ax.text(x, y, "★", fontsize=16, color=PCAT.get(poi["cat"], "#b5179e"), ha="center", va="center", zorder=22, family="DejaVu Sans",
            path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    POI_T.append((ax.text(x, y, nm_, fontsize=10 if ZOOM else 8.5, weight="bold", color=PCAT.get(poi["cat"], "#b5179e"), zorder=25,
                          path_effects=[pe.withStroke(linewidth=3, foreground="white")]), x, y))

# posts
POLEC = {"istniejący": ("#2563a8", "istniejący słupek – podpinamy tabliczki"), "nowy": ("#d9480f", "nowy słupek – do postawienia"),
         "opcjonalny": ("#7b4fb3", "opcjonalny – do ustalenia (w lasach: z Nadleśnictwem Koszęcin)"), "do sprawdzenia": ("#8a8f94", "słupek do sprawdzenia")}
RING = {"gmina": "white", "nadl_K": "#1f5c2c", "—": "white"}
for p, geom in zip(posts, pts.geometry):
    c = POLEC[p.get("pole", "do sprawdzenia")][0]
    ax.text(geom.x, geom.y, str(p["nr"]), ha="center", va="center", fontsize=12 if ZOOM else 10, weight="bold", color="white", zorder=20,
            bbox=dict(boxstyle="circle,pad=0.35", fc=c, ec=RING[p["who"]], lw=1.8 if p["who"] == "gmina" else 3.2))

# panel
pan = fig.add_axes([0, 0, PANEL / PW, 1]); pan.set_axis_off(); pan.set_xlim(0, PANEL); pan.set_ylim(0, PH)
pan.add_patch(Rectangle((0, 0), PANEL, PH, color="#f7f4ec")); pan.plot([PANEL - 0.6, PANEL - 0.6], [0, PH], color="#1d3b30", lw=lw(0.8))
fade = fig.add_axes([PANEL / PW, 0, 25 / PW, 1]); fade.set_axis_off()
from matplotlib.colors import LinearSegmentedColormap
fade.imshow(np.linspace(1, 0, 256)[None, :] ** 1.6, aspect="auto", extent=(0, 1, 0, 1),
            cmap=LinearSegmentedColormap.from_list("p", [(0.957, 0.945, 0.91, 0), (0.957, 0.945, 0.91, 1)]))
T = lambda x, y, s, **k: pan.text(x, y, s, color=k.pop("color", "#1d2a23"), **k)
M = 12
T(M, 398, "SOŁECTWO STRZEBIŃ" + (" · POWIĘKSZENIE" if ZOOM else ""), fontsize=13, weight="bold", color="#8a5300")
T(M, 390, "Drogowskazy\nrowerowe", fontsize=30, weight="bold", va="top", linespacing=1.05)
T(M, 352, "Projekt rozmieszczenia znaków kierunkowych\nłączących trasy wokół Strzebinia", fontsize=10.5,
  va="top", color="#4b5d53", linespacing=1.4)
n_pl = sum(len(p["groups"]) for p in posts)
MAN0 = next((a_.split("=", 1)[1] for a_ in sys.argv if a_.startswith("--manifest=")), None)
if MAN0: n_pl = sum(len(v) for v in json.load(open(MAN0)).values())
cnt = {k: sum(p["who"] == k for p in posts) for k in WHO}
_opt = [p for p in posts if p.get("pole") == "opcjonalny"]
_opt_pl = sum(len(v) for k, v in json.load(open(MAN0)).items() if int(k) in {p["nr"] for p in _opt}) if MAN0 else 0
for i, (v, u) in enumerate([(len(posts) - len(_opt), "słupków"), (n_pl - _opt_pl, "tabliczek"), (sum(p.get("pole") == "istniejący" for p in posts), "istniejących")]):
    T(M + i * 44, 313, str(v), fontsize=26, weight="bold", color="#8a5300"); T(M + i * 44, 305, u, fontsize=9, color="#4b5d53")
if _opt: T(M, 297, f"+ {len(_opt)} słupków opcjonalnych ({_opt_pl} tabliczek)", fontsize=8.5, color="#6a3fa0")
y = 284
T(M, y, "SŁUPKI", fontsize=9, weight="bold", color="#4b5d53"); y -= 10
pcnt = {k: sum(p.get("pole") == k for p in posts) for k in POLEC}
for k, (c, lab) in POLEC.items():
    if not pcnt[k]: continue
    pan.text(M + 4, y, "1", ha="center", va="center", fontsize=8, weight="bold", color="white",
             bbox=dict(boxstyle="circle,pad=0.3", fc=c, ec="white", lw=1)); T(M + 12, y, f"{lab} ({pcnt[k]})", fontsize=10, va="center"); y -= 9
y -= 2; T(M, y, "obwódka = kto uzgadnia:", fontsize=8.5, color="#4b5d53", va="center"); y -= 9
for k, lab in (("gmina", "Gmina Koszęcin"), ("nadl_K", "Nadleśnictwo Koszęcin")):
    if not cnt.get(k): continue
    pan.text(M + 4, y, "1", ha="center", va="center", fontsize=8, weight="bold", color="white",
             bbox=dict(boxstyle="circle,pad=0.3", fc="#8a8f94", ec=RING[k], lw=1 if k == "gmina" else 2.6)); T(M + 12, y, f"{lab} ({cnt[k]})", fontsize=10, va="center"); y -= 9
if SHOW_P: y -= 5; T(M, y, "ODCINKI DO POPRAWY (pomiary 2026)", fontsize=9, weight="bold", color="#4b5d53"); y -= 9
for k, c in PCOL.items():
    if k not in SHOW_P: continue
    pan.plot([M, M + 9], [y, y], color=c, lw=lw(1.8), solid_capstyle="round"); T(M + 13, y, "przejezdność " + k, fontsize=10, va="center"); y -= 8
y -= 5; T(M, y, "SZLAKI ROWEROWE (OSM)", fontsize=9, weight="bold", color="#4b5d53"); y -= 9
for nm, c in leg_routes:
    pan.plot([M, M + 9], [y, y], color=c, lw=lw(2.4), alpha=0.5, solid_capstyle="round")
    pan.plot([M, M + 9], [y, y], color=c, lw=lw(0.7), linestyle=(0, (3, 1.5)))
    T(M + 13, y, nm, fontsize=9.5, va="center"); y -= 8
y -= 5; T(M, y, "INNE", fontsize=9, weight="bold", color="#4b5d53"); y -= 9
pan.text(M + 4, y, "★", ha="center", va="center", fontsize=11, color="#e05ad0", family="DejaVu Sans")
T(M + 13, y, "cele lokalne: brąz – historia i kultura,\nczerwień – gastronomia (przykładowa)" + ("" if ZOOM else ";\nnazwy w ciasnym centrum Strzebinia – na mapie\npowiększonej"), fontsize=9, va="center"); y -= (14 if ZOOM else 22)
wrench(pan, M + 4, y, 6)
T(M + 13, y, "stacja napraw rowerów (fundusz sołecki 2027; przy boisku także WC)", fontsize=9, va="center"); y -= 14
T(M, y, "Odległości na tabliczkach (katalog) liczone po drogach\nz OpenStreetMap do centrum miejscowości.\n"
        "Zwrot tabliczek (← / →) przyjęto wstępnie: cel na wschód = →,\nna zachód = ←. Do weryfikacji w terenie.",
  fontsize=8.5, va="top", color="#4b5d53", linespacing=1.45)
T(M, 10, "Status: PROPOZYCJA · dane mapy © autorzy OpenStreetMap (ODbL)", fontsize=7.5, color="#4b5d53")
# scale + north
SEG = 250 if ZOOM else 500
sbx, sby = x1 - 3600 * KZ, y0 + 700 * KZ
for i in range(4):
    ax.add_patch(Rectangle((sbx + i * SEG, sby), SEG, 90 * KZ, fc="#1d3b30" if i % 2 == 0 else "white", ec="#1d3b30", lw=1, zorder=30))
for v in ([0, 500, 1000] if ZOOM else [0, 1000, 2000]):
    ax.text(sbx + v, sby + 200 * KZ, (f"{v} m" if ZOOM and v < 1000 else f"{v // 1000} km"), ha="center", fontsize=9, zorder=30, color="#1d3b30",
            path_effects=[pe.withStroke(linewidth=3, foreground="#f4f1e8")])
ax.text(sbx + 2 * SEG, sby - 220 * KZ, f"skala 1 : {SCALE:,} przy wydruku A2".replace(",", " "), ha="center", fontsize=8, color="#1d3b30", zorder=30,
        path_effects=[pe.withStroke(linewidth=3, foreground="#f4f1e8")])
nx_, ny_ = x1 - 700 * KZ, y1 - 1300 * KZ
ax.add_patch(MP([(nx_, ny_ + 500 * KZ), (nx_ - 170 * KZ, ny_ - 80 * KZ), (nx_, ny_ + 40 * KZ)], fc="#1d3b30", zorder=30))
ax.add_patch(MP([(nx_, ny_ + 500 * KZ), (nx_ + 170 * KZ, ny_ - 80 * KZ), (nx_, ny_ + 40 * KZ)], fc="white", ec="#1d3b30", lw=1, zorder=30))
ax.text(nx_, ny_ + 700 * KZ, "N", ha="center", fontsize=16, weight="bold", color="#1d3b30", zorder=30)
if ZOOM:   # street names for the village
    named = g[line & hw.isin(["residential", "unclassified", "living_street", "tertiary", "secondary", "service"]) & g["name"].notna()]
    vb = box(vx0 + 300, y0 + 300, x1 - 300, y1 - 300); done = []
    for nm, grp in named.groupby("name"):
        geom = grp.geometry.union_all().intersection(vb)
        parts = list(getattr(geom, "geoms", [geom])); parts = [p_ for p_ in parts if p_.geom_type == "LineString" and p_.length > 180]
        for p_ in sorted(parts, key=lambda q: -q.length)[:2]:
            m = p_.interpolate(0.5, normalized=True); a_ = p_.interpolate(max(0, p_.project(m) - 40)); b_ = p_.interpolate(min(p_.length, p_.project(m) + 40))
            if any(math.dist((m.x, m.y), d_) < 350 for d_ in done) or any(math.dist((m.x, m.y), q) < 2.2 * R_POST for q in post_xy): continue
            ang = math.degrees(math.atan2(b_.y - a_.y, b_.x - a_.x)); ang = ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
            ax.text(m.x, m.y, nm, fontsize=6.3, color="#6b6153", rotation=ang, rotation_mode="anchor", ha="center", va="center", zorder=8,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")]); done.append((m.x, m.y))
if ZOOM:   # powiększenia gęstych miejsc (Łazy, most w Strzebiniu)
    def inset(lon, lat, half_w, rect, title, tag):
        cxi, cyi = gpd.GeoSeries.from_xy([lon], [lat], crs=4326).to_crs(2180).iloc[0].coords[0]
        wmm, hmm = rect[2], rect[3]; half_h = half_w * hmm / wmm
        bx = (cxi - half_w, cyi - half_h, cxi + half_w, cyi + half_h)
        ax.add_patch(Rectangle((bx[0], bx[1]), 2 * half_w, 2 * half_h, fill=False, ec="#1d3b30", lw=1.3, ls=(0, (3, 2)), zorder=24))
        ax.text(bx[0], bx[3] + 40, tag, fontsize=10, weight="bold", color="#1d3b30", zorder=24, va="bottom",
                path_effects=[pe.withStroke(linewidth=3, foreground="#f4f1e8")])
        ia = fig.add_axes([rect[0] / PW, rect[1] / PH, wmm / PW, hmm / PH]); ia.set_xlim(bx[0], bx[2]); ia.set_ylim(bx[1], bx[3])
        ia.set_aspect("equal"); ia.set_xticks([]); ia.set_yticks([])
        for s_ in ia.spines.values(): s_.set_edgecolor("#1d3b30"); s_.set_linewidth(1.6)
        ia.add_patch(Rectangle((bx[0], bx[1]), 2 * half_w, 2 * half_h, color="#f4f1e8", zorder=0))
        bb = box(*bx); gi = g[g.intersects(bb)].copy(); gi["geometry"] = gi.geometry.intersection(bb)
        hwi = gi["highway"] if "highway" in gi else gpd.pd.Series([None] * len(gi), index=gi.index)
        rwi = gi["railway"] if "railway" in gi else gpd.pd.Series([None] * len(gi), index=gi.index)
        lui = gi["landuse"] if "landuse" in gi else gpd.pd.Series([None] * len(gi), index=gi.index)
        isl = gi.geometry.geom_type.isin(["LineString", "MultiLineString"]); isa = gi.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
        if (isa & lui.isin(["residential"])).any(): gi[isa & lui.isin(["residential"])].plot(ax=ia, fc="#e6dccd", ec="none", zorder=1)
        if (isa & lui.isin(["forest"])).any(): gi[isa & lui.isin(["forest"])].plot(ax=ia, fc="#b7d3a0", ec="none", zorder=1)
        sel = isl & hwi.isin(["track", "path", "footway", "cycleway"])
        if sel.any(): gi[sel].plot(ax=ia, color="#a08360", lw=lw(0.5), linestyle=(0, (4, 2)), zorder=3)
        sel = isl & hwi.isin(["residential", "unclassified", "service", "living_street"])
        if sel.any(): gi[sel].plot(ax=ia, color="white", lw=lw(2.6), zorder=4, path_effects=[pe.Stroke(linewidth=lw(3.4), foreground="#a89d8c"), pe.Normal()])
        sel = isl & hwi.isin(["tertiary", "secondary", "primary"])
        if sel.any(): gi[sel].plot(ax=ia, color="#f6c766", lw=lw(3.4), zorder=4.5, path_effects=[pe.Stroke(linewidth=lw(4.2), foreground="#c4983f"), pe.Normal()])
        sel = isl & rwi.isin(["rail"])
        if sel.any():
            gi[sel].plot(ax=ia, color="#666", lw=lw(1.2), zorder=5); gi[sel].plot(ax=ia, color="white", lw=lw(0.7), linestyle=(0, (5, 5)), zorder=5.1)
        if "name" in gi:
            for nm_, grp_ in gi[isl & hwi.notna() & gi["name"].notna()].groupby("name"):
                geo = grp_.geometry.union_all(); parts = [p_ for p_ in getattr(geo, "geoms", [geo]) if p_.geom_type == "LineString"]
                if not parts: continue
                p_ = max(parts, key=lambda q: q.length)
                if p_.length < half_w * 0.35: continue
                m_ = p_.interpolate(0.5, normalized=True); a_ = p_.interpolate(max(0, p_.project(m_) - 15)); b_ = p_.interpolate(min(p_.length, p_.project(m_) + 15))
                ang = math.degrees(math.atan2(b_.y - a_.y, b_.x - a_.x)); ang = ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
                ia.text(m_.x, m_.y, nm_, fontsize=7, color="#5b5246", rotation=ang, rotation_mode="anchor", ha="center", va="center", zorder=8,
                        path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])
        for poi in D.get("pois", []):
            x_, y_ = gpd.GeoSeries.from_xy([poi["lon"]], [poi["lat"]], crs=4326).to_crs(2180).iloc[0].coords[0]
            if not (bx[0] < x_ < bx[2] and bx[1] < y_ < bx[3]): continue
            if poi.get("icon") == "wc": continue
            if poi.get("icon") == "service":
                wrench(ia, x_, y_, 7); continue
            ia.text(x_, y_, "★", fontsize=15, color=PCAT.get(poi["cat"], "#b5179e"), ha="center", va="center", zorder=12, family="DejaVu Sans",
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])
            _lft = x_ > cxi
            ia.text(x_ + (-1 if _lft else 1) * half_w * 0.05, y_ + half_h * 0.08, poi["name"], fontsize=8, weight="bold", color=PCAT.get(poi["cat"], "#b5179e"),
                    va="center", ha="right" if _lft else "left", zorder=12,
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])
        for p_, geom in zip(posts, pts.geometry):
            if bx[0] < geom.x < bx[2] and bx[1] < geom.y < bx[3]:
                ia.text(geom.x, geom.y, str(p_["nr"]), ha="center", va="center", fontsize=12, weight="bold", color="white", zorder=20,
                        bbox=dict(boxstyle="circle,pad=0.35", fc=POLEC[p_.get("pole", "do sprawdzenia")][0], ec=RING[p_["who"]],
                                  lw=1.8 if p_["who"] == "gmina" else 3.2))
        ia.set_xlabel(""); ia.set_ylabel("")
        ia.text(bx[0] + half_w * 0.04, bx[3] - half_h * 0.06, f"{tag}  {title}", fontsize=9.5, weight="bold", color="#1d3b30", va="top", zorder=25,
                path_effects=[pe.withStroke(linewidth=3, foreground="#f4f1e8")])
    inset(18.9289, 50.6362, 230, (182, 298, 100, 64), "Łazy – słupki 12 i 49, kapliczka", "A")
    inset(18.8975, 50.6157, 170, (182, 12, 100, 64), "Strzebiń przy torach – słupki 3 i 25", "B")
SUF = "_mapa_strzebin" if ZOOM else "_mapa"
exec(open("labels.py").read()); place_beside(fig, ax, POI_T, extra=[(wx, wy, 3.6 * SCALE / 1000) for wx, wy in WRENCH], hide=not ZOOM); declutter(fig, ax, PLACE_T)
if HIDDEN: print("bez podpisu na mapie ogólnej:", HIDDEN)
fig.savefig(OUT + SUF + ".pdf"); fig.savefig(OUT + SUF + "_podglad.png", dpi=60)
plt.close(fig)
if ZOOM: sys.exit(0)

# ======================= CATALOG (A4) =======================
def bike(a, x, y, s, c):
    for dx in (-0.55, 0.55): a.add_patch(Circle((x + dx * s, y - 0.15 * s), 0.38 * s, fill=False, ec=c, lw=1.3))
    a.plot([x - .55 * s, x - .1 * s, x + .55 * s, x + .25 * s, x - .1 * s, x - .3 * s, x - .1 * s],
           [y - .15 * s, y + .35 * s, y - .15 * s, y + .45 * s, y + .35 * s, y + .62 * s, y + .62 * s], color=c, lw=1.3)
from PIL import Image as _Im
from fontTools.ttLib import TTFont as _TT
from matplotlib import font_manager as _fm
FD = "../fonts/"
SIGNF = ["fira-sans-condensed-latin-600", "fira-sans-condensed-latin-ext-600"]
for _f in SIGNF: _fm.fontManager.addfont(FD + _f + ".ttf")
_fonts = [_TT(FD + f + ".ttf") for f in SIGNF]
_upm = _fonts[0]["head"].unitsPerEm; CAP = _fonts[0]["OS/2"].sCapHeight / _upm
def _adv(ch):
    for t in _fonts:
        g = t.getBestCmap().get(ord(ch))
        if g: return t["hmtx"][g][0] / _upm
    return 0.5
def tw(text, pt):  # text width in mm
    return sum(_adv(c) for c in text) * pt * 0.3528
SIGN_NAVY = "#042856"
def _load(fn, box, wipe):
    im = np.array(_Im.open(fn).convert("RGB").crop(box)).copy()
    x0, y0 = box[0], box[1]
    wx0, wy0, wx1, wy1 = wipe
    reg = im[wy0 - y0:wy1 - y0, wx0 - x0:wx1 - x0]
    bg = np.median(im[wy0 - y0:wy1 - y0, wx0 - x0:wx1 - x0].reshape(-1, 3), axis=0)
    reg[:] = bg.astype(np.uint8)
    return im
# templates from Bartosz's mockups (pixel geometry measured on the mockups)
TPL = {
  ("1", "L"): dict(img=_load(MOCK1, (18, 275, 706, 483), (284, 326, 690, 440)), x0=18, y0=275, name_x=291, km_r=675, base=[390], cap=37),
  ("1", "R"): dict(img=_load(MOCK1, (741, 274, 1430, 483), (882, 326, 1282, 440)), x0=741, y0=274, name_x=890, km_r=1271, base=[390], cap=37),
  ("2", "L"): dict(img=_load(MOCK2, (20, 290, 705, 501), (288, 328, 685, 456)), x0=20, y0=290, name_x=295, km_r=669, base=[373, 444], cap=35),
  ("2", "R"): dict(img=_load(MOCK2, (740, 290, 1425, 501), (880, 328, 1268, 456)), x0=740, y0=290, name_x=887, km_r=1256, base=[373, 444], cap=35),
}
def plate(a, x, y, grp, w=86):
    """Plate exactly in the agreed layout: [arrow tip] bike  Name  x,x km  (1 or 2 lines)."""
    deg = grp[0].get("deg")
    right = deg is not None and (math.sin(math.radians(deg)) > 0.34 or (abs(math.sin(math.radians(deg))) <= 0.34 and math.cos(math.radians(deg)) > 0))
    t = TPL[(str(len(grp)), "R" if right else "L")]
    H, W = t["img"].shape[:2]; sc = w / W; h = H * sc
    a.imshow(t["img"], extent=(x, x + w, y, y + h), interpolation="lanczos", zorder=2, aspect="auto")
    pt = t["cap"] * sc / CAP / 0.3528
    X = lambda px: x + (px - t["x0"]) * sc
    Y = lambda py: y + h - (py - t["y0"]) * sc
    nx, kr = X(t["name_x"]), X(t["km_r"])
    for k, pl in enumerate(grp):
        km = (f"{pl['km']:.1f} km".replace(".", ",")) if pl.get("km") is not None else ""
        avail = kr - nx - tw(km, pt) - 3.5
        p_ = pt * min(1, avail / max(tw(pl["name"], pt), 0.1))
        by = Y(t["base"][k])
        a.text(nx, by, pl["name"], family=SIGNF, fontsize=p_, color=SIGN_NAVY, va="baseline", ha="left", zorder=3)
        a.text(kr, by, km, family=SIGNF, fontsize=pt, color=SIGN_NAVY, va="baseline", ha="right", zorder=3)
    if deg is not None:
        a.text(x + w / 2, y - 2.4, "kier. " + DIR8[int((deg + 22.5) // 45) % 8], fontsize=6.3, color="#6b7a90", ha="center")

MAN = next((a_.split("=", 1)[1] for a_ in sys.argv if a_.startswith("--manifest=")), None)
REP = next((a_.split("=", 1)[1] for a_ in sys.argv if a_.startswith("--report=")), None)
REPORT = {r["nr"]: r for r in json.load(open(REP))} if REP else {}
def change_text(nr):
    r = REPORT.get(nr)
    if not r: return ""
    add = [f"+{n} ({w})" for n, km, w in r["prop"] if w != "jest w uMap"]
    rem = [f"−{n} ({w})" for n, w in r["removed"]]
    return "; ".join(add + rem)
MANIFEST = json.load(open(MAN)) if MAN else None
def plate_png(a, x, y, item, w=86):
    w = w * item.get("W", 800) / 800
    im = _Im.open(item["png"]).convert("RGBA"); arr = np.array(im)
    h = w * arr.shape[0] / arr.shape[1]
    a.imshow(arr, extent=(x, x + w, y, y + h), interpolation="none", zorder=2, aspect="auto")   # bez resamplingu – pełna rozdzielczość w PDF
    if item.get("deg") is not None:
        a.text(x + w / 2, y - 2.4, "kier. " + DIR8[int((item["deg"] + 22.5) // 45) % 8], fontsize=6.3, color="#6b7a90", ha="center")

AW, AH = 210, 297
with PdfPages(OUT + "_katalog.pdf") as pdf:
    # summary pages (z podziałem na strony)
    POLE_PL = {"istniejący": ("#2563a8", "istn."), "nowy": ("#d9480f", "nowy"), "opcjonalny": ("#7b4fb3", "opcj."), "do sprawdzenia": ("#8a8f94", "?")}
    hdr = ["Nr", "Lokalizacja", "Kierunki", "Słupek", "Tab.", "Uzgodnienie"]; xs = [15, 23, 70, 152, 165, 175]
    def spage(first):
        f_ = plt.figure(figsize=(AW * MM, AH * MM)); a_ = f_.add_axes([0, 0, 1, 1]); a_.set_xlim(0, AW); a_.set_ylim(0, AH); a_.set_axis_off()
        if first:
            a_.text(15, 280, "Drogowskazy rowerowe – Sołectwo Strzebiń jako HUB rowerowy", fontsize=16, weight="bold", color="#1d3b30")
            a_.text(15, 273, "Katalog słupków · propozycja · listopad 2026 · tabliczki wg generatora HUB Strzebiń V21\n"
                    "(dibond, cięcie po obrysie, strefa montażowa 60 mm; 800 × 200 mm, Fira Sans Condensed 44 mm)", fontsize=9, color="#5b6b62", va="top", linespacing=1.4)
            y0 = 258
        else:
            a_.text(15, 282, "Katalog słupków – zestawienie (ciąg dalszy)", fontsize=12, weight="bold", color="#1d3b30"); y0 = 272
        for h_, xx in zip(hdr, xs): a_.text(xx, y0, h_, fontsize=8, weight="bold", color="#1d3b30")
        a_.plot([15, 196], [y0 - 2, y0 - 2], color="#1d3b30", lw=0.8)
        return f_, a_, y0 - 7
    fig, a, yy = spage(True)
    for p in posts:
        kier = ", ".join(pl["name"] for pl in p["plates"])
        lines_ = []; cur = ""
        for w_ in kier.split(" "):
            if len(cur + " " + w_) > 48: lines_.append(cur); cur = w_
            else: cur = (cur + " " + w_).strip()
        lines_.append(cur)
        loc_ = []; cur = ""
        for w_ in p["loc"].replace("Las – ", "Las: ").split(" "):
            if len(cur + " " + w_) > 27: loc_.append(cur); cur = w_
            else: cur = (cur + " " + w_).strip()
        loc_.append(cur); loc_ = loc_[:2]
        hrow = 4.4 * max(len(lines_), len(loc_)) + 2.6
        if yy - hrow < 22:
            pdf.savefig(fig); plt.close(fig); fig, a, yy = spage(False)
        pc, pl_ = POLE_PL.get(p.get("pole", "do sprawdzenia"), ("#888", "?"))
        a.text(15, yy, str(p["nr"]), fontsize=8, weight="bold", color=pc, va="top")
        a.text(23, yy, "\n".join(loc_), fontsize=7.6, va="top", linespacing=1.3)
        a.text(70, yy, "\n".join(lines_), fontsize=7.6, va="top", linespacing=1.3)
        a.text(152, yy, pl_ + ("\n(istn.)" if p.get("slup_jest") else ""), fontsize=7.4, va="top", color=pc, linespacing=1.3)
        a.text(165, yy, str(len(MANIFEST[str(p["nr"])]) if MANIFEST else len(p["groups"])), fontsize=7.6, va="top")
        a.text(175, yy, " + ".join(x.replace("Nadleśnictwo", "Nadl.").replace("Gmina Koszęcin", "Gmina") for x in p["agree"]) or "—", fontsize=7.6, va="top")
        yy -= hrow
        a.plot([15, 196], [yy + 1.2, yy + 1.2], color="#ddd", lw=0.4)
    a.text(15, 14, "Odległości liczone po drogach z OpenStreetMap do centrum miejscowości. Zwrot ← / → wstępny (wschód = →, zachód = ←),\n"
           "do weryfikacji w terenie; pod tabliczką kierunek kompasowy. Słupek: istn. – istniejący, nowy – do postawienia, opcj. – opcjonalny (do ustalenia).",
           fontsize=6.5, color="#777", va="top", linespacing=1.4)
    pdf.savefig(fig); plt.close(fig)
    if REPORT:
        def rpage():
            f_ = plt.figure(figsize=(AW * MM, AH * MM)); a_ = f_.add_axes([0, 0, 1, 1]); a_.set_xlim(0, AW); a_.set_ylim(0, AH); a_.set_axis_off()
            a_.text(15, 282, "Propozycja kierunków – porównanie z uMap", fontsize=15, weight="bold", color="#1d3b30")
            a_.text(15, 275, "Zasady: każda droga wychodząca ze skrzyżowania dostaje najbliższą miejscowość; cel raz pokazany musi być powtarzany "
                    "na kolejnych słupkach (ciągłość);\nnie kierujemy do miejscowości, w której stoi słupek. Trasy liczone z preferencją dróg utwardzonych "
                    "i Twoich ocen przejezdności.", fontsize=6.8, color="#5b6b62", va="top", linespacing=1.4)
            for h_, xx in zip(["Nr", "Lokalizacja", "Jest w uMap", "Dodane (+)", "Usunięte (−)"], [15, 22, 58, 108, 166]):
                a_.text(xx, 262, h_, fontsize=7.5, weight="bold", color="#1d3b30")
            a_.plot([15, 196], [260, 260], color="#1d3b30", lw=0.8)
            return f_, a_
        import textwrap
        fig, a = rpage(); yy = 256
        for nr in sorted(REPORT):
            r = REPORT[nr]
            cols = [", ".join(r["jest"]),
                    "\n".join(f"{n} {km:.1f} km".replace(".", ",") + (" – ciągłość z " + w.split()[-1] if w.startswith("ciągłość") else " – nowy kierunek")
                              for n, km, w in r["prop"] if w != "jest w uMap") or "—",
                    "\n".join(f"{n} – {w}" for n, w in r["removed"]) or "—"]
            wrapped = [textwrap.fill(cols[0], 26), cols[1], textwrap.fill(cols[2], 18)]
            nl = max([c.count("\n") + 1 for c in wrapped] + [textwrap.fill(r["loc"], 20).count("\n") + 1])
            if yy - nl * 3.4 < 12:
                pdf.savefig(fig); plt.close(fig); fig, a = rpage(); yy = 256
            a.text(15, yy, str(nr), fontsize=7.5, weight="bold", va="top")
            a.text(22, yy, textwrap.fill(r["loc"], 20), fontsize=7, va="top", linespacing=1.25)
            for txt, xx, col in zip(wrapped, [58, 108, 166], ["#333", "#1e7a3c", "#b5462a"]):
                a.text(xx, yy, txt, fontsize=7, va="top", color=col, linespacing=1.25)
            yy -= nl * 3.4 + 2.6
            a.plot([15, 196], [yy + 1.3, yy + 1.3], color="#ddd", lw=0.4)
        pdf.savefig(fig); plt.close(fig)
    # post pages: flow layout
    def newpage():
        f_ = plt.figure(figsize=(AW * MM, AH * MM)); a_ = f_.add_axes([0, 0, 1, 1]); a_.set_xlim(0, AW); a_.set_ylim(0, AH); a_.set_axis_off(); a_.set_autoscale_on(False)
        return f_, a_
    fig, a = newpage(); top = 285
    for p in posts:
        nplates = len(MANIFEST[str(p["nr"])]) if MANIFEST else len(p["groups"])
        rows = (nplates + 1) // 2
        chg = ""   # wersja dla gminy: bez komentarzy o zmianach
        hgt = 20 + rows * 32 + 8
        if top - hgt < 10:
            pdf.savefig(fig); plt.close(fig); fig, a = newpage(); top = 285
        c = WHO[p["who"]][0]
        a.text(19, top - 5, str(p["nr"]), ha="center", va="center", fontsize=13, weight="bold", color="white",
               bbox=dict(boxstyle="circle,pad=0.35", fc=c, ec="none"))
        a.text(28, top - 2.5, p["loc"], fontsize=13, weight="bold", color="#1d3b30", va="center")
        a.text(28, top - 8.5, f"{p['lat']:.5f}, {p['lon']:.5f} · {p['status']} · uzgodnienie: {', '.join(p['agree']) or 'brak'}"
               + (f" · tabliczek w pliku: {p['n_plates']}" if p["n_plates"] else ""), fontsize=7.5, color="#5b6b62", va="center")
        if MANIFEST:
            for k, item in enumerate(MANIFEST[str(p["nr"])]):
                plate_png(a, 15 + (k % 2) * 92, top - 44 - (k // 2) * 32, item)
        else:
            for k, grp in enumerate(p["groups"]):
                plate(a, 15 + (k % 2) * 92, top - 44 - (k // 2) * 32, grp)
        ny = top - 20 - rows * 32 - 2
        if chg:
            import textwrap as _tw
            a.text(15, ny, _tw.fill("Zmiany względem uMap: " + chg, 150), fontsize=7, color="#1e7a3c", va="top"); ny -= 8
        if False:
            a.text(15, ny, "Uwagi: " + "; ".join(p["notes"]), fontsize=7.5, color="#b5462a", va="top")
        top -= hgt
        a.plot([15, 195], [top + 3, top + 3], color="#ccc", lw=0.5)
    pdf.savefig(fig); plt.close(fig)
print("ok", n_pl)
