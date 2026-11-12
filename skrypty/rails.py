"""Linie kolejowe do rysowania: tylko tory główne, tor podwójny jako jedna linia, połączone odcinki (ciągły wzór kresek)."""
from shapely.ops import linemerge, unary_union
from shapely.geometry import LineString, MultiLineString
import geopandas as _gpd

def rail_lines(gdf, tol=18):
    rw = gdf["railway"] if "railway" in gdf else None
    if rw is None: return _gpd.GeoSeries([], crs=gdf.crs)
    sv = gdf["service"] if "service" in gdf else _gpd.pd.Series([None] * len(gdf), index=gdf.index)
    sel = gdf[(rw == "rail") & sv.isna() & gdf.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    parts = []
    for gm in sel.geometry:
        parts += list(gm.geoms) if gm.geom_type == "MultiLineString" else [gm]
    parts.sort(key=lambda l: -l.length)
    kept = []
    for l in parts:
        if kept:
            u = unary_union(kept).buffer(tol)
            if l.difference(u).length < 0.25 * l.length: continue      # drugi tor tej samej linii
            l = l.difference(u)
            if l.is_empty: continue
        kept.append(l)
    m = linemerge(unary_union(kept))
    geoms = list(m.geoms) if m.geom_type == "MultiLineString" else [m]
    return _gpd.GeoSeries([g for g in geoms if g.length > 30], crs=gdf.crs)
