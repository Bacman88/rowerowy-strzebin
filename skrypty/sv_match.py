"""Georeference a Google Street View coverage screenshot to OSM roads and find roads with coverage."""
import json, sys, numpy as np
from PIL import Image
from scipy import ndimage
from pyproj import Transformer
IMG, LABELS = sys.argv[1], json.loads(sys.argv[2])
t = Transformer.from_crs(4326, 3857, always_xy=True)
im = np.array(Image.open(IMG).convert('RGB')).astype(int)
R, Gc, B = im[..., 0], im[..., 1], im[..., 2]
core = (R < 120) & (Gc > 120) & (Gc < 215) & (B > 140) & (B < 230) & (Gc - R > 60)
core[int(im.shape[0] * 0.83):, :] = False                     # legend box at the bottom
dist = ndimage.distance_transform_edt(~core)
D = json.load(open('signs.json')); PL = D['places']
F = json.load(open('osm2_clean.geojson'))['features']
roads = [f for f in F if f['geometry']['type'] == 'LineString' and f['properties'].get('highway') in
         ('primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'service', 'track', 'living_street')]
samp = []
for f in roads:
    cs = np.array([t.transform(*c) for c in f['geometry']['coordinates']])
    for a, b in zip(cs, cs[1:]):
        n = max(1, int(np.hypot(*(b - a)) / 40))
        for k in range(n): samp.append(a + (b - a) * k / n)
samp = np.array(samp)
# initial similarity from two labelled places (pixel positions of the place points)
(n1, u1, v1), (n2, u2, v2) = LABELS[:2]
X1 = np.array(t.transform(*PL[n1])); X2 = np.array(t.transform(*PL[n2]))
s = np.hypot(u2 - u1, v2 - v1) / np.hypot(*(X2 - X1))
tx, ty = u1 - s * X1[0], v1 + s * X1[1]
# score = how much of the cyan coverage is explained by OSM roads (coverage pixels near a projected road sample)
cy, cx = np.nonzero(core); sel = np.random.default_rng(0).choice(len(cx), min(4000, len(cx)), replace=False); cpx = np.stack([cx[sel], cy[sel]], 1).astype(float)
from scipy.spatial import cKDTree
def score(s, tx, ty):
    u = s * samp[:, 0] + tx; v = -s * samp[:, 1] + ty
    m = (u > -50) & (v > -50) & (u < im.shape[1] + 50) & (v < im.shape[0] + 50)
    if m.sum() < 50: return 0
    d, _ = cKDTree(np.stack([u[m], v[m]], 1)).query(cpx, distance_upper_bound=60)
    return np.exp(-np.minimum(d, 60) / 4).mean()
best = (score(s, tx, ty), s, tx, ty)
for it, (ss, ns, span, nt) in enumerate([(0.25, 11, 200, 21), (0.06, 9, 40, 17), (0.015, 9, 10, 11), (0.004, 9, 3, 7)]):
    b0 = best
    for ds in np.linspace(-ss, ss, ns):
        for dx in np.linspace(-span, span, nt):
            for dy in np.linspace(-span, span, nt):
                sc = score(b0[1] * (1 + ds), b0[2] + dx, b0[3] + dy)
                if sc > best[0]: best = (sc, b0[1] * (1 + ds), b0[2] + dx, b0[3] + dy)
    print('iter', it, 'score', round(best[0], 3))
_, s, tx, ty = best
# per road: share of samples on coverage
out = []
for f in roads:
    cs = np.array([t.transform(*c) for c in f['geometry']['coordinates']])
    pts = []
    for a, b in zip(cs, cs[1:]):
        n = max(1, int(np.hypot(*(b - a)) / 15))
        pts += [a + (b - a) * k / n for k in range(n)]
    pts = np.array(pts + [cs[-1]])
    u = s * pts[:, 0] + tx; v = -s * pts[:, 1] + ty
    m = (u > 2) & (v > 2) & (u < im.shape[1] - 3) & (v < im.shape[0] * 0.83 - 3)
    if m.sum() < 3: continue
    on = (dist[v[m].astype(int), u[m].astype(int)] < 4).mean()
    out.append(dict(id=f['properties'].get('@id'), name=f['properties'].get('name'), hw=f['properties']['highway'],
                    inside=float(m.mean()), on=float(on)))
json.dump(dict(transform=[s, tx, ty], roads=out), open(sys.argv[3], 'w'), ensure_ascii=False)
cov = [r for r in out if r['on'] > 0.8 and r['inside'] > 0.5]
print('roads in view', len(out), 'covered', len(cov))
