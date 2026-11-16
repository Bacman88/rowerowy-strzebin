"""Dane pomocnicze dla nawigacji „Jedź” (strona/jedz.html): które odcinki dróg leżą na trasach pokazowych,
a które wojewódzkie mają obok drogę rowerową (ciąg pieszo-rowerowy z pomiarów w uMap).
Wynik: <strona>/stan/jedz.js  →  window.JEDZ = {trasy: [id…], rower: [id…], chodnik: [id…], linie: [{typ: rower|chodnik, ll}], oceny: {id: stan}}
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
UF = [f for f in features(json.load(open(UMAP))) if f.get("geometry", {}).get("type") == "LineString"]
linia = lambda f: [(c[1], c[0]) for c in f["geometry"]["coordinates"]]
ciagi = [linia(f) for f in UF if f["properties"].get("Typ drogi") == "ciąg pieszo-rowerowy"]
chodniki = [linia(f) for f in UF if f["properties"].get("Typ drogi") == "chodnik pieszy"]
# 16.11.2026 (Bartosz): droga rowerowa wzdłuż DW 906 (ul. Lubliniecka) w Koszęcinie, po południowo-zachodniej stronie –
# od przystanku Koszęcin Lubliniecka do skrzyżowania z Powstańców Śląskich (nie ma jej jeszcze w uMap)
ciagi.append([(50.641757, 18.831126), (50.641477, 18.831766), (50.640997, 18.832936), (50.640227, 18.834846), (50.638967, 18.837916), (50.638377, 18.839386), (50.637997, 18.840336)])
# 16.11.2026 (Bartosz): droga rowerowa wzdłuż DW 908 (ul. Tarnogórska) w Kaletach-Miotku, po wschodniej stronie – od Orzeszkowej do Młyńskiej
ciagi.append([(50.55135, 18.956194), (50.55174, 18.956394), (50.552, 18.956534), (50.55275, 18.956924), (50.55287, 18.956984), (50.553, 18.957054), (50.55356, 18.957354), (50.55392, 18.957534), (50.55544, 18.958334), (50.55549, 18.958364), (50.5559, 18.958574), (50.55901, 18.960204)])
GLOWNE = {s[0] for s in ODC if s[1] in ("droga wojewódzka", "droga krajowa")}
R = [i for i in wybierz(Siatka(lines_xy(ciagi)), 25, .6) if i in GLOWNE] if ciagi else []
# szeroki chodnik wzdłuż DW (ludzie jeżdżą nim jako bezpieczniejszą alternatywą) – osobna lista: bez kary za DW, ale trochę wolniej
C = [i for i in wybierz(Siatka(lines_xy(chodniki)), 25, .6) if i in GLOWNE and i not in R] if chodniki else []

# linie do narysowania na mapach: wzdłuż osi drogi (co 10 m), odsunięte o ODSUN m na tę stronę, po której narysowano je w uMap
# (oś DW + pół jezdni ≈ 4–5 m – linia „przyklejona” do krawędzi drogi, nie po płotach)
ODSUN = 5
SEGXY = [[xy(s[7][i], s[7][i + 1]) for i in range(0, len(s[7]), 2)] for s in ODC if s[0] in set(R) | set(C)]
def rzut(p):
    best = None
    for ln in SEGXY:
        for a, b in zip(ln, ln[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
            t = 0 if not L2 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
            q = (a[0] + t * dx, a[1] + t * dy); d = math.dist(p, q)
            if best is None or d < best[0]: best = (d, q, (dx, dy))
    return best
def odsun(ll):
    P = [xy(*q) for q in ll]; pts = []
    for a, b in zip(P, P[1:]):
        n = max(1, int(math.dist(a, b) // 10)); pts += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n) for k in range(n)]
    pts.append(P[-1]); out = []
    for p in pts:
        r = rzut(p)
        if not r or r[0] > 40: q = p                                  # daleko od drogi – zostaw jak narysowano
        else:
            _, q0, (dx, dy) = r; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L, dx / L
            strona = 1 if (p[0] - q0[0]) * nx + (p[1] - q0[1]) * ny >= 0 else -1
            q = (q0[0] + strona * ODSUN * nx, q0[1] + strona * ODSUN * ny)
        lat = q[1] / 111200; out.append([round(lat, 6), round(q[0] / (111200 * math.cos(math.radians(lat))), 6)])
    # wygładzenie (średnia z sąsiadów) – rzut na załamania osi daje drobne ząbki
    return [out[0]] + [[round((out[i - 1][0] + out[i][0] + out[i + 1][0]) / 3, 6), round((out[i - 1][1] + out[i][1] + out[i + 1][1]) / 3, 6)] for i in range(1, len(out) - 1)] + [out[-1]]
LINIE = [{"typ": "rower", "ll": odsun(l)} for l in ciagi] + [{"typ": "chodnik", "ll": odsun(l)} for l in chodniki]
# 16.11.2026: drogi dla rowerów z OpenStreetMap – highway=cycleway oraz ciągi pieszo-rowerowe (footway/path z bicycle=designated);
# rysowane po swojej geometrii, a odcinki sieci, które nimi biegną, nawigacja traktuje jak drogę rowerową (preferowane)
OSMR = []
for f in json.load(open("../dane/osm_gmina.geojson"))["features"]:
    p = f["properties"]; g = f.get("geometry") or {}
    if g.get("type") not in ("LineString", "MultiLineString") or p.get("bicycle") in ("no", "dismount"): continue
    if not (p.get("highway") == "cycleway" or (p.get("highway") in ("footway", "path") and p.get("bicycle") == "designated")): continue
    for part in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
        if len(part) > 1: OSMR.append([[round(lat, 6), round(lon, 6)] for lon, lat in part])
R_OSM = [i for i in wybierz(Siatka(lines_xy(OSMR)), 6, .8) if i not in set(R)] if OSMR else []
R = R + R_OSM
LINIE += [{"typ": "rower", "osm": 1, "ll": ln} for ln in OSMR]

# 16.11.2026: szlaki rowerowe z OSM (Leśno Rajza, Liswarciański) – nawigacja „do szlaku” prowadzi do najbliższego punktu samego szlaku
SZLAKI = []
for f in json.load(open("../dane/osm2_clean.geojson"))["features"]:
    p = f["properties"]; nz = p.get("name") or ""
    if p.get("route") != "bicycle" or not (p.get("ref") == "LR" or "Liswarcia" in nz): continue
    g = f["geometry"]; parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
    linie = []
    for part in parts:
        ln = []
        for lon, lat in part:   # co ~40 m wystarczy do szukania najbliższego punktu
            if not ln or math.dist(xy(lat, lon), xy(*ln[-1])) > 40: ln.append([round(lat, 5), round(lon, 5)])
        if len(ln) > 1: linie.append(ln)
    SZLAKI.append({"n": "Leśno Rajza" if p.get("ref") == "LR" else "Liswarciański Szlak Rowerowy", "linie": linie})

# zatwierdzone oceny dróg z mapy wspólnej (migawka z api/stan.php: id odcinka → stan) – działają od pierwszego uruchomienia, także bez sieci;
# świeże oceny aplikacja i tak dociąga z serwera przy starcie
import os
OCENY = json.load(open("../dane/oceny_mapa.json")) if os.path.exists("../dane/oceny_mapa.json") else {}
open(f"{OUT}/stan/jedz.js", "w").write("window.JEDZ=" + json.dumps({"trasy": T, "rower": R, "chodnik": C, "linie": LINIE, "oceny": OCENY, "szlaki": SZLAKI}, separators=(",", ":")) + ";")
km = lambda ids: sum(s[6] for s in ODC if s[0] in set(ids)) / 1000
print(f"jedź: odcinki na trasach {len(T)} ({km(T):.0f} km), z drogą rowerową (DW obok ścieżki + ścieżki z OSM) {len(R)} ({km(R):.1f} km), z szerokim chodnikiem {len(C)} ({km(C):.1f} km), linii na mapę {len(LINIE)}")
