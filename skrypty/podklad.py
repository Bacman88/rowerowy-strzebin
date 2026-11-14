"""Mapa offline dla nawigacji „Jedź”: dane/podklad.json (lasy, wody, zabudowa, budynki, tory, nazwy z OpenStreetMap,
uproszczone – tworzy je workflow „Podklad” na gałęzi `wysokosci`) → <strona>/stan/podklad.js (window.PODKLAD).
Gdy pliku brak, pobieramy go z wydania „podklad” na GitHubie. Dane © współtwórcy OpenStreetMap (ODbL).
Użycie: python3 podklad.py ../dane/podklad.json ../out/strona
"""
import json, os, sys, urllib.request
SRC, OUT = sys.argv[1:3]
URL = "https://github.com/Bacman88/rowerowy-strzebin/releases/download/podklad/podklad.json"
if not os.path.exists(SRC):
    try:
        print("pobieram podkład mapy offline…"); urllib.request.urlretrieve(URL, SRC)
    except Exception as e:
        print("brak podkładu (", e, ") – mapa offline pokaże same drogi")
        open(f"{OUT}/stan/podklad.js", "w").write("window.PODKLAD=null;"); sys.exit(0)
d = json.load(open(SRC))
js = "window.PODKLAD=" + json.dumps(d, separators=(",", ":"), ensure_ascii=False) + ";"
open(f"{OUT}/stan/podklad.js", "w").write(js)
print(f"podkład offline: {len(d.get('las', []))} lasów, {len(d.get('bud', []))} budynków, {len(d.get('nazwy', []))} nazw, plik {len(js.encode()) / 1e6:.1f} MB")
