"""Sieć węzłów: sąsiedztwo słupków po drogach (bez przechodzenia przez inny słupek)."""
import json, math, sys, pickle
import numpy as np, networkx as nx
from pyproj import Transformer
from shapely.geometry import LineString, Point
exec(open("directions.py").read().split("posts = D[\"posts\"]")[0].replace("OSM, SIGNS, OUT, REPORT, SURVEY = sys.argv[1:6]",
  "OSM, SIGNS, SURVEY = 'osm2_clean.geojson','signs_prop.json',sys.argv[1]"))
posts=D["posts"]; pn={p["nr"]:snap(p["lon"],p["lat"]) for p in posts}; inv={v:k for k,v in pn.items()}
pxy={k:np.array(P(*v)) for k,v in pn.items()}
edges={}
for a in pn:
    cost,paths=nx.single_source_dijkstra(G,pn[a],cutoff=7000,weight="c")
    for b in pn:
        if b<=a or pn[b] not in paths: continue
        pth=paths[pn[b]]; pts=np.array([P(*n) for n in pth])
        blocked=False
        for c in pn:
            if c in(a,b): continue
            dmin=np.min(((pts[1:-1]-pxy[c])**2).sum(1))**.5 if len(pts)>2 else 1e9
            if dmin<40: blocked=True; break
        if blocked: continue
        L=sum(G[u][v]["w"] for u,v in zip(pth,pth[1:]))/1000
        edges[(a,b)]=(L,pth)
# usuń krawędzie "przez" – jeśli istnieje a-c-b o podobnej długości
pickle.dump(edges,open("../wezly/siec.pkl","wb"))
print(len(edges))
for (a,b),(L,_) in sorted(edges.items()): print(f"{a}-{b}:{L:.1f}",end="  ")
