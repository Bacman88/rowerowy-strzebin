# Warstwa infrastruktury turystycznej (wykonywana wewnątrz trasy.py przy --infra)
import subprocess, re as _re, tempfile
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
TAB = "../generator/piktogramy_tabler/"
CATS = [  # klucz, ikona, kolor, opis
    ("rest", "rest", "#237647", "wiata / miejsce odpoczynku"),
    ("view", "view", "#6b3fa0", "punkt widokowy"),
    ("sight", "heritage", "#81552F", "ciekawe miejsce"),
    ("bed", "bed", "#B96516", "nocleg"),
    ("food", "restaurant", "#902B38", "gastronomia"),
    ("bikep", "bikeparking", "#0759A7", "stojak rowerowy"),
    ("park", "parking", "#3d6fb0", "parking"),
    ("info", "information", "#505C66", "tablica informacyjna"),
    ("service", "service", "#505C66", "stacja napraw rowerów (fundusz sołecki 2027)"),
]
CC = {c[0]: c for c in CATS}
def cat_of(pr):
    a, t = pr.get("amenity"), pr.get("tourism")
    if a == "shelter" and pr.get("shelter_type") != "public_transport": return "rest"
    if t == "picnic_site": return "rest"
    if t == "viewpoint" or (t == "attraction" and "widok" in (pr.get("name") or "").lower()): return "view"
    if t in ("attraction", "artwork"): return "sight"
    if t in ("hotel", "hostel", "guest_house", "motel", "chalet", "camp_site"): return "bed"
    if a in ("restaurant", "biergarten", "cafe", "fast_food", "pub", "bar"): return "food"
    if a == "bicycle_parking": return "bikep"
    if a == "parking": return "park"
    if t == "information" and pr.get("information") != "guidepost": return "info"
    return None
from shapely.geometry import shape as _shape
IT = []
for f in osm:
    k = cat_of(f["properties"])
    if not k: continue
    g_ = _shape(f["geometry"]); c_ = g_.centroid if g_.geom_type != "Point" else g_
    x, y = P((c_.x, c_.y)); IT.append((k, x, y, f["properties"].get("name")))
for poi in D.get("pois", []):
    if poi.get("icon") == "service":
        x, y = P((poi["lon"], poi["lat"])); IT.append(("service", x, y, "Stacja napraw"))
vx0 = x0 + PANEL / 1000 * SCALE
IT = [it for it in IT if vx0 + 200 < it[1] < x1 - 200 and y0 + 200 < it[2] < y1 - 200]
keep = []
for it in IT:                                   # scal duble tej samej kategorii (<120 m)
    if any(k_[0] == it[0] and math.hypot(k_[1] - it[1], k_[2] - it[2]) < 120 for k_ in keep): continue
    keep.append(it)
IT = keep
from svgpath2mpl import parse_path
from matplotlib.patches import Circle, PathPatch
from matplotlib.path import Path as MPath
from matplotlib.transforms import Affine2D
BIKE = ['M2 18a3 3 0 1 0 6 0a3 3 0 1 0 -6 0', 'M16 18a3 3 0 1 0 6 0a3 3 0 1 0 -6 0', 'M12 19l0 -4l-3 -3l5 -4l2 3l3 0', 'M17 5a1 1 0 1 0 2 0a1 1 0 1 0 -2 0']
_PTH = {}
def icon_paths(k):
    if k in _PTH: return _PTH[k]
    if k == "bikep": ds = BIKE
    else: ds = _re.findall(r'<path d="([^"]+)"', open(TAB + CC[k][1] + ".svg").read())
    _PTH[k] = [parse_path(d) for d in ds]; return _PTH[k]
def draw_icon(a_, k, x, y, d, z=23):
    """Wektorowa ikona: koło o średnicy d (jednostki osi) + piktogram Tabler jako linie."""
    col = CC[k][2]; r_ = d / 2
    a_.add_patch(Circle((x, y), r_, facecolor=col, edgecolor="white", lw=lw(d / (m2 if a_ is ax else 1) * 0.07), zorder=z))
    s_ = d * 0.78 / 24
    T_ = Affine2D().translate(-12, -12).scale(s_, -s_).translate(x, y)
    for pth in icon_paths(k):
        a_.add_patch(PathPatch(T_.transform_path(pth), facecolor="none", edgecolor="white", lw=lw(d / (m2 if a_ is ax else 1) * 0.78 / 24 * 2.2),
                               capstyle="round", joinstyle="round", zorder=z + 0.5))
m2 = SCALE / 1000            # metry terenu na 1 mm papieru
D_MAP = 5.6 * m2
order = {c[0]: i for i, c in enumerate(CATS)}
_tx, _ty = P(TROJCA)
OBST = [P((p_["lon"], p_["lat"])) for p_ in D["posts"]] + [(_tx, _ty)] + [(_tx + dx, _ty - dy) for dx in (-250, 0, 250) for dy in (420, 650)]
PLACED = []
for k, x, y, nm in sorted(IT, key=lambda t: order[t[0]]):
    free = lambda px, py: all(math.hypot(px - q[0], py - q[1]) > 1.05 * D_MAP for q in OBST + PLACED)
    if not free(x, y):          # odsuń ikonę, gdy nachodzi na słupek, kościół albo inną ikonę
        for rr in (1.15, 1.6, 2.1):
            hit = next(((x + rr * D_MAP * math.cos(math.radians(a_)), y + rr * D_MAP * math.sin(math.radians(a_)))
                        for a_ in range(0, 360, 30) if free(x + rr * D_MAP * math.cos(math.radians(a_)), y + rr * D_MAP * math.sin(math.radians(a_)))), None)
            if hit: x, y = hit; break
    PLACED.append((x, y))
    draw_icon(ax, k, x, y, D_MAP, z=23 + (1 if k == "service" else 0))
# panel
pan = fig.add_axes([0, 0, PANEL / PW, 1]); pan.set_axis_off(); pan.set_xlim(0, PANEL); pan.set_ylim(0, PH)
pan.add_patch(Rectangle((0, 0), PANEL, PH, color="#1d3b30"))
T = lambda x, y, s, **k: pan.text(x, y, s, color=k.pop("color", "#f3efe4"), **k)
M = 12
T(M, 398, "SOŁECTWO STRZEBIŃ · HUB ROWEROWY", fontsize=12, weight="bold", color="#e9b949")
T(M, 390, "Miejsca odpoczynku\ni infrastruktura", fontsize=27, weight="bold", va="top", linespacing=1.05)
T(M, 352, "Wiaty, punkty widokowe, noclegi, gastronomia i parkingi przy proponowanych\ntrasach – to, co już jest w terenie. Oznakowanie HUB-u może do nich prowadzić.", fontsize=9.2,
  va="top", color="#a9c0b2", linespacing=1.45)
y = 326
cnt = collections.Counter(it[0] for it in IT)
for k, ic, col, lab in CATS:
    if not cnt[k]: continue
    draw_icon(pan, k, M + 5, y, 7.5)
    T(M + 15, y, lab, fontsize=11, va="center"); T(PANEL - M, y, str(cnt[k]), fontsize=11, va="center", ha="right", color="#e9b949", weight="bold")
    y -= 12
y -= 4
named = sorted({(CC[k][3], nm) for k, x, y_, nm in IT if nm and k in ("view", "sight", "bed", "rest")})
if named:
    T(M, y, "WARTO ZOBACZYĆ / ZATRZYMAĆ SIĘ", fontsize=9, weight="bold", color="#e9b949"); y -= 8
    for lab, nm in named[:12]:
        T(M, y, f"• {nm}", fontsize=8.8, va="center"); T(M + 4, y - 5, lab, fontsize=7.8, va="center", color="#a9c0b2"); y -= 11
y -= 4
for r in RES:
    if r["alt"]: continue
    pan.plot([M, M + 10], [y, y], color=r["c"], lw=lw(1.6), alpha=0.6)
    T(M + 14, y, f"trasa {r['id']} – {r['name']}", fontsize=8.2, va="center", color="#cfd9d1"); y -= 6
y -= 4
T(M, y, "Trasy pokazano półprzezroczyście – szczegóły na mapie tras.\nObiekty według OpenStreetMap (stan 2026) – lista niepełna, do uzupełnienia\no ławki i parkingi leśne z terenu i od nadleśnictw.", fontsize=8, va="top", color="#a9c0b2", linespacing=1.45)
T(M, 6, "Dane mapy © autorzy OpenStreetMap (ODbL) · piktogramy Tabler Icons (MIT)", fontsize=7.5, color="#a9c0b2")
exec(open("labels.py").read()); declutter(fig, ax, PLACE_T)
fig.savefig(OUT + "_infrastruktura.pdf"); fig.savefig(OUT + "_infrastruktura_podglad.png", dpi=60)
print("ok infra", dict(cnt))
