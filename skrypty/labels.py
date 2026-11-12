HIDDEN = []
DEBUG_LBL = None
"""Usuwanie nakładających się podpisów miejscowości (prosty algorytm zachłanny)."""
from matplotlib.transforms import Bbox

def _ext(t, r):
    bp = t.get_bbox_patch()
    return (bp.get_window_extent(r) if bp is not None else t.get_window_extent(r)).expanded(1.05, 1.05)

def _ov(a, b, tol=12):
    w = min(a.x1, b.x1) - max(a.x0, b.x0); h = min(a.y1, b.y1) - max(a.y0, b.y0)
    return w > 3 and h > 3 and w * h > tol

def place_beside(fig, ax, items, gap_px=None, pad=1, extra=(), hide=False):
    """items: lista (Text, x_gwiazdki, y_gwiazdki). Podpis na wysokości gwiazdki – z prawej, a gdy zajęte, z lewej,
    dalej w bok (za ikoną), w ostateczności nad lub pod gwiazdką. Nazwy ulic przeszkadzają mniej niż słupki i ikony."""
    r = fig.canvas.get_renderer(); mine = {it[0] for it in items}
    taken = []                                 # (bbox, waga)
    for t in ax.texts:
        if t in mine or not t.get_visible(): continue
        try:
            minor = t.get_bbox_patch() is None and (t.get_fontsize() <= 7.5 or (t.get_rotation() % 180) not in (0.0,))
            taken.append((_ext(t, r), 0.3 if minor else 1.0))
        except Exception: pass
    for a in ax.artists:                      # ikony (klucze stacji napraw)
        try: taken.append((a.get_window_extent(r), 1.0))
        except Exception: pass
    for ex, ey, er in extra:                  # dodatkowe przeszkody w jednostkach osi (x, y, promień)
        (X0, Y0), (X1, Y1) = ax.transData.transform([(ex - er, ey - er), (ex + er, ey + er)])
        taken.append((Bbox.from_extents(X0, Y0, X1, Y1), 1.0))
    NAMES = [x.get_text() for x in ax.texts if x not in mine and x.get_visible()] + ['<ikona>'] * len(ax.artists)
    inv = ax.transData.inverted()
    for t, xs, ys in items:
        X, Y = ax.transData.transform((xs, ys))
        g = gap_px or t.get_fontsize() * fig.dpi / 72 * 0.95
        h = t.get_window_extent(r).height
        best = None
        cands = ((g, 0, "left", "center"), (-g, 0, "right", "center"),
                 (g, -0.5 * h, "left", "center"), (-g, -0.5 * h, "right", "center"),
                 (g, 0.5 * h, "left", "center"), (-g, 0.5 * h, "right", "center"),
                 (3.2 * g, 0, "left", "center"), (-3.2 * g, 0, "right", "center"),
                 (5.5 * g, 0, "left", "center"), (-5.5 * g, 0, "right", "center"),
                 (0, 0.9 * g + h / 2, "center", "center"), (0, -0.9 * g - h / 2, "center", "center"))
        for i, (dx, dy, ha, va) in enumerate(cands):
            t.set_ha(ha); t.set_va(va); t.set_position(inv.transform((X + dx, Y + dy)))
            b = t.get_window_extent(r); b = Bbox.from_extents(b.x0 - pad, b.y0 - pad, b.x1 + pad, b.y1 + pad)
            sc = sum(w for o, w in taken if _ov(b, o)) + 0.12 * i
            if DEBUG_LBL and t.get_text() == DEBUG_LBL: print(i, round(sc, 2), [(round(min(b.x1,o.x1)-max(b.x0,o.x0),1), round(min(b.y1,o.y1)-max(b.y0,o.y0),1), w) for o, w in taken if _ov(b, o)])
            if best is None or sc < best[0]: best = (sc, dx, dy, ha, va, b)
        sc_, dx, dy, ha, va, b = best
        t.set_ha(ha); t.set_va(va); t.set_position(inv.transform((X + dx, Y + dy)))
        if hide and sum(w for o, w in taken if w >= 1 and _ov(b, o)) > 0:
            t.set_visible(False); HIDDEN.append(t.get_text()); continue
        taken.append((b, 1.0))

def declutter(fig, ax, places, pad=2):
    """places: lista (priorytet, Text). Wyższy priorytet stawiany pierwszy; reszta przesuwana albo ukrywana."""
    r = fig.canvas.get_renderer()
    others = [t for t in ax.texts if t not in {p[1] for p in places} and t.get_visible()]
    taken = []
    for t in others:
        try: taken.append(_ext(t, r))
        except Exception: pass
    inv = ax.transData.inverted()
    for _, t in sorted(places, key=lambda p: -p[0]):
        x0, y0 = t.get_position()
        bb = t.get_window_extent(r); w, h = bb.width, bb.height
        X0, Y0 = ax.transData.transform((x0, y0))
        ok = False
        for dx, dy in ((0, 0), (0, -1.6 * h), (0, 1.3 * h), (0.65 * w, -0.8 * h), (-0.65 * w, -0.8 * h),
                       (0.65 * w, 0.8 * h), (-0.65 * w, 0.8 * h), (0, -2.6 * h), (0, 2.3 * h)):
            t.set_position(inv.transform((X0 + dx, Y0 + dy)))
            b = t.get_window_extent(r)
            b = Bbox.from_extents(b.x0 - pad, b.y0 - pad, b.x1 + pad, b.y1 + pad)
            if not any(b.overlaps(o) for o in taken):
                taken.append(b); ok = True; break
        if not ok:
            t.set_position((x0, y0)); t.set_visible(False); print("ukryty podpis:", t.get_text())
