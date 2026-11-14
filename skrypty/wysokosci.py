"""Wysokości wzdłuż odcinków dróg dla nawigacji „Jedź” (profil trasy, czas jazdy pod górkę / z górki).
Źródło: numeryczny model terenu GUGiK (siatka 5 m, EPSG:2180) – dane/nmt.npz; gdy go brak, pobieramy go
z wydania „nmt” na GitHubie (zob. gałąź `wysokosci`, workflow NMT).
Wynik: <strona>/stan/wysokosci.js → window.WYS = {k: 25, z: {id: [wysokość dm, różnica dm, …]}}
  – próbki co ~25 m wzdłuż odcinka (pierwsza na początku, ostatnia na końcu).
Użycie (po odcinki.py): python3 wysokosci.py ../dane/nmt.npz ../out/strona
"""
import json, math, os, sys, urllib.request
import numpy as np
from pyproj import Transformer

NMT, OUT = sys.argv[1:3]
URL = "https://github.com/Bacman88/rowerowy-strzebin/releases/download/nmt/nmt.npz"
K = 25
if not os.path.exists(NMT):
    try:
        print("pobieram model terenu…"); urllib.request.urlretrieve(URL, NMT)
    except Exception as e:
        print("brak modelu terenu (", e, ") – profil bez wysokości")
        open(f"{OUT}/stan/wysokosci.js", "w").write("window.WYS=null;"); sys.exit(0)
d = np.load(NMT)
Z, STEP, X0, Y1 = d["z"], float(d["step"]), float(d["x0"]), float(d["y1"])
ND = -32768
tr = Transformer.from_crs(4326, 2180, always_xy=True)

txt = open(f"{OUT}/stan/odcinki.js").read()
ODC = json.loads(txt[txt.index("=") + 1:txt.index(";\nwindow.ODC_ALIASY")])

def probki(c):
    ll = [(c[i], c[i + 1]) for i in range(0, len(c), 2)]
    lon = [q[1] for q in ll]; lat = [q[0] for q in ll]
    x, y = tr.transform(lon, lat)
    P = list(zip(x, y)); cum = [0.0]
    for a, b in zip(P, P[1:]): cum.append(cum[-1] + math.dist(a, b))
    L = cum[-1]; n = max(1, round(L / K))
    out = []; j = 0
    for k in range(n + 1):
        s = L * k / n
        while j < len(P) - 2 and cum[j + 1] < s: j += 1
        seg = cum[j + 1] - cum[j] or 1; t = min(1, max(0, (s - cum[j]) / seg))
        out.append((P[j][0] + (P[j + 1][0] - P[j][0]) * t, P[j][1] + (P[j + 1][1] - P[j][1]) * t))
    return out

def wys(x, y):
    # interpolacja dwuliniowa w siatce (środki komórek)
    c = (x - X0) / STEP - .5; r = (Y1 - y) / STEP - .5
    c0, r0 = int(math.floor(c)), int(math.floor(r))
    if r0 < 0 or c0 < 0 or r0 + 1 >= Z.shape[0] or c0 + 1 >= Z.shape[1]: return None
    q = Z[r0:r0 + 2, c0:c0 + 2]
    if (q == ND).any():
        v = q[q != ND]; return float(v.mean()) / 10 if v.size else None
    fc, fr = c - c0, r - r0
    return float(q[0, 0] * (1 - fc) * (1 - fr) + q[0, 1] * fc * (1 - fr) + q[1, 0] * (1 - fc) * fr + q[1, 1] * fc * fr) / 10

W = {}; brak = 0
for s in ODC:
    zs = [wys(x, y) for x, y in probki(s[7])]
    if any(z is None for z in zs):
        ok = [z for z in zs if z is not None]
        if not ok: brak += 1; continue
        zs = [z if z is not None else sum(ok) / len(ok) for z in zs]
    dm = [round(z * 10) for z in zs]
    W[s[0]] = [dm[0]] + [b - a for a, b in zip(dm, dm[1:])]
js = "window.WYS=" + json.dumps({"k": K, "z": W}, separators=(",", ":")) + ";"
open(f"{OUT}/stan/wysokosci.js", "w").write(js)
wsz = [v / 10 for a in W.values() for v in np.cumsum(a)]
print(f"wysokości: {len(W)} odcinków ({brak} poza modelem), {min(wsz):.0f}–{max(wsz):.0f} m n.p.m., plik {len(js) / 1e6:.2f} MB")
