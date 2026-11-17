"""Upakowanie stan/odcinki.js (17.11.2026, etap 2 – lżejsza nawigacja). Bezstratne.

Krok na końcu budowania (po odcinki.py, jedz_dane.py, kafle.py, wysokosci.py, które czytają zwykły format):
  - powtarzające się teksty (typ drogi, nazwa ulicy, nawierzchnia, stan, opis pomiaru) → tabela + numery,
  - współrzędne → liczby całkowite w 1e-5 stopnia, różnicowo (dane mają i tak 5 miejsc po przecinku).
W pliku jest mały dekoder, który odtwarza dokładnie tę samą tablicę window.ODC co wcześniej – mapa wspólna,
Jedź, panel i edytor tabliczek działają bez zmian. Po zapisaniu porównanie w Node: dane po rozpakowaniu muszą być
identyczne z wejściem, inaczej plik wejściowy zostaje i budowanie kończy się błędem.
Użycie: python3 pakuj_odcinki.py <katalog strony>
"""
import json, os, subprocess, sys, tempfile

OUT = sys.argv[1]
P = os.path.join(OUT, "stan", "odcinki.js")
src = open(P, encoding="utf-8").read()
if not src.startswith("window.ODC=["):
    print("odcinki.js: już upakowany – pomijam"); sys.exit(0)
dec = json.JSONDecoder()
ODC, e = dec.raw_decode(src, len("window.ODC="))
reszta = src[e:]          # raw_decode zwraca pozycję bezwzględną; ";\nwindow.ODC_ALIASY=…;" – bez zmian

tab, idx = [], {}
def t(x):
    if x not in idx: idx[x] = len(tab); tab.append(x)
    return idx[x]

o = []
for s in ODC:
    c, d, pa, pb = s[7], [], 0, 0
    for k in range(0, len(c), 2):
        a, b = round(c[k] * 1e5), round(c[k + 1] * 1e5)
        d += [a - pa, b - pb]; pa, pb = a, b
    o.append([s[0], t(s[1]), t(s[2]), t(s[3]), t(s[4]), t(s[5]), s[6], d])

DEKODER = ("window.ODC=(D=>{const T=D.t;return D.o.map(x=>{const d=x[7],c=new Array(d.length);let a=0,b=0;"
           "for(let i=0;i<d.length;i+=2){a+=d[i];b+=d[i+1];c[i]=a/1e5;c[i+1]=b/1e5}"
           "return[x[0],T[x[1]],T[x[2]],T[x[3]],T[x[4]],T[x[5]],x[6],c]})})(")
nowy = DEKODER + json.dumps({"t": tab, "o": o}, ensure_ascii=False, separators=(",", ":")) + ")" + reszta

# kontrola: Node rozpakowuje i porównuje z wejściem (ten sam JSON = te same liczby i teksty)
with tempfile.TemporaryDirectory() as tmp:
    a, b = os.path.join(tmp, "a.js"), os.path.join(tmp, "b.js")
    open(a, "w", encoding="utf-8").write(src); open(b, "w", encoding="utf-8").write(nowy)
    js = ("const fs=require('fs');global.window=global;const w=f=>{(0,eval)(fs.readFileSync(f,'utf8'));return JSON.stringify([window.ODC,window.ODC_ALIASY])};"
          f"process.exit(w({json.dumps(a)})===w({json.dumps(b)})?0:1)")
    if subprocess.run(["node", "-e", js]).returncode != 0:
        print("BŁĄD: odcinki po upakowaniu różnią się od wejścia – zostawiam zwykły plik"); sys.exit(1)

open(P, "w", encoding="utf-8").write(nowy)
print(f"odcinki.js upakowany: {len(src.encode()) // 1024} kB → {len(nowy.encode()) // 1024} kB, dane identyczne")
