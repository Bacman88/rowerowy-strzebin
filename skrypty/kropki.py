"""Kółka z numerami tras (generator V22) jako naklejki do doklejenia na tabliczki.
Tabliczki mają kółka już w pliku do druku; naklejki są na zmiany tras (dokleić/zakleić) i na tabliczki zrobione wcześniej.
Wynik: ../out/kropki_tras_A4.pdf (arkusze do wycięcia, z zapasem) i ../out/kropki_tras_wykaz.csv."""
import csv, math, collections
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
exec(open("trasy_kolory.py").read())
pdfmetrics.registerFont(TTFont("Inter", "../fonts/Inter-Regular.ttf")); pdfmetrics.registerFont(TTFont("InterB", "../fonts/Inter-Bold.ttf"))

O = "../out"; D = 31   # mm, jak w generatorze V22
rows = list(csv.reader(open(f"{O}/tabliczki/wykaz_tabliczek.csv", encoding="utf-8-sig"), delimiter=";"))
h = rows[0]; ic = h.index("Kółka tras (cel 1 / cel 2)")
wyk, cnt = [], collections.Counter()
for r in rows[1:]:
    if not r[ic]: continue
    cele = [(r[7], r[8]), (r[9], r[10])]
    for (cel, km), tr in zip(cele, r[ic].split(" / ")):
        if tr:
            wyk.append([r[0], r[1], r[2], r[4], cel, km, tr.replace(",", ", ")])
            for t in tr.split(","): cnt[t] += 1
with open(f"{O}/kropki_tras_wykaz.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";"); w.writerow(["Słupek", "Tabliczka", "Plik SVG", "Zwrot", "Cel", "Odległość", "Trasy (kółka)"]); w.writerows(wyk)

zapas = {t: n + max(2, math.ceil(n * .1)) for t, n in cnt.items()}
c = canvas.Canvas(f"{O}/kropki_tras_A4.pdf", pagesize=A4); PW, PH = A4
M, G = 12 * mm, 5 * mm; cols = int((PW - 2 * M + G) // (D * mm + G))
def head(first):
    c.setFont("InterB", 13); c.setFillColor("#1d2a23")
    c.drawString(M, PH - M - 4 * mm, "Kółka tras na tabliczki – naklejki Ø31 mm" + ("" if first else " (cd.)"))
    c.setFont("Inter", 8.5); c.setFillColor("#56665c")
    c.drawString(M, PH - M - 9 * mm, "Folia odporna na UV, cięcie po szarym okręgu (biała obwódka 1,4 mm zostaje). Ilości z ok. 10% zapasem.")
    c.drawString(M, PH - M - 13 * mm, "Do zmian tras i do tabliczek bez kółek. Gdzie który numer: kropki_tras_wykaz.csv (słupek, tabliczka, cel).")
    return PH - M - 19 * mm
y = head(True); first = True
for t in sorted(zapas, key=int):
    col, txt = KOLORY[t][:2]; n = zapas[t]; rows_n = math.ceil(n / cols)
    if y - 7 * mm - rows_n * (D * mm + G) < M:
        c.showPage(); y = head(False)
    c.setFont("InterB", 10); c.setFillColor("#1d2a23")
    c.drawString(M, y - 4 * mm, f"Trasa {t} – {KOLORY[t][2]}: {cnt[t]} szt. na tabliczkach + zapas = {n} szt."); y -= 8 * mm
    for i in range(n):
        x = M + (i % cols) * (D * mm + G) + D * mm / 2; yy = y - (i // cols) * (D * mm + G) - D * mm / 2
        c.setStrokeColor("#9aa3a8"); c.setLineWidth(.3); c.setDash(2, 1.5); c.circle(x, yy, D * mm / 2 + .6 * mm, stroke=1, fill=0); c.setDash()
        c.setFillColor("white"); c.circle(x, yy, D * mm / 2, stroke=0, fill=1)
        c.setFillColor(col); c.circle(x, yy, D * mm / 2 - 1.4 * mm, stroke=0, fill=1)
        c.setFillColor(txt); c.setFont("InterB", D * .66 / 25.4 * 72); c.drawCentredString(x, yy - D * .66 * .36 * mm, t)
    y -= rows_n * (D * mm + G) + 3 * mm
c.save()
# przykład do opisu: tabliczka z największą liczbą kółek
import json, shutil
man = json.load(open(f"{O}/tabliczki/manifest.json"))
best = max((t for ts in man.values() for t in ts), key=lambda t: (sum(len(x) for x in t["routes"]), len(t["routes"])))
shutil.copy(best["png"], f"{O}/kropki_demo.png")
print("kropki:", sum(cnt.values()), "na", len({(r[0], r[1]) for r in wyk}), "tabliczkach; naklejek z zapasem", sum(zapas.values()), dict(sorted(cnt.items(), key=lambda x: int(x[0]))))
