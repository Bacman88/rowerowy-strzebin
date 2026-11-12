import json, sys, numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
t=Transformer.from_crs(4326,3857,always_xy=True)
s,tx,ty=json.load(open(sys.argv[2]))['transform']
im=Image.open(sys.argv[1]).convert('RGB'); d=ImageDraw.Draw(im)
F=json.load(open('osm2_clean.geojson'))['features']
for f in F:
    if f['geometry']['type']=='LineString' and f['properties'].get('highway') in ('primary','secondary','tertiary','residential','unclassified','track'):
        pts=[(s*x+tx,-s*y+ty) for x,y in (t.transform(*c) for c in f['geometry']['coordinates'])]
        d.line(pts,fill=(220,0,0),width=1)
im.save(sys.argv[3])
