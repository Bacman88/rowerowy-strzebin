"""Dane pomocnicze dla nawigacji „Jedź” (strona/jedz.html): które odcinki dróg leżą na trasach pokazowych,
a które wojewódzkie mają obok drogę rowerową (ciąg pieszo-rowerowy z pomiarów w uMap).
Wynik: <strona>/stan/jedz.js  →  window.JEDZ = {trasy: [id…], rower: [id…]}
Użycie (po odcinki.py): python3 jedz_dane.py ../dane/umap_mapa_rowerowa.geojson ../out/strona
"""
import json, math, sys

UMAP, OUT = sys.argv[1:3]
txt = open(f"{OUT}/stan/odcinki.js").read()
ODC = json.loads(txt[txt.index("=") + 1:txt.index(";\nwindow.ODC_ALIASY")])
dj = open(f"{OUT}/data.js").read()
H = json.loads(dj[dj.index("=") + 1:].strip().rstrip(";"))

def xy(lat, lon): return (lon * 111200 * math.cos(math.radians(lat)), lat * 111200)
def lines_xy(lines): return [[xy(a, b) for a, b in ln] for ln in lines]
def dseg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
    t = 0 if not L2 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

class Siatka:
    """Odcinki linii w siatce 100 m – szybkie „czy punkt leży do r metrów od linii”."""
    def __init__(self, lines):
        self.g = {}
        for ln in lines:
            for a, b in zip(ln, ln[1:]):
                for gx in range(int(min(a[0], b[0]) // 100) - 1, int(max(a[0], b[0]) // 100) + 2):
                    for gy in range(int(min(a[1], b[1]) // 100) - 1, int(max(a[1], b[1]) // 100) + 2):
                        self.g.setdefault((gx, gy), []).append((a, b))
    def blisko(self, p, r):
        return any(dseg(p, a, b) <= r for a, b in self.g.get((int(p[0] // 100), int(p[1] // 100)), []))

def punkty(s, co=25):
    """Punkty odcinka co ok. 25 m (bez samych końców – tam stykają się z innymi drogami)."""
    c = s[7]; ll = [(c[i], c[i + 1]) for i in range(0, len(c), 2)]; P = [xy(*q) for q in ll]; out = []
    for a, b in zip(P, P[1:]):
        n = max(1, int(math.dist(a, b) // co))
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    out.append(P[-1])
    return out[1:-1] or out

def wybierz(siatka, r, udzial):
    ids = []
    for s in ODC:
        pts = punkty(s)
        if sum(siatka.blisko(p, r) for p in pts) >= udzial * len(pts): ids.append(s[0])
    return ids

trasy = [[(q[0], q[1]) for q in part["c"]] for r in H["routes"] if not r.get("alt") for part in r["parts"]]
T = wybierz(Siatka(lines_xy(trasy)), 18, .7)

def features(o):
    if isinstance(o, dict):
        if o.get("type") == "Feature": yield o
        else:
            for v in o.values(): yield from features(v)
    elif isinstance(o, list):
        for v in o: yield from features(v)
ciagi = [[(c[1], c[0]) for c in f["geometry"]["coordinates"]] for f in features(json.load(open(UMAP)))
         if f.get("geometry", {}).get("type") == "LineString" and f["properties"].get("Typ drogi") == "ciąg pieszo-rowerowy"]
R = [i for i in wybierz(Siatka(lines_xy(ciagi)), 25, .6) if i in {s[0] for s in ODC if s[1] in ("droga wojewódzka", "droga krajowa")}] if ciagi else []

open(f"{OUT}/stan/jedz.js", "w").write("window.JEDZ=" + json.dumps({"trasy": T, "rower": R}, separators=(",", ":")) + ";")
km = lambda ids: sum(s[6] for s in ODC if s[0] in set(ids)) / 1000
print(f"jedź: odcinki na trasach {len(T)} ({km(T):.0f} km), DW z drogą rowerową obok {len(R)} ({km(R):.1f} km)")
