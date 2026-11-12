"""Given an initial pixel<->EPSG:3857 similarity, refine locally and mark OSM roads covered by Street View."""
import json, sys, numpy as np
from PIL import Image
from scipy import ndimage
from pyproj import Transformer
IMG, INIT, OUT = sys.argv[1:4]
t = Transformer.from_crs(4326, 3857, always_xy=True)
im = np.array(Image.open(IMG).convert('RGB')).astype(int)
R, Gc, B = im[..., 0], im[..., 1], im[..., 2]
core = (R < 120) & (Gc > 120) & (Gc < 215) & (B > 140) & (B < 230) & (Gc - R > 60)
H, W = core.shape; LEG = json.load(open(INIT)).get("legend", [0, int(H * 0.83), W, H])
core[LEG[1]:LEG[3], LEG[0]:LEG[2]] = False
dist = ndimage.distance_transform_edt(~core)
F = json.load(open('osm2_clean.geojson'))['features']
roads = [f for f in F if f['geometry']['type'] == 'LineString' and f['properties'].get('highway') in
         ('primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'service', 'track', 'living_street', 'path', 'cycleway')]
def dens(f, step):
    cs = np.array([t.transform(*c) for c in f['geometry']['coordinates']]); pts = []
    for a, b in zip(cs, cs[1:]):
        n = max(1, int(np.hypot(*(b - a)) / step)); pts += [a + (b - a) * k / n for k in range(n)]
    return np.array(pts + [cs[-1]])
RP = [dens(f, 12) for f in roads]
s0, tx0, ty0 = json.load(open(INIT))['transform']
def visible(u, v): return (u > 2) & (v > 2) & (u < W - 3) & (v < H - 3) & ~((u > LEG[0]) & (u < LEG[2]) & (v > LEG[1]) & (v < LEG[3]))
allp = np.vstack(RP)
def score(s, tx, ty):   # share of coverage pixels explained by OSM roads
    u = s * allp[:, 0] + tx; v = -s * allp[:, 1] + ty; m = visible(u, v)
    img = np.zeros_like(core); img[v[m].astype(int), u[m].astype(int)] = True
    near = ndimage.binary_dilation(img, iterations=3)
    return (near & core).sum() / max(1, core.sum())
best = (score(s0, tx0, ty0), s0, tx0, ty0)
for ss, span in [(0.02, 8), (0.005, 2)]:
    b0 = best
    for ds in np.linspace(-ss, ss, 5):
        for dx in np.linspace(-span, span, 5):
            for dy in np.linspace(-span, span, 5):
                sc = score(b0[1] * (1 + ds), b0[2] + dx, b0[3] + dy)
                if sc > best[0]: best = (sc, b0[1] * (1 + ds), b0[2] + dx, b0[3] + dy)
print('coverage explained', round(best[0], 3))
_, s, tx, ty = best
res = {}
for f, pts in zip(roads, RP):
    u = s * pts[:, 0] + tx; v = -s * pts[:, 1] + ty; m = visible(u, v)
    if m.sum() < 3: continue
    on = (dist[v[m].astype(int), u[m].astype(int)] < 4)
    res[f['properties'].get('@id')] = dict(name=f['properties'].get('name'), seen=int(m.sum()), on=int(on.sum()))
json.dump(dict(transform=[s, tx, ty], roads=res), open(OUT, 'w'), ensure_ascii=False)
print('roads in view', len(res), 'mostly covered', sum(r['on'] / r['seen'] > 0.8 for r in res.values()))
