"""AED, apteki i sklepy spożywcze z OpenStreetMap (Overpass API) dla okolic Koszęcina → poi.json (lista punktów)."""
import json, sys, time, requests
S, W, N, E = 50.486, 18.655, 50.732, 19.013
BB = f"{S},{W},{N},{E}"
Q = f"""[out:json][timeout:300];
(
  nwr["emergency"="defibrillator"]({BB});
  nwr["amenity"="pharmacy"]({BB});
  nwr["shop"~"^(convenience|supermarket|greengrocer|bakery|butcher|general|farm|deli|food)$"]({BB});
);
out center tags;"""
dane = None
for url in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]:
    for proba in range(3):
        try:
            r = requests.post(url, data={"data": Q}, timeout=400, headers={"User-Agent": "HUB-rowerowy-Strzebin/1.0 (github.com/Bacman88/rowerowy-strzebin)"})
            print(url, r.status_code, len(r.content))
            if r.status_code == 200: dane = r.json(); break
        except Exception as e: print(url, "err", e)
        time.sleep(20)
    if dane: break
if not dane: sys.exit("brak danych z Overpass")
out = []
for e in dane["elements"]:
    t = e.get("tags", {}); lat = e.get("lat") or e.get("center", {}).get("lat"); lon = e.get("lon") or e.get("center", {}).get("lon")
    if lat is None: continue
    keep = {k: v for k, v in t.items() if k in ("emergency", "amenity", "dispensing", "shop", "name", "brand", "opening_hours", "defibrillator:location", "access", "indoor", "operator", "addr:street", "addr:housenumber", "addr:city", "addr:place")}
    out.append(dict(id=f"{e['type']}/{e['id']}", lat=round(lat, 6), lon=round(lon, 6), **keep))
json.dump(out, open("poi.json", "w"), ensure_ascii=False, indent=0)
print("punktów:", len(out), "AED:", sum(1 for o in out if o.get("emergency")), "aptek:", sum(1 for o in out if o.get("amenity") == "pharmacy"), "sklepów:", sum(1 for o in out if o.get("shop")))
