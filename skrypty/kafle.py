"""Kafle odcinków dla strony (17.11.2026, etap 1).

Z pełnego stan/odcinki.js (który dalej zostaje dla Jedź, panelu i planera tras) robi:
  stan/przeglad.js        – window.ODCP: wszystkie odcinki w wersji uproszczonej (id, stan z pomiaru, długość, kształt
                            uproszczony do ~15 m, współrzędne różnicowo w 1e-5 stopnia) + window.ODC_ALIASY;
                            wystarcza do rysowania całej mapy, kolorów ocen i sum kilometrów
  stan/kafle/X_Y.json     – pełne dane odcinków (nazwa, typ, nawierzchnia, dokładny kształt) w kaflu ~4,4 × 4,2 km;
                            odcinek należy do kafla, w którym leży jego pierwszy punkt (ten sam w obu wersjach)
Strona dociąga kafle dopiero po przybliżeniu (zoom ≥ 13) albo przy kliknięciu odcinka.
Użycie: python3 kafle.py <katalog strony>
"""
import hashlib, json, os, shutil, sys

from shapely.geometry import LineString

OUT = sys.argv[1]
LAT0, LON0, DLAT, DLON = 50.0, 18.0, 0.04, 0.06   # siatka kafli (stała – nie zależy od obszaru mapy)
TOL = 0.00015                                       # uproszczenie kształtu w warstwie przeglądowej (~15 m)

src = open(os.path.join(OUT, "stan", "odcinki.js"), encoding="utf-8").read()
dec = json.JSONDecoder()
i = src.index("window.ODC=") + len("window.ODC=")
ODC, e = dec.raw_decode(src[i:])
aliasy = {}
j = src.find("window.ODC_ALIASY=")
if j >= 0: aliasy, _ = dec.raw_decode(src[j + len("window.ODC_ALIASY="):])


def kafel(lat, lon):
    return f"{int((lon - LON0) // DLON)}_{int((lat - LAT0) // DLAT)}"


def delta(pts):
    out, pa, pb = [], 0, 0
    for la, lo in pts:
        a, b = round(la * 1e5), round(lo * 1e5)
        out += [a - pa, b - pb]; pa, pb = a, b
    return out


kafle, prz = {}, []
for s in ODC:
    c = s[7]; pts = [(c[k], c[k + 1]) for k in range(0, len(c), 2)]
    kafle.setdefault(kafel(*pts[0]), []).append(s)
    up = list(LineString(pts).simplify(TOL, preserve_topology=False).coords) if len(pts) > 2 else pts
    if up[0] != pts[0]: up[0] = pts[0]           # pierwszy punkt bez zmian – wyznacza kafel
    # [id, stan z pomiaru, długość, droga rowerowa?, kształt]
    prz.append([s[0], s[4], s[6], 1 if s[5] == "droga rowerowa" else 0, delta(up)])

kat = os.path.join(OUT, "stan", "kafle")
shutil.rmtree(kat, ignore_errors=True); os.makedirs(kat)
for k, lista in kafle.items():
    with open(os.path.join(kat, k + ".json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, separators=(",", ":"))

ver = hashlib.sha1(src.encode()).hexdigest()[:8]
dane = {"v": ver, "siatka": [LAT0, LON0, DLAT, DLON], "kafle": sorted(kafle), "o": prz}
with open(os.path.join(OUT, "stan", "przeglad.js"), "w", encoding="utf-8") as f:
    f.write("window.ODCP=" + json.dumps(dane, ensure_ascii=False, separators=(",", ":")) + ";\n")
    f.write("window.ODC_ALIASY=" + json.dumps(aliasy, ensure_ascii=False, separators=(",", ":")) + ";\n")
print(f"kafle: {len(ODC)} odcinków w {len(kafle)} kaflach, przegląd {os.path.getsize(os.path.join(OUT, 'stan', 'przeglad.js')) // 1024} kB")
