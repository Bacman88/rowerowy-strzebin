"""Pobiera numeryczny model terenu dla okolic Koszęcina (GUGiK NMT, WCS) i zapisuje siatkę 5 m jako nmt.npz.
Zapasowo: Copernicus GLO-30 (model pokrycia – z drzewami) jako cop.npz. Log z próbami w log.txt."""
import re, sys, io, traceback, numpy as np, requests, rasterio
from rasterio.io import MemoryFile
from pyproj import Transformer
LOG = open("log.txt", "w")
def log(*a):
    s = " ".join(str(x) for x in a); print(s); LOG.write(s + "\n"); LOG.flush()
S, N, W, E = 50.486, 50.732, 18.655, 19.013
tr = Transformer.from_crs(4326, 2180, always_xy=True)
xs, ys = tr.transform([W, E, W, E], [S, S, N, N])
X0, X1, Y0, Y1 = int(min(xs)) // 100 * 100, int(max(xs)) // 100 * 100 + 100, int(min(ys)) // 100 * 100, int(max(ys)) // 100 * 100 + 100
log("EPSG:2180 easting", X0, X1, "northing", Y0, Y1)
STEP, TILE = 5, 2500
BASE = "https://mapy.geoportal.gov.pl/wss/service/PZGIK/NMT/GRID1/WCS/DigitalTerrainModelFormatTIFF"
ses = requests.Session(); ses.headers["User-Agent"] = "HUB-rowerowy-Strzebin/1.0 (github.com/Bacman88/rowerowy-strzebin)"

def czytaj(b):
    with MemoryFile(b) as mf, mf.open() as ds:
        a = ds.read(1).astype("float64"); nd = ds.nodata
        if nd is not None: a[a == nd] = np.nan
        a[(a < -100) | (a > 3000)] = np.nan
        return a, ds.bounds, ds.crs, ds.transform

def proba_gugik():
    try:
        cap = ses.get(BASE, params={"SERVICE": "WCS", "REQUEST": "GetCapabilities", "VERSION": "1.0.0"}, timeout=60).text
        open("gugik_cap10.xml", "w").write(cap)
        names = re.findall(r"<(?:wcs:)?name>([^<]+)</(?:wcs:)?name>", cap)
        log("GUGiK cap 1.0.0 names:", names[:10])
    except Exception as e:
        log("cap err", e); names = []
    try:
        cap2 = ses.get(BASE, params={"SERVICE": "WCS", "REQUEST": "GetCapabilities", "VERSION": "2.0.1"}, timeout=60).text
        open("gugik_cap20.xml", "w").write(cap2)
        ids = re.findall(r"CoverageId>([^<]+)<", cap2); log("GUGiK cap 2.0.1 ids:", ids[:10])
    except Exception as e:
        log("cap2 err", e); ids = []
    kand = list(dict.fromkeys(names + ids + ["DTM_PL-KRON86-NH_TIFF", "DTM_PL-EVRF2007-NH_TIFF"]))
    # mała próba: 500 m wokół Strzebinia; szukamy kombinacji (nazwa, kolejność osi), która zwraca sensowny raster
    cx, cy = tr.transform(18.897, 50.616); cx, cy = int(cx), int(cy)
    for nm in kand:
        for kol in ("xy", "yx"):
            bb = (cx - 250, cy - 250, cx + 250, cy + 250) if kol == "xy" else (cy - 250, cx - 250, cy + 250, cx + 250)
            p = {"SERVICE": "WCS", "VERSION": "1.0.0", "REQUEST": "GetCoverage", "COVERAGE": nm, "CRS": "EPSG:2180", "RESPONSE_CRS": "EPSG:2180",
                 "BBOX": ",".join(map(str, bb)), "WIDTH": 100, "HEIGHT": 100, "FORMAT": "image/tiff"}
            try:
                r = ses.get(BASE, params=p, timeout=120)
                log("try", nm, kol, r.status_code, r.headers.get("content-type"), len(r.content))
                if r.status_code != 200 or b"xception" in r.content[:2000]: log("   ", r.content[:300]); continue
                a, bnd, crs, t = czytaj(r.content)
                log("    shape", a.shape, "bounds", bnd, "crs", crs, "min/max", np.nanmin(a), np.nanmax(a), "nan%", np.isnan(a).mean())
                if np.isnan(a).mean() < .5 and 150 < np.nanmean(a) < 450: return nm, kol
            except Exception as e:
                log("    err", e)
    return None

def pobierz_gugik(nm, kol):
    nx, ny = (X1 - X0) // STEP, (Y1 - Y0) // STEP
    Z = np.full((ny, nx), np.nan)
    n = TILE // STEP
    for y in range(Y0, Y1, TILE):
        for x in range(X0, X1, TILE):
            xe, ye = min(x + TILE, X1), min(y + TILE, Y1)
            w, h = (xe - x) // STEP, (ye - y) // STEP
            bb = (x, y, xe, ye) if kol == "xy" else (y, x, ye, xe)
            p = {"SERVICE": "WCS", "VERSION": "1.0.0", "REQUEST": "GetCoverage", "COVERAGE": nm, "CRS": "EPSG:2180", "RESPONSE_CRS": "EPSG:2180",
                 "BBOX": ",".join(map(str, bb)), "WIDTH": w, "HEIGHT": h, "FORMAT": "image/tiff"}
            for proba in range(4):
                try:
                    r = ses.get(BASE, params=p, timeout=300); a, bnd, crs, t = czytaj(r.content); break
                except Exception as e:
                    log("tile retry", x, y, e); a = None
            if a is None: continue
            if a.shape != (h, w): log("tile shape", a.shape, "expected", (h, w), bnd); a = a[:h, :w]
            r0 = (Y1 - ye) // STEP; c0 = (x - X0) // STEP
            Z[r0:r0 + a.shape[0], c0:c0 + a.shape[1]] = a
            log("tile", x, y, "ok nan%", round(float(np.isnan(a).mean()), 3))
    return Z

def zapisz(fn, Z, step, x0, y1, zrodlo):
    zi = np.where(np.isnan(Z), -32768, np.round(Z * 10)).astype("int16")
    np.savez_compressed(fn, z=zi, step=step, x0=x0, y1=y1, crs=2180, zrodlo=zrodlo)
    log("saved", fn, Z.shape, "nan%", float(np.isnan(Z).mean()), "range", np.nanmin(Z), np.nanmax(Z))

try:
    k = proba_gugik(); log("GUGiK wybór:", k)
    if k: zapisz("nmt.npz", pobierz_gugik(*k), STEP, X0, Y1, "GUGiK NMT")
except Exception:
    log(traceback.format_exc())

# Copernicus GLO-30 (zapas)
try:
    url = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N50_00_E018_00_DEM/Copernicus_DSM_COG_10_N50_00_E018_00_DEM.tif"
    from rasterio.windows import from_bounds
    with rasterio.open(url) as ds:
        win = from_bounds(W, S, E, N, ds.transform); a = ds.read(1, window=win).astype("float64"); t = ds.window_transform(win)
    np.savez_compressed("cop.npz", z=np.round(a * 10).astype("int16"), lon0=t.c, lat1=t.f, dlon=t.a, dlat=t.e)
    log("copernicus", a.shape, a.min(), a.max())
except Exception:
    log(traceback.format_exc())
