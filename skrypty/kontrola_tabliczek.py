"""Kontrola kompletności tabliczek: czy z każdego słupka każdy kierunek trasy pokazowej i każda droga do sąsiedniego
węzła ma tabliczkę. Wynik: ../out/kontrola_tabliczek.csv + podsumowanie na ekranie.
Użycie: python3 kontrola_tabliczek.py <signs_prop.json> <drogowskazy_trasy.geojson> [--sasiedzi]"""
import json, math, sys, csv, collections
from pyproj import Transformer
tf = Transformer.from_crs(4326, 2180, always_xy=True); P = lambda c: tf.transform(*c)
SIGNS, TR = sys.argv[1:3]
D = json.load(open(SIGNS)); routes = json.load(open(TR))["features"]
close = lambda a, b, t=35: abs((a - b + 180) % 360 - 180) <= t
def brg(a, b): return (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360
def kierunki_trasy(xy, post):
    """kierunki (azymut) trasy wychodzące ze słupka: punkt 80 m dalej w obie strony od najbliższego wierzchołka"""
    d = [math.dist(q, post) for q in xy]; i = min(range(len(xy)), key=d.__getitem__)
    if d[i] > 40: return []
    out = []
    for step in (1, -1):
        j, acc = i, 0
        while 0 <= j + step < len(xy) and acc < 80: acc += math.dist(xy[j], xy[j + step]); j += step
        if acc > 20: out.append(brg(xy[i], xy[j]))
    return out
DIR8 = ["płn.", "płn.-wsch.", "wsch.", "płd.-wsch.", "płd.", "płd.-zach.", "zach.", "płn.-zach."]
from pyproj import Geod
geod = Geod(ellps="WGS84"); m_ = lambda a, b: geod.inv(a[0], a[1], b[0], b[1])[2]
R = [(f["properties"]["id"], [tuple(round(v, 7) for v in c) for c in f["geometry"]["coordinates"]]) for f in routes]
def pokrywa(pl, rc, i, step):
    """tabliczka prowadzi trasą w tym kierunku: ścieżka zawiera krawędź trasy (i -> i+step) blisko słupka
    i dalej jedzie trasą co najmniej min(1 km, 60% drogi do celu) – tak samo jak kółka tras"""
    path = [tuple(round(v, 7) for v in q) for q in (pl.get("path") or [])]
    if len(path) < 2: return False
    e = (rc[i], rc[i + step]); total = sum(m_(a, b) for a, b in zip(path, path[1:]))
    for k in range(min(10, len(path) - 1)):
        if (path[k], path[k + 1]) == e:
            run, j = 0, i; kk = k
            while kk < len(path) - 1 and 0 <= j + step < len(rc) and (path[kk], path[kk + 1]) == (rc[j], rc[j + step]):
                run += m_(rc[j], rc[j + step]); j += step; kk += 1
            return run >= min(1000, 0.6 * total) - 1 or kk == len(path) - 1
    return False
rows = []; braki = collections.Counter()
for p in D["posts"]:
    pxy = P((p["lon"], p["lat"]))
    for rid, rc in R:
        xy = [P(c) for c in rc]; d = [math.dist(q, pxy) for q in xy]; i = min(range(len(xy)), key=d.__getitem__)
        if d[i] > 40: continue
        for step in (1, -1):
            if not (0 <= i + step < len(rc)): continue
            j, acc = i, 0
            while 0 <= j + step < len(rc) and acc < 300: acc += m_(rc[j], rc[j + step]); j += step
            if acc < 150: continue   # trasa tu się kończy
            if not any(pokrywa(pl, rc, i, step) for pl in p["plates"]):
                dg = brg(xy[i], xy[j])
                rows.append([p["nr"], p["loc"], f"trasa {rid}", DIR8[int((dg + 22.5) // 45) % 8], round(dg), ", ".join(pl["name"] for pl in p["plates"])])
                braki[p["nr"]] += 1
# zduplikowane kierunki (trasa 1 i 1a, kilka tras tą samą drogą) – jeden wiersz na słupek i kierunek
seen, uniq = set(), []
for r in rows:
    k = (r[0], r[3])
    if k in seen: continue
    seen.add(k); uniq.append(r)
with open("../out/kontrola_tabliczek.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["Słupek", "Lokalizacja", "Trasa", "Kierunek bez tabliczki", "Azymut", "Tabliczki na słupku"]); w.writerows(uniq)
print("kontrola tabliczek:", len(uniq), "kierunków tras bez tabliczki na", len({r[0] for r in uniq}), "słupkach")
for r in uniq: print(f"  {r[0]:>2} {r[3]:<11} ({r[2]}) | ma: {r[5]}")
