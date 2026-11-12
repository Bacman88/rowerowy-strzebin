"""Paski tras (3 cm, w kolorze trasy, z numerem) + naklejki węzłów: pliki do druku, wykaz i podgląd słupków."""
import json, math, os, subprocess, zipfile, csv, collections, glob
from pypdf import PdfReader, PdfWriter, Transformation, PageObject
exec(open("trasy_kolory.py").read())
O = "../out"; W_ = "../out/_tmp/paski"; os.makedirs(W_, exist_ok=True)
F = "Fira Sans Condensed"; NODE = "#00838F"; BAND_H = 30; GAP = 10
TR = [r for r in json.load(open(f"{O}/drogowskazy_trasy.json")) if not r.get("alt")]
D = json.load(open("signs_prop.json")); posts = sorted(p["nr"] for p in D["posts"])
BANDS = collections.defaultdict(list)
for r in TR:
    for k in r["seq"]:
        if isinstance(k, int) and r["id"] not in BANDS[k]: BANDS[k].append(r["id"])
for k in BANDS: BANDS[k].sort(key=int)
def band_svg(rid, dia):
    C = math.pi * dia; L = round(C + 6); col, txt, _ = KOLORY[rid]; step = C / 3
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{L}mm" height="{BAND_H}mm" viewBox="0 0 {L} {BAND_H}"><rect width="{L}" height="{BAND_H}" fill="{col}"/>']
    for i in range(3):
        g.append(f'<text x="{step / 2 + i * step:.1f}" y="{BAND_H / 2 + 7.6:.1f}" text-anchor="middle" font-family="{F}" font-weight="700" font-size="22" fill="{txt}">{rid}</text>')
    g.append(f'<rect x="{C:.1f}" width="6" height="{BAND_H}" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="0.3" stroke-dasharray="1.5 1.5"/></svg>')
    return "".join(g)
need = collections.Counter(r for b in BANDS.values() for r in b)
z = zipfile.ZipFile(f"{O}/paski_tras_SVG.zip", "w")
for dia in (60.3, 76.1):
    for rid in KOLORY:
        p = f"{W_}/pasek_trasa{rid}_fi{int(dia)}.svg"; open(p, "w").write(band_svg(rid, dia)); z.write(p, f"fi{int(dia)}/" + os.path.basename(p))
z.close()
# arkusz A4 do druku (Ø60): każdy pasek tyle razy, ile słupków + 10% zapasu
mm = 72 / 25.4
items = []
for rid in KOLORY:
    items += [rid] * (math.ceil(need[rid] * 1.1) if need[rid] else 0)
subprocess.run(["rsvg-convert", "-f", "pdf", "-o", f"{W_}/b.pdf"] + [f"{W_}/pasek_trasa{r}_fi60.svg" for r in KOLORY], check=True)
src = {r: pg for r, pg in zip(KOLORY, PdfReader(f"{W_}/b.pdf").pages)}
w = PdfWriter(); per = 7
for i, rid in enumerate(items):
    if i % per == 0: w.add_page(PageObject.create_blank_page(width=210 * mm, height=297 * mm))
    w.pages[-1].merge_transformed_page(src[rid], Transformation().translate(7.5 * mm, 297 * mm - (15 + (i % per) * 39 + BAND_H) * mm))
w.write(f"{O}/paski_tras_A4_fi60.pdf")
# wykaz CSV
with open(f"{O}/wykaz_paskow.csv", "w", newline="", encoding="utf-8-sig") as f:
    cw = csv.writer(f, delimiter=";"); cw.writerow(["Słupek (węzeł)", "Paski tras (od góry)", "Liczba pasków"])
    for n in posts: cw.writerow([n, ", ".join(BANDS.get(n, [])) or "—", len(BANDS.get(n, []))])
# podgląd słupków: wszystkie słupki, siatka
def pole_svg(x, y, n, bands, s=1.0):
    W = 22 * s; g = [f'<rect x="{x}" y="{y}" width="{W}" height="{120 * s}" fill="#aab2b7"/>']
    yy = y + 20 * s
    g.append(f'<rect x="{x}" y="{yy}" width="{W}" height="{26 * s}" fill="white"/><circle cx="{x + W / 2}" cy="{yy + 13 * s}" r="{10 * s}" fill="{NODE}"/>'
             f'<text x="{x + W / 2}" y="{yy + 17.2 * s}" text-anchor="middle" font-family="{F}" font-weight="700" font-size="{12 * s}" fill="white">{n}</text>')
    yy += 26 * s + 3 * s
    for rid in bands:
        col, txt, _ = KOLORY[rid]
        g.append(f'<rect x="{x}" y="{yy}" width="{W}" height="{9 * s}" fill="{col}"/><text x="{x + W / 2}" y="{yy + 7 * s}" text-anchor="middle" font-family="{F}" '
                 f'font-weight="700" font-size="{7.5 * s}" fill="{txt}">{rid}</text>')
        yy += 9 * s + 3 * s
    g.append(f'<rect x="{x}" y="{y}" width="{W}" height="{120 * s}" fill="url(#sh)"/>')
    return "".join(g)
def page(nrs, title, legend=False):
    g = ['<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 297 210"><defs><linearGradient id="sh" x1="0" x2="1">'
         '<stop offset="0" stop-color="#000" stop-opacity=".3"/><stop offset=".35" stop-color="#fff" stop-opacity=".2"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></linearGradient></defs>'
         '<rect width="297" height="210" fill="white"/>', f'<text x="12" y="14" font-family="{F}" font-weight="600" font-size="7" fill="#1d3b30">{title}</text>']
    for i, n in enumerate(nrs):
        cx = 14 + (i % 14) * 20; cy = 22 + (i // 14) * 80
        g.append(pole_svg(cx, cy, n, BANDS.get(n, []), s=0.6))
    if legend:
        SH = {"1": "obwodnica DW 906", "2": "Kalety – Hucisko", "3": "Kalety – Boronów", "4": "Bukowiec – Trójca", "5": "Babienica – Koszęcin",
              "6": "Psary – Trójca", "7": "Drutarnia – Strzebiń", "8": "Kalety – Sośnica", "9": "Sośnica – Trójca"}
        for j, (rid, (col, txt, nm)) in enumerate(KOLORY.items()):
            x = 12 + (j % 5) * 56; y = 186 + (j // 5) * 9
            g.append(f'<rect x="{x}" y="{y}" width="9" height="5" fill="{col}"/><text x="{x + 4.5}" y="{y + 4}" text-anchor="middle" font-family="{F}" font-weight="700" font-size="4" fill="{txt}">{rid}</text>'
                     f'<text x="{x + 11}" y="{y + 4}" font-family="{F}" font-size="3.6" fill="#333">{SH[rid]}</text>')
    g.append("</svg>"); return "".join(g)
chunks = [posts[i:i + 28] for i in range(0, len(posts), 28)]
pp = []
for k, ch in enumerate(chunks):
    fn = f"{W_}/slupki_{k}.svg"
    open(fn, "w").write(page(ch, f"Naklejka węzła i paski tras na słupkach (paski 3 cm, od góry wg numeru trasy) – słupki {ch[0]}–{ch[-1]}", legend=True)); pp.append(fn)
subprocess.run(["rsvg-convert", "-f", "pdf", "-o", f"{O}/paski_na_slupkach_wykaz.pdf"] + pp, check=True)
# podgląd do opisu
open(f"{W_}/demo.svg", "w").write('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="110" viewBox="0 0 120 110"><defs><linearGradient id="sh" x1="0" x2="1">'
    '<stop offset="0" stop-color="#000" stop-opacity=".3"/><stop offset=".35" stop-color="#fff" stop-opacity=".2"/><stop offset="1" stop-color="#000" stop-opacity=".4"/></linearGradient></defs>'
    '<rect width="120" height="110" fill="white"/>' + pole_svg(10, -10, 25, BANDS[25], .8) + pole_svg(48, -10, 41, BANDS[41], .8) + pole_svg(86, -10, 48, BANDS[48], .8) + "</svg>")
subprocess.run(["rsvg-convert", "-z", "6", f"{W_}/demo.svg", "-o", f"{O}/paski_demo.png"], check=True)
print("paski:", dict(need), "razem", sum(need.values()), "| strony wykazu", len(pp))
