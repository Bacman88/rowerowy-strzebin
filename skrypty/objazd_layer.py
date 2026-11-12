# Odcinki do sprawdzenia w terenie (wywoływane z trasy.py --objazd)
import xml.sax.saxutils as _x
SEGS = [  # id, priorytet, ciąg punktów, opis, uwaga Bartosza
    ("A", 1, ["Sośnica", 52], "Sośnica – słupek 52", "początek trasy 1; leśny wyjazd z Sośnicy"),
    ("B", 1, [52, 53, 48, 29, 22, 47], "las Sośnica – Piasek – Bukowiec (52–53–48–29–22–47)", "trasa 1 – kluczowe dla obwodnicy DW 906"),
    ("C", 2, [52, 34], "52 – 34 (las w stronę Kalet)", "trasy 8 i 9"),
    ("D", 2, ["Drutarnia", 40, 41], "Drutarnia – 40 – 41", "trasa 7 (i 9 na odcinku 40–41)"),
    ("E", 2, ["Babienica", 49], "Babienica – Łazy (49)", "trasa 5; nie wiadomo, czy jechane"),
    ("F", 2, [2, 39, 38, 37, 36], "Spokojna – las – kościół św. Trójcy (2–39–38–37–36)", "trasy 4 i 6; przejezdne, podobno piach"),
    ("G", 3, [28, 22], "28 – 22 (las między trasami 2 i 1)", "łącznik, bez trasy"),
    ("H", 3, [1, 15], "Prądy (1) – 15", "jechane – sprawdzić, czy stan się poprawił"),
    ("I", 3, [45, 44, 43], "Czajcze Bagno – Lipowiec – Łazy (45–44–43)", "możliwe tereny prywatne; opinie sprzeczne"),
]
PCOL = {1: "#d62828", 2: "#f08c00", 3: "#7e22ce"}
PLAB = {1: "priorytet 1 – przed spotkaniem z gminą", 2: "priorytet 2 – trasy pokazowe", 3: "priorytet 3 – łączniki i słupki opcjonalne"}
SEGRES = []
for sid, pr_, sq, opis, uw in SEGS:
    path = [ep(sq[0])]
    for a, b in zip(sq, sq[1:]): path += nx.shortest_path(G, ep(a), ep(b), weight="c")[1:]
    L = sum(G[u][v]["w"] for u, v in zip(path, path[1:])); pv = sum(G[u][v]["w"] for u, v in zip(path, path[1:]) if is_paved(G[u][v]["pr"]))
    gv = sum(G[u][v]["w"] for u, v in zip(path, path[1:]) if is_gravel(G[u][v]["pr"]))
    SEGRES.append(dict(id=sid, pr=pr_, opis=opis, uw=uw, path=path, km=L / 1000, pav=pv / L, grv=gv / L))
    ln = LineString([P(n) for n in path])
    gpd.GeoSeries([ln]).plot(ax=ax, color="white", lw=lw(2.6), zorder=12, capstyle="round", joinstyle="round")
    gpd.GeoSeries([ln]).plot(ax=ax, color=PCOL[pr_], lw=lw(1.7), zorder=12.5, capstyle="round", joinstyle="round")
    m = ln.interpolate(0.5, normalized=True)
    ax.text(m.x, m.y, sid, ha="center", va="center", fontsize=11, weight="bold", color="white", zorder=26,
            bbox=dict(boxstyle="round,pad=0.35", fc=PCOL[pr_], ec="white", lw=1.6))
# panel (jasny)
pan = fig.add_axes([0, 0, PANEL / PW, 1]); pan.set_axis_off(); pan.set_xlim(0, PANEL); pan.set_ylim(0, PH)
pan.add_patch(Rectangle((0, 0), PANEL, PH, color="#f7f4ec")); pan.plot([PANEL - 0.6, PANEL - 0.6], [0, PH], color="#1d3b30", lw=lw(0.8))
T = lambda x, y, s, **k: pan.text(x, y, s, color=k.pop("color", "#1d2a23"), **k)
M = 12
T(M, 398, "SOŁECTWO STRZEBIŃ · HUB ROWEROWY", fontsize=12, weight="bold", color="#8a5300")
T(M, 390, "Objazd kontrolny\ndróg", fontsize=27, weight="bold", va="top", linespacing=1.05)
T(M, 352, "Odcinki, którymi trasy prowadzą wg map, a które trzeba przejechać.\nPrzy każdym zaznacz: przejezdne / średnio / nieprzejezdne.", fontsize=9.2, va="top", color="#4b5d53", linespacing=1.45)
y = 330
for pr_ in (1, 2, 3):
    T(M, y, PLAB[pr_].upper(), fontsize=9, weight="bold", color=PCOL[pr_]); y -= 8
    for r in [r for r in SEGRES if r["pr"] == pr_]:
        pan.text(M + 4, y - 1, r["id"], ha="center", va="center", fontsize=10, weight="bold", color="white", bbox=dict(boxstyle="round,pad=0.3", fc=PCOL[pr_], ec="white"))
        T(M + 11, y, r["opis"], fontsize=9.6, weight="bold", va="center"); y -= 5.6
        T(M + 11, y, f"{r['km']:.1f} km · asfalt {r['pav']*100:.0f}% · szuter {r['grv']*100:.0f}% · grunt {100 - (r['pav'] + r['grv'])*100:.0f}% (OSM)".replace(".", ",", 1),
          fontsize=8.4, va="center", color="#4b5d53"); y -= 5.2
        T(M + 11, y, r["uw"], fontsize=8.4, va="center", color="#2c3a32", style="italic"); y -= 5.2
        T(M + 11, y, "☐ przejezdne     ☐ średnio     ☐ nieprzejezdne", fontsize=8.6, va="center", color="#1d2a23", family="DejaVu Sans"); y -= 9
    y -= 3
tot = sum(r["km"] for r in SEGRES)
T(M, y, f"Razem ok. {tot:.0f} km odcinków (bez dojazdów). Pliki GPX: osobno każdy odcinek.".replace(".", ",", 0), fontsize=8.6, color="#4b5d53"); y -= 7
T(M, 6, "Dane mapy © autorzy OpenStreetMap (ODbL)", fontsize=7.5, color="#4b5d53")
exec(open("labels.py").read()); declutter(fig, ax, PLACE_T)
fig.savefig(OUT + "_objazd.pdf")
# GPX
inv_ = Transformer.from_crs(2180, 4326, always_xy=True) if "Transformer" in dir() else None
import os
from pyproj import Transformer as _T
_inv = _T.from_crs(2180, 4326, always_xy=True)
gd = os.path.dirname(OUT) + "/objazd_gpx"; os.makedirs(gd, exist_ok=True)
def gpx(rs):
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="HUB Strzebin" xmlns="http://www.topografix.com/GPX/1/1">']
    for r in rs:
        out.append(f"<trk><name>{_x.escape(r['id'] + ' – ' + r['opis'])}</name><desc>{_x.escape(r['uw'])}</desc><trkseg>")
        for n in r["path"]: out.append(f'<trkpt lat="{n[1]:.7f}" lon="{n[0]:.7f}"/>')
        out.append("</trkseg></trk>")
    out.append("</gpx>"); return "\n".join(out)
for r in SEGRES: open(f"{gd}/{r['id']}_priorytet{r['pr']}.gpx", "w").write(gpx([r]))
open(f"{gd}/wszystkie_odcinki.gpx", "w").write(gpx(SEGRES))
print("ok objazd", [(r["id"], round(r["km"], 1)) for r in SEGRES])
