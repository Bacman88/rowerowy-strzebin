"""uMap layers: POI + proposed posts (with pole status)."""
import json
D = json.load(open('signs_prop.json')); M = json.load(open('../out/tabliczki/manifest.json'))
COL = {"brown": "#81552F", "red": "#902B38", "gray": "#505C66", "orange": "#B96516", "green": "#237647"}
KAT = {"brown": "historia i kultura", "red": "gastronomia", "gray": "infrastruktura", "orange": "sport i rekreacja", "green": "przyroda i szlaki"}
IK = {"church": "kościół", "community": "dom kultury", "bar": "bar", "restaurant": "restauracja", "heritage": "pomnik / zabytek", "service": "stacja napraw", "wc": "WC", "swim": "basen"}
where = {}
for p in D['posts']:
    for pl in p['plates']:
        if pl.get('poi'): where.setdefault(pl['name'], []).append(p['nr'])
feats, seen = [], set()
for poi in D['pois']:
    k = (poi['name'], round(poi['lat'], 5))
    if k in seen: continue
    seen.add(k)
    st = "planowane (fundusz sołecki 2027)" if poi.get('planned') else "istniejące"
    if poi.get('approx'): st += ", położenie przybliżone"
    feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [poi['lon'], poi['lat']]},
                  "properties": {"name": poi['name'], "Kategoria": KAT.get(poi['cat'], ""), "Piktogram": IK.get(poi['icon'], poi['icon']), "Status": st,
                                 "Na słupkach": ", ".join(map(str, sorted(set(poi.get('posts') or where.get(poi['name'], []))))),
                                 "_umap_options": {"color": COL.get(poi['cat'], "#333")}}})
json.dump({"type": "FeatureCollection", "features": feats}, open('../out/umap_POI.geojson', 'w'), ensure_ascii=False, indent=1)
PCOL = {"istniejący": "#2563a8", "nowy": "#d9480f", "opcjonalny": "#7b4fb3", "do sprawdzenia": "#8a8f94"}
pf = []
for p in D['posts']:
    names = []
    for pl in p['plates']:
        n = "Leśno Rajza" if pl.get('lr') else pl['name']
        if n not in names: names.append(n)
    pole = p.get('pole', 'do sprawdzenia')
    pf.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [p['lon'], p['lat']]},
               "properties": {"name": f"Słupek {p['nr']}", "Kierunki": ", ".join(names), "Liczba tabliczek": len(M.get(str(p['nr']), [])),
                              "Lokalizacja": p['loc'], "Status": "propozycja",
                              "Uzgodnienie": {"nadl_K": "Nadleśnictwo Koszęcin"}.get(p['who'], "Gmina Koszęcin"), "Gmina": p.get("gmina", "Koszęcin"),
                              "Słupek": pole + (" (na istniejącym słupku)" if p.get("slup_jest") else ""), "Średnica rury": "", "Data dodania": "2026-11-06",
                              "_umap_options": {"color": PCOL[pole]}}})
json.dump({"type": "FeatureCollection", "features": pf}, open('../out/umap_slupki_propozycja.geojson', 'w'), ensure_ascii=False, indent=1)
print("POI", len(feats), "słupki", len(pf), {k: sum(f['properties']['Słupek'] == k for f in pf) for k in PCOL})
