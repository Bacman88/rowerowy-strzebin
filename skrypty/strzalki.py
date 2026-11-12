"""Strzałki tabliczek (← / →) dobierane osobno dla każdego słupka.

Tabliczka jest dwustronna i obraca się na słupku w stronę swojej drogi, więc ← / → to umowa: wszystkie drogi
po jednej stronie umownej „osi” słupka dostają →, po drugiej ←. Wcześniej oś była wspólna (wschód i północ →),
przez co dwa kierunki tej samej trasy (np. na słupku 25: Kalety na południe, Boronów na zachód) miały tę samą strzałkę.

Teraz oś dobieramy tak, żeby:
  1. wejście i wyjście każdej trasy pokazowej przez słupek miały przeciwne strzałki,
  2. żaden kierunek nie leżał tuż przy osi (min. 12°),
  3. przy remisie – jak najbliżej dawnej umowy (wschód →).
Wynik: pole „os” słupka i „strona” każdego celu w signs_prop.json (czytają je plates.py, signs_render.py i strona).
Użycie: python3 strzalki.py signs_prop.json ../out/drogowskazy_trasy.geojson
"""
import json, math, sys
from pyproj import Transformer

PROP, TRASY = sys.argv[1:3]
tf = Transformer.from_crs(4326, 2180, always_xy=True)
D = json.load(open(PROP))
OS0 = 340          # dawna umowa: → dla kierunków od ok. 340° do 160° (północ i wschód)

def bearing(a, b): return (math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])) + 360) % 360
def adiff(a, b): return abs((a - b + 180) % 360 - 180)
def strona(deg, os_): return "right" if 0 < (deg - os_) % 360 < 180 else "left"

# przebiegi tras (bez wariantów) w układzie metrycznym
trasy = []
for f in json.load(open(TRASY))["features"]:
    if str(f["properties"].get("alt")) == "True": continue
    trasy.append((f["properties"]["id"], [tf.transform(*c) for c in f["geometry"]["coordinates"]]))

def wyjscia(xy, line, m=80):
    """Kierunki trasy od słupka: do tyłu i do przodu (punkt ok. 80 m po trasie). None, gdy słupek jest na końcu."""
    i = min(range(len(line)), key=lambda k: math.dist(line[k], xy))
    if math.dist(line[i], xy) > 30: return None
    def idz(step):
        acc, k, last = 0, i, line[i]
        while 0 <= k + step < len(line):
            k += step; acc += math.dist(last, line[k]); last = line[k]
            if acc >= m: break
        return last if acc > 15 else None
    a, b = idz(-1), idz(1)
    if not a or not b: return None
    return bearing(xy, a), bearing(xy, b)

zm = 0
for p in D["posts"]:
    xy = tf.transform(p["lon"], p["lat"])
    dirs = sorted({round(pl["deg"]) for pl in p["plates"] if pl.get("deg") is not None})
    pary = []
    for rid, line in trasy:
        w = wyjscia(xy, line)
        if w and adiff(*w) > 60: pary.append(w)
    best = None
    for os_ in range(0, 360, 2):
        sat = sum(strona(a, os_) != strona(b, os_) for a, b in pary)
        marg = min([min(adiff(d, os_), adiff(d, os_ + 180)) for d in dirs] or [90])
        key = (sat, min(marg, 12), -adiff(os_, OS0))
        if best is None or key > best[0]: best = (key, os_)
    os_ = best[1]
    p["os"] = os_
    for pl in p["plates"]:
        if pl.get("deg") is None: continue
        s_ = strona(pl["deg"], os_)
        if s_ != strona(pl["deg"], OS0): zm += 1
        pl["strona"] = s_
json.dump(D, open(PROP, "w"), ensure_ascii=False)
print(f"strzałki: oś dobrana dla {len(D['posts'])} słupków, {zm} celów zmieniło stronę względem dawnej umowy")
