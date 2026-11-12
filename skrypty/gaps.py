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
import glob as _g
from matplotlib import font_manager as _fmr
for _f in _g.glob("../fonts/Inter-*.ttf"): _fmr.fontManager.addfont(_f)
plt.rcParams.update({"font.family": "Inter", "pdf.fonttype": 42})
tf = Transformer.from_crs(4326, 2180, always_xy=True); P = lambda c: tf.transform(*c)
osm = json.load(open(OSM))["features"]; D = json.load(open(SIGNS))

# edge -> way attributes
EA = {}
for f in osm:
    p = f["properties"]
    if not p.get("highway") or f["geometry"]["type"] != "LineString": continue
    cs = [tuple(round(v, 7) for v in c) for c in f["geometry"]["coordinates"]]
    for a, b in zip(cs, cs[1:]): EA[frozenset((a, b))] = p
used = collections.Counter()
for p in D["posts"]:
    for pl in p["plates"]:
        path = pl.get("path") or []
        for a, b in zip(path, path[1:]): used[frozenset((tuple(a), tuple(b)))] += 1
for c in D["connectors"]:
    for a, b in zip(c["path"], c["path"][1:]): used[frozenset((tuple(a), tuple(b)))] += 1

sv = gpd.read_file(SURVEY).to_crs(2180); sv = sv[sv.geometry.geom_type == "LineString"]
checked = unary_union(sv.geometry.buffer(20))
PAVED_S = {"asphalt", "paved", "concrete", "paving_stones", "sett", "concrete:plates", "chipseal"}
PAVED_H = {"primary", "secondary", "tertiary", "trunk", "residential", "living_street"}
SURF_PL = {"asphalt": "asfalt", "paved": "utwardzona", "concrete": "beton", "paving_stones": "kostka", "sett": "kostka kamienna",
           "gravel": "tłuczeń/żwir", "fine_gravel": "drobny żwir", "compacted": "ubita", "dirt": "ziemia", "ground": "ziemia",
           "sand": "piach", "grass": "trawa", "unpaved": "nieutwardzona", "earth": "ziemia", "mud": "błoto"}
HW_PL = {"track": "droga leśna/polna", "path": "ścieżka", "footway": "chodnik/ścieżka piesza", "cycleway": "droga rowerowa",
         "residential": "ulica", "unclassified": "droga lokalna", "service": "droga dojazdowa", "tertiary": "droga powiatowa/gminna",
         "secondary": "droga wojewódzka", "primary": "droga krajowa", "living_street": "strefa zamieszkania"}
PAVED_NAMES = {"1 Maja", "Dębowa", "Kosmonautów", "Hugona Kołłątaja"}   # asfalt wg Bartosza
PAVED_IDS = {"way/976663503", "way/587698466", "way/976663504"}   # Łazy–Strzebiń: asfalt wg Bartosza
import glob
SVW = set()   # drogi z Google Street View (auto przejechało => przejezdne rowerem, wg Bartosza)
for fn in glob.glob("sv_cov_*.json"):
    for wid_, r_ in json.load(open(fn))["roads"].items():
        if r_["seen"] >= 3 and r_["on"] / r_["seen"] > 0.7: SVW.add(wid_)
groups = collections.defaultdict(list)
for e, n in used.items():
    a, b = tuple(e) if len(e) == 2 else (next(iter(e)),) * 2
    ln = LineString([P(a), P(b)])
    if ln.length == 0 or checked.contains(ln.interpolate(0.5, normalized=True)): continue
    attrs = EA.get(e, {})
    groups[attrs.get("@id", "?")].append((ln, attrs, n))
feats = []
for wid, items in groups.items():
    attrs = items[0][1]; geom = linemerge(MultiLineString([i[0] for i in items]))
    surf, hw = attrs.get("surface"), attrs.get("highway", "")
    paved = surf in PAVED_S or (surf is None and hw in PAVED_H) or wid in PAVED_IDS or attrs.get("name") in PAVED_NAMES
    if wid in PAVED_IDS or attrs.get("name") in PAVED_NAMES: surf = "asphalt"
    svx = (not paved) and wid in SVW
    feats.append(dict(geometry=geom, priorytet="niższy (utwardzona wg OSM)" if paved else ("niższy (Street View – przejechane autem)" if svx else "WYSOKI (nieutwardzona / brak danych)"),
                      paved=paved or svx, nazwa=attrs.get("name", ""), typ_osm=HW_PL.get(hw, hw),
                      naw_osm=SURF_PL.get(surf, surf or "brak danych"), tracktype=attrs.get("tracktype", ""), uzycie=max(i[2] for i in items),
                      osm=wid))
gdf = gpd.GeoDataFrame(feats, crs=2180)
km_hi = gdf[~gdf.paved].length.sum() / 1000; km_lo = gdf[gdf.paved].length.sum() / 1000
print(f"gaps: {len(gdf)} odcinków, wysoki {km_hi:.1f} km, niższy {km_lo:.1f} km")

# GeoJSON in the user's survey schema (empty fields to fill in uMap)
g4 = gdf.to_crs(4326)
out_feats = []
for _, r in g4.iterrows():
    out_feats.append({"type": "Feature", "geometry": json.loads(gpd.GeoSeries([r.geometry]).to_json())["features"][0]["geometry"],
                      "properties": {"Priorytet sprawdzenia": r.priorytet, "Nazwa (OSM)": r.nazwa, "Typ drogi (OSM)": r.typ_osm,
                                     "Nawierzchnia (OSM)": r.naw_osm, "Nawierzchnia": "", "Zagęszczenie nawierzchni": "", "Stan": "",
                                     "Przejezdność ogólna": "", "Warunki po deszczu": "", "Typ drogi": "", "Uwagi": "", "Data": "",
                                     "OSM": r.osm}})
json.dump({"type": "FeatureCollection", "features": out_feats}, open(OUT + "_do_sprawdzenia.geojson", "w"), ensure_ascii=False)

# ---------------- map ----------------
MM = 1 / 25.4; lw = lambda mm: mm / 25.4 * 72
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
C_OK, C_SR, C_TR, C_HI, C_LO, C_CON = "#4f8f5b", "#f0a12b", "#d43d33", "#6a3fb5", "#8fb0d6", "#0e8a8a"
pr_ = sv.get("Przejezdność ogólna")
ok_ = sv[~pr_.isin(["średnia", "trudna"])]; bad = sv[pr_.isin(["średnia", "trudna"])].copy()
_routes = unary_union([LineString([P(a), P(b)]) for e in used for a, b in [tuple(e) if len(e) == 2 else (next(iter(e)),) * 2] if a != b]).buffer(30)
bad = bad[bad.geometry.apply(lambda ge: ge.intersection(_routes).length / max(ge.length, 1) > 0.3)].copy()   # tylko odcinki na trasach drogowskazów
ok_.plot(ax=ax, color=C_OK, lw=lw(1.0), zorder=7, alpha=0.8)
gdf[gdf.paved].plot(ax=ax, color=C_LO, lw=lw(1.2), zorder=8, capstyle="round", linestyle=(0, (4, 2)))
gdf[~gdf.paved].plot(ax=ax, color=C_HI, lw=lw(1.8), zorder=9, capstyle="round", linestyle=(0, (5, 2)),
                     path_effects=[pe.Stroke(linewidth=lw(2.8), foreground="white"), pe.Normal()])
bad["_n"] = range(1, len(bad) + 1)
for _, r in bad.iterrows():
    c = C_TR if r["Przejezdność ogólna"] == "trudna" else C_SR
    gpd.GeoSeries([r.geometry]).plot(ax=ax, color=c, lw=lw(1.8), zorder=10, capstyle="round",
                                     path_effects=[pe.Stroke(linewidth=lw(2.8), foreground="white"), pe.Normal()])
for c in D["connectors"]:
    ln = LineString([P(n) for n in c["path"]])
    gpd.GeoSeries([ln]).plot(ax=ax, color=C_CON, lw=lw(1.4), zorder=10, linestyle=(0, (1, 1.5)))
    # podpis przy samej linii, równolegle do niej (najprostszy fragment)
    best = None
    for t in np.linspace(0.2, 0.8, 25):
        a_, b_ = ln.interpolate(t - 0.15, normalized=True), ln.interpolate(t + 0.15, normalized=True)
        chord = math.hypot(b_.x - a_.x, b_.y - a_.y); arc = 0.3 * ln.length
        if best is None or chord / arc > best[0]: best = (chord / arc, t, a_, b_)
    _, t, a_, b_ = best
    m = ln.interpolate(t, normalized=True); ang = math.degrees(math.atan2(b_.y - a_.y, b_.x - a_.x))
    if ang > 90: ang -= 180
    if ang < -90: ang += 180
    nx_, ny_ = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
    off = 0.0045 * SCALE   # ok. 4,5 mm nad linią
    ax.text(m.x + nx_ * off, m.y + ny_ * off, f"{c['frm']} → {c['to'].replace(' Szlak Rowerowy', '')} · {c['km']:.1f} km".replace(".", ","),
            fontsize=8.5, weight="bold", color=C_CON, zorder=11, ha="center", va="center", rotation=ang, rotation_mode="anchor",
            path_effects=[pe.withStroke(linewidth=3, foreground="white")])
for p in D["posts"]:
    x, y = tf.transform(p["lon"], p["lat"])
    ax.text(x, y, str(p["nr"]), ha="center", va="center", fontsize=8, weight="bold", color="white", zorder=20,
            bbox=dict(boxstyle="circle,pad=0.3", fc="#1d3b30", ec="white", lw=1.2))
PLACE_T = []
for name, (lon, lat) in D["places"].items():
    x, y = tf.transform(lon, lat)
    if not (x0 + PANEL / 1000 * SCALE + 150 < x < x1 - 150 and y0 + 150 < y < y1 - 350): continue
    big = name in ["Strzebiń", "Koszęcin", "Kalety", "Boronów", "Psary", "Babienica", "Piasek", "Hucisko"]
    PLACE_T.append((2 if big else 1, ax.text(x, y + 260, name.upper() if big else name, ha="center", fontsize=12 if big else 8, weight="bold" if big else "medium",
            color="#3a3630", zorder=12, path_effects=[pe.withStroke(linewidth=3, foreground="#f4f1e8")])))
pan = fig.add_axes([0, 0, PANEL / PW, 1]); pan.set_axis_off(); pan.set_xlim(0, PANEL); pan.set_ylim(0, PH)
pan.add_patch(Rectangle((0, 0), PANEL, PH, color="#f7f4ec")); pan.plot([PANEL - 0.6, PANEL - 0.6], [0, PH], color="#1d3b30", lw=lw(0.8))
T = lambda x, y, s, **k: pan.text(x, y, s, color=k.pop("color", "#1d2a23"), **k)
M = 12
T(M, 398, "SOŁECTWO STRZEBIŃ · HUB ROWEROWY", fontsize=12, weight="bold", color="#8a5300")
T(M, 390, "Stan dróg\nna trasach\ndrogowskazów", fontsize=27, weight="bold", va="top", linespacing=1.05)
T(M, 330, "Drogi, którymi prowadzą proponowane drogowskazy:\nzmierzone odcinki średniej lub złej jakości\noraz odcinki, których jeszcze nie sprawdzono", fontsize=9.5,
  va="top", color="#4b5d53", linespacing=1.4)
km_bad = bad.length.sum() / 1000; km_tr = bad[bad["Przejezdność ogólna"] == "trudna"].length.sum() / 1000
for i, (v, u) in enumerate([(f"{km_bad:.1f}".replace(".", ","), "km średniej / złej jakości"), (f"{km_hi:.1f}".replace(".", ","), "km do sprawdzenia"),
                            (f"{km_lo:.1f}".replace(".", ","), "km niższy priorytet")]):
    T(M + i * 44, 290, v, fontsize=22, weight="bold", color="#8a5300"); T(M + i * 44, 283, u, fontsize=8.5, color="#4b5d53")
y = 268
T(M, y, "ODCINKI ŚREDNIEJ LUB ZŁEJ JAKOŚCI (pomiary 2026)", fontsize=9, weight="bold", color="#4b5d53"); y -= 9
for c, w_, lab, ls in [(C_TR, 1.8, f"zła jakość (przejezdność trudna) – {km_tr:.1f} km".replace(".", ","), "-"),
                       (C_SR, 1.8, f"średnia jakość – {km_bad - km_tr:.1f} km".replace(".", ","), "-")]:
    pan.plot([M, M + 10], [y, y], color=c, lw=lw(w_), solid_capstyle="round"); T(M + 14, y, lab, fontsize=9.5, va="center"); y -= 8
y -= 2
for _, r in bad.iterrows():
    c = C_TR if r["Przejezdność ogólna"] == "trudna" else C_SR
    pan.plot([M + 1, M + 7], [y, y], color=c, lw=lw(2.2), solid_capstyle="round")
    desc = f"{r.geometry.length:.0f} m · {r.get('Nawierzchnia') or ''}, {r.get('Typ drogi') or ''}"
    if isinstance(r.get("Uwagi"), str) and r["Uwagi"]: desc += f" – {r['Uwagi']}"
    T(M + 10, y, desc[:95], fontsize=7.8, va="center", color="#2c3a32"); y -= 6.5
y -= 5; T(M, y, "DO SPRAWDZENIA (brak pomiarów)", fontsize=9, weight="bold", color="#4b5d53"); y -= 9
for c, w_, lab, ls in [(C_HI, 1.8, "priorytet – nieutwardzone lub brak danych w OSM", (0, (3, 1.2))),
                       (C_LO, 1.2, "niższy priorytet – asfalt / droga publiczna\nwg OSM lub przejechane autem (Street View)", (0, (3, 1.2))),
                       (C_OK, 1.0, "sprawdzone, w dobrym stanie", "-"),
                       (C_CON, 1.4, "proponowane łączniki do szlaków", (0, (1, 1)))]:
    pan.plot([M, M + 10], [y, y], color=c, lw=lw(w_), solid_capstyle="round", linestyle=ls)
    T(M + 14, y, lab, fontsize=9, va="center", linespacing=1.3); y -= 12 if "\n" in lab else 8
y -= 3
pan.text(M + 5, y, "7", ha="center", va="center", fontsize=8, weight="bold", color="white",
         bbox=dict(boxstyle="circle,pad=0.3", fc="#1d3b30", ec="white", lw=1)); T(M + 14, y, "słupek z drogowskazami", fontsize=9, va="center"); y -= 12
T(M, y, "Odcinki do sprawdzenia są w pliku „drogowskazy_do_sprawdzenia.geojson”\n"
        "(układ pól jak Twoja warstwa w uMapie) – uzupełniaj Stan,\nNawierzchnię itd. po objechaniu odcinka.", fontsize=8, va="top", color="#4b5d53", linespacing=1.45)
T(M, 10, "Dane mapy © autorzy OpenStreetMap (ODbL)", fontsize=7.5, color="#4b5d53")
exec(open("labels.py").read()); declutter(fig, ax, PLACE_T)
fig.savefig(OUT + "_stan_drog.pdf"); fig.savefig(OUT + "_stan_drog_podglad.png", dpi=60)
print("ok")
