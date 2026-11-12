"""Jeden PDF dla Sołtys: opis projektu + kosztorys + mapy + katalog."""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, CondPageBreak)
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader, PdfWriter

S = ".."
O = "../out"
import os as _os; _os.makedirs(f"{O}/_tmp", exist_ok=True)
for w in ("Regular", "SemiBold", "Bold"):
    pdfmetrics.registerFont(TTFont(f"Inter-{w}", f"{S}/fonts/Inter-{w}.ttf"))
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("Inter-Regular", normal="Inter-Regular", bold="Inter-Bold", italic="Inter-Regular", boldItalic="Inter-Bold")
GREEN, GOLD, MUTED, INK = colors.HexColor("#1d3b30"), colors.HexColor("#c99a1e"), colors.HexColor("#5b6b62"), colors.HexColor("#24302b")

base = dict(fontName="Inter-Regular", fontSize=9.6, leading=13.6, textColor=INK)
P = ParagraphStyle("p", **base, spaceAfter=5)
LEAD = ParagraphStyle("lead", **{**base, "fontSize": 11.2, "leading": 15.5}, spaceAfter=8)
H1 = ParagraphStyle("h1", fontName="Inter-Bold", fontSize=25, leading=29, textColor=GREEN, spaceAfter=4)
KICK = ParagraphStyle("k", fontName="Inter-SemiBold", fontSize=9, leading=12, textColor=GOLD, spaceAfter=3)
H2 = ParagraphStyle("h2", fontName="Inter-Bold", fontSize=13.5, leading=17, textColor=GREEN, spaceBefore=10, spaceAfter=5, keepWithNext=1)
BUL = ParagraphStyle("b", **base, leftIndent=11, bulletIndent=1, spaceAfter=2.5)
SMALL = ParagraphStyle("s", **{**base, "fontSize": 8, "leading": 10.5, "textColor": MUTED})
CELL = ParagraphStyle("c", **{**base, "fontSize": 8.4, "leading": 10.6})
CELLB = ParagraphStyle("cb", **{**base, "fontName": "Inter-SemiBold", "fontSize": 8.4, "leading": 10.6})
HEAD = ParagraphStyle("hd", **{**base, "fontName": "Inter-SemiBold", "fontSize": 8.2, "leading": 10.2, "textColor": colors.white})

def bullets(items): return [Paragraph(t, BUL, bulletText="•") for t in items]
def table(rows, widths, bold_rows=(), stripe=True):
    data = [[Paragraph(c, HEAD) for c in rows[0]]] + [[Paragraph(c, CELLB if i in bold_rows else CELL) for c in r] for i, r in enumerate(rows[1:], 1)]
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), GREEN), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#d9ddd6")),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    for i in bold_rows: st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#eef2ea")))
    t.setStyle(TableStyle(st)); return t

def footer(c, d):
    c.saveState(); c.setFont("Inter-Regular", 7.5); c.setFillColor(MUTED)
    c.drawString(18 * mm, 10 * mm, "Sołectwo Strzebiń jako HUB rowerowy – projekt oznakowania · propozycja do dyskusji · listopad 2026")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(d.page)); c.restoreState()

doc = BaseDocTemplate(f"{O}/_tmp/opis.pdf", pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=17 * mm,
                      title="Sołectwo Strzebiń jako HUB rowerowy – projekt", author="Bartosz")
doc.addPageTemplates([PageTemplate(frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=footer)])
W = doc.width

# --- liczby i kosztorys liczone z danych ---
import json
DP = json.load(open("signs_prop.json")); MF = json.load(open(f"{O}/tabliczki/manifest.json"))
import csv as _csv
NKROP = sum(1 for r in list(_csv.reader(open(f"{O}/kropki_tras_wykaz.csv", encoding="utf-8-sig"), delimiter=";"))[1:] for _ in r[6].split(","))
NKT = len({(r[0], r[1]) for r in list(_csv.reader(open(f"{O}/kropki_tras_wykaz.csv", encoding="utf-8-sig"), delimiter=";"))[1:]})
NPASK = sum(int(r[2]) for r in list(_csv.reader(open(f"{O}/wykaz_paskow.csv", encoding="utf-8-sig"), delimiter=";"))[1:])
TR_all = json.load(open(f"{O}/drogowskazy_trasy.json"))
TR = [r for r in TR_all if not r.get("alt")]; TR1A = next((r for r in TR_all if r.get("alt")), None)
np_ = lambda p: len(MF.get(str(p["nr"]), []))
needpole = lambda p: p["pole"] == "nowy" or (p["pole"] == "opcjonalny" and not p.get("slup_jest"))
core = [p for p in DP["posts"] if p["pole"] != "opcjonalny"]
c_ex = [p for p in core if p["pole"] == "istniejący"]; c_new = [p for p in core if p["pole"] == "nowy"]
o_gm = [p for p in DP["posts"] if p["pole"] == "opcjonalny" and p["who"] == "gmina"]
o_K = [p for p in DP["posts"] if p["pole"] == "opcjonalny" and p["who"] == "nadl_K"]
o_B = [p for p in DP["posts"] if p["pole"] == "opcjonalny" and p["who"] == "nadl_B"]
nowe = lambda n: "nowe" if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14) else "nowych"
VAR = [(70, 110), (110, 160), (140, 200)]
def cost(ps):
    n = sum(np_(p) for p in ps); poles = sum(needpole(p) for p in ps)
    return n, poles, [(poles * 280 + n * 30 + n * a, poles * 280 + n * 30 + n * b) for a, b in VAR]
f1 = lambda v: f"{v / 1000:.1f}".replace(".", ",")
rng = lambda ab: f"{f1(ab[0])}–{f1(ab[1])} tys. zł"
def add_(*cs): return [(sum(c[2][i][0] for c in cs), sum(c[2][i][1] for c in cs)) for i in range(3)]
K1, K2, KG, KK, KB = cost(c_ex), cost(c_new), cost(o_gm), cost(o_K), cost(o_B)
NPOST = len(DP["posts"]); NPL = sum(np_(p) for p in DP["posts"]); NCORE = sum(np_(p) for p in core)
NOPT = NPOST - len(core); NFOR = len(o_K) + len(o_B); NGEX = sum(1 for p in o_gm if p.get("slup_jest"))
NNEW = sum(needpole(p) for p in DP["posts"])
st = []
st += [Paragraph("SOŁECTWO STRZEBIŃ · GMINA KOSZĘCIN", KICK), Paragraph("Sołectwo Strzebiń jako HUB rowerowy", H1),
       Paragraph("Projekt oznakowania tras rowerowych wokół Strzebinia – opis, kosztorys, mapy i katalog tabliczek", ParagraphStyle("sub", **{**base, "fontSize": 11.5, "leading": 15, "textColor": MUTED}, spaceAfter=10))]
R1 = {k for k in TR[0]["seq"] if isinstance(k, int)}
r1_opt = [p for p in DP["posts"] if p["nr"] in R1 and p["pole"] == "opcjonalny"]
r1_ex = [p for p in r1_opt if p.get("slup_jest")]; r1_las = [p for p in r1_opt if not p.get("slup_jest")]
K1 = cost(c_ex + r1_ex); KD = cost(r1_las)
o_gm = [p for p in o_gm if p["nr"] not in R1]; o_K = [p for p in o_K if p["nr"] not in R1]; o_B = [p for p in o_B if p["nr"] not in R1]
KG, KK, KB = cost(o_gm), cost(o_K), cost(o_B)
e1 = core + r1_opt; NE1 = sum(np_(p) for p in e1); NOPT = NPOST - len(e1); NFOR = len(o_K) + len(o_B); NGEX = sum(1 for p in o_gm if p.get("slup_jest"))
E1 = add_(K1, K2, KD); E2 = add_(KG, KK, KB); ALL = add_(K1, K2, KD, KG, KK, KB)
r1n = lambda ps: ", ".join(str(p["nr"]) for p in sorted(ps, key=lambda p: p["nr"]))
lo_hi = lambda v: f"{f1(v[0][0])}–{f1(v[2][1])} tys. zł"     # od wariantu A min do wariantu C max
T1 = TR[0]; km = lambda v: f"{v:.1f}".replace(".", ",")
e1n = {p["nr"] for p in e1}
forest_routes = [r for r in TR if any(isinstance(k, int) and k not in e1n for k in r["seq"])]
BOX = ParagraphStyle("box", **{**base, "fontSize": 10, "leading": 14.2, "textColor": colors.white}, leftIndent=12, bulletIndent=0, spaceAfter=4)
BOXH = ParagraphStyle("boxh", fontName="Inter-Bold", fontSize=10, leading=13, textColor=colors.HexColor("#e9b949"), spaceAfter=6)
box = [Paragraph("W SKRÓCIE", BOXH)] + [Paragraph(t, BOX, bulletText="•") for t in [
    f"<b>Rowerowa obwodnica DW 906 – {km(T1['km'])} km</b> z Sośnicy przez Piasek, Bukowiec i Strzebiń do Prądów, bocznymi ulicami i drogami leśnymi; przy okazji omija też DW 908 między Sośnicą a Piaskiem. "
    f"Po samej wojewódzkiej (poza chodnikiem i drogą rowerową) tylko ok. {T1['dw'] * 1000:.0f} m. To odpowiedź na brak drogi rowerowej "
    "Bukowiec – Strzebiń – Prądy – Koszęcin.",
    f"<b>Etap 1 – Strzebiń i cała obwodnica DW 906: {lo_hi(E1)}</b>. {len(e1)} słupków (w tym {len(c_ex) + len(r1_ex)} już stojących słupków z nazwami ulic), {NE1} tabliczek.",
    f"<b>Etap 2 – trasy leśne z nadleśnictwami: {lo_hi(E2)}</b>. Słupki w lasach Nadleśnictw Koszęcin i Boronów tworzą trasy do Kalet, Boronowa, Koszęcina i Drutarni.",
    "<b>Pilotaż dla całej gminy</b> – Strzebiń może przetrzeć szlak: metoda, wzór tabliczek i numeracja węzłów są gotowe do wprowadzenia w kolejnych sołectwach."]]
bt = Table([[box]], colWidths=[W]); bt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
st.append(bt); st.append(Spacer(1, 8))
st.append(Paragraph("Strzebiń jest ze wszystkich stron otoczony szlakami rowerowymi – od południa Leśno Rajza, od północy Liswarciański Szlak Rowerowy – "
                    "i w naturalny sposób stał się miejscem, w którym te trasy się spotykają. Proponuję ten HUB oznakować prostymi tabliczkami "
                    "kierunkowymi dla rowerzystów: nazwa miejscowości lub miejsca, odległość i strzałka.", LEAD))
plates = ["S17_T1_lewo_800.png", "S17_T4_lewo_800.png", "S27_T4_prawo_800.png", "S09_T4_prawo_800.png", "S21_T4_lewo_800.png"]
pw = (W - 6 * mm) / 2
imgs = [Image(f"{O}/tabliczki/png/{p}", width=pw, height=pw / 4) for p in plates]
grid = Table([[imgs[0], imgs[1]], [imgs[2], imgs[3]], [imgs[4], Paragraph("Przykładowe tabliczki 800 × 200 mm (wzór „HUB Strzebiń”): "
              "niebieskie – miejscowości, zielone – szlaki, brązowe – historia i kultura, grafitowe – infrastruktura, pomarańczowe – sport, czerwone – gastronomia.", SMALL)]],
             colWidths=[pw + 3 * mm, pw + 3 * mm])
grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
st.append(grid)
st.append(Paragraph("Nie są to znaki szlaków rowerowych ani znaki drogowe, tylko tabliczki informacyjne. Przy drogach publicznych i w lasach wymagają zgody zarządcy.", SMALL))

st.append(Paragraph("Po co to robimy", H2))
st += bullets([
    "<b>Bezpieczny objazd DW 906</b> – brak drogi rowerowej wzdłuż wojewódzkiej wraca na każdym zebraniu od lat. W samym Strzebiniu jest już "
    "droga rowerowa wzdłuż DW 906 (od słupka 25 do 16, ok. 1,5 km) i bezpieczny chodnik (od słupka 27 do 25), ale brakuje połączeń z Bukowcem, Prądami i Koszęcinem. "
    "Oznakowanie tras obok DW 906, z utwardzeniem najgorszych odcinków, to szybka i wielokrotnie tańsza alternatywa niż budowa drogi rowerowej.",
    "<b>Turystyka</b> – oznakowany HUB przyciągnie turystów rowerowych, a ci, którzy już przejeżdżają szlakami, zatrzymają się przy ciekawych miejscach.",
    "<b>Uroki sołectwa i gminy</b> – tabliczki prowadzą do zabytków, miejsc spotkań, przyrody i lokalnych punktów.",
    "<b>Połączenia, o których mało kto wie</b> – coraz więcej mieszkańców to osoby napływowe, które znają tylko główne drogi.",
    "<b>Stan dróg</b> – projekt porządkuje wiedzę o drogach łączących miejscowości i wskazuje odcinki wymagające naprawy."])

st.append(Paragraph("Proponowane trasy rowerowe", H2))
st.append(Paragraph(f"Proponuję {['','jedną','dwie','trzy','cztery','pięć','sześć','siedem','osiem','dziewięć','dziesięć','jedenaście','dwanaście'][len(TR)]} tras pokazowych poprowadzonych drogami, "
                    "na których stoją drogowskazy (mapa 1). Ciąg liczb to numery słupków – trasę można opisać jednym zdaniem na ulotce, "
                    "stronie gminy czy profilu sołectwa.", P))
def seqs(r): return " → ".join(str(k) if isinstance(k, int) else ("kościół św. Trójcy" if k == "Trójca" else ("Kalety (stadion Unii)" if k == "Kalety Unia" else k)) for k in r["seq"])
pc = lambda r: (round(r['pav'] / r['km'] * 100), round(r.get('grv', 0) / r['km'] * 100))
st.append(table([["Trasa", "Przebieg (numery słupków)", "km", "Asfalt / kostka", "Szuter", "Grunt.", "DW 906*"]] +
    [[f"<b>{r['id']}. {r['name']}</b>" + (f"<br/>{r['sub']}" if r['sub'] else ""), seqs(r), km(r['km']),
      f"{pc(r)[0]}%", f"{pc(r)[1]}%", f"{100 - sum(pc(r))}%", f"{r['dw'] * 1000:.0f} m"] for r in TR],
    [40 * mm, W - 40 * mm - 77 * mm, 14 * mm, 16 * mm, 13 * mm, 13 * mm, 15 * mm]))
st.append(Paragraph("Nawierzchnia według OpenStreetMap: asfalt / kostka – asfalt, beton, kostka (oraz ulice bez opisu nawierzchni); "
                    "szuter – drogi z kruszywa i dobre drogi leśne; gruntowe – pozostałe drogi polne i leśne. Do potwierdzenia w terenie.", SMALL))
st.append(Paragraph("* „DW 906” – tylko jazda jezdnią wojewódzkiej (głównie krótki fragment Katowickiej w Bukowcu i przejazdy w poprzek); "
                    "nie obejmuje istniejącej drogi rowerowej (słupki 25–16) ani chodnika (27–25) wzdłuż DW 906. "
                    f"Trasa 1 jest w całości w etapie 1. Trasy {', '.join(r['id'] for r in forest_routes)} prowadzą także przez lasy – "
                    "do ich pełnego oznakowania potrzebne są słupki z etapu 2, z udziałem nadleśnictw.", SMALL))
st.append(Spacer(1, 3))
st.append(Paragraph("<b>Trasa 1 to rowerowa obwodnica DW 906.</b> Zamiast budowy drogi rowerowej wzdłuż wojewódzkiej (Bukowiec – Strzebiń – Prądy, a na początku także DW 908 Sośnica – Piasek) "
                    "rowerzysta jedzie bocznymi ulicami – 1 Maja, Lompy, Wojska Polskiego, Kościuszki, Ligonia – i drogami leśnymi. "
                    f"Z DW 906 styka się tylko na ok. {T1['dw'] * 1000:.0f} m. Gmina może za ok. {lo_hi(E1)} (cały etap 1) dać mieszkańcom objazd "
                    "całego problematycznego odcinka: wystarczą tabliczki na istniejących i kilku nowych słupkach oraz utwardzenie najgorszych odcinków."
                    + (f" <b>Wariant 1a:</b> w środku Strzebinia trasa może też jechać istniejącą drogą rowerową wzdłuż DW 906 "
                       f"({' → '.join(map(str, TR1A['seq']))}, {km(TR1A['km'])} km) zamiast ulicą 1 Maja." if TR1A else ""), P))

st.append(Paragraph("Propozycja: numery węzłów i paski tras na słupkach", H2))
st.append(Table([[Image(f"{O}/paski_demo.png", width=40 * mm, height=40 * 110 / 120 * mm),
    Paragraph("Na wzór holenderskiej sieci węzłów rowerowych każdy słupek ma swój numer – ten sam na mapach, w katalogu i na tablicach z mapą "
              "(„Jesteś przy węźle 25”). Numer jest na opasce owiniętej wokół słupka, powtórzony trzy razy, więc widać go z każdej strony. "
              "To oznaczenie pomocnicze: drogowskazy prowadzą tak samo, a numery pozwalają opisać trasę jednym zdaniem. Kolor morski wybrano tak, "
              "by nie mylił się ze znakami szlaków ani z oznaczeniami sieci uzbrojenia (gaz – żółty, woda – niebieski, hydranty – czerwony). "
              "Pod numerem węzła są 3-centymetrowe paski w kolorach tras, które przez ten słupek przebiegają, z numerem trasy – zawsze od góry "
              "według numeru (na przykładzie: słupki 25, 41 i 48). Kolory są te same co na mapie tras, więc rowerzysta jadący np. czerwoną trasą 1 "
              "na każdym słupku widzi swój czerwony pasek z „1”. Przy zmianie przebiegu trasy wystarczy wymienić pasek.", SMALL)]],
    colWidths=[44 * mm, W - 44 * mm], style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))

st.append(Spacer(1, 4))
st.append(Table([[Image(f"{O}/kropki_demo.png", width=62 * mm, height=62 * 200 / 800 * mm),
    Paragraph(f"<b>Numery tras na tabliczkach (generator V22).</b> Przy nazwie celu stoją kółka z numerami tras w ich kolorach – np. „Łazy ①④⑥” "
              f"mówi od razu, że w tę stronę jedzie trasa 1, 4 i 6. Kółko dostaje cel, do którego trasa prowadzi co najmniej przez 1 km "
              f"(lub większość drogi); cele bliżej niż 1 km są bez kółek. Razem {NKROP} kółek na {NKT} tabliczkach, bez wydłużania żadnej tabliczki. "
              "Kółka są w plikach do druku, a przy zmianie przebiegu trasy wystarczy dokleić lub zakleić kółko-naklejkę Ø31 mm – tabliczka zostaje. "
              "Paski na słupkach zostają jako potwierdzenie trasy przy samym węźle.", SMALL)]],
    colWidths=[66 * mm, W - 66 * mm], style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))

st.append(Paragraph("Co obejmuje projekt", H2))
st.append(table([
    ["Element", "Zakres"],
    ["Etap 1 – Strzebiń i obwodnica DW 906", f"{len(e1)} lokalizacji: {len(c_ex) + len(r1_ex)} istniejących słupków z nazwami ulic (podpinamy tabliczki), {len(c_new)} nowych w gminie i {len(r1_las)} w lasach między Sośnicą, Piaskiem i Bukowcem (słupki {r1n(r1_las)}, z Nadl. Koszęcin); {NE1} tabliczek"],
    ["Etap 2 – trasy leśne i uzupełnienia", f"{NOPT} lokalizacji: {NFOR} w lasach (Nadleśnictwa Koszęcin i Boronów) oraz {len(o_gm)} dodatkowych na terenie gminy; {NPL - NE1} tabliczek"],
    ["Tabliczki", f"razem {NPL} tabliczek 800 × 200 mm, dibond z drukiem dwustronnym"],
    ["Odległości", "liczone po drogach, z preferencją dróg utwardzonych i odcinków sprawdzonych w terenie; kierunki przejrzane ręcznie słupek po słupku"],
    ["Połączenia ze szlakami", "Prądy → Leśno Rajza (ok. 2,3 km), Łazy → Liswarciański Szlak Rowerowy (ok. 1,8 km)"],
    ["Stan dróg", "ok. 18 km zmierzonych w terenie; 8 odcinków (2,2 km) średniej lub złej jakości; mapa dróg do sprawdzenia"],
    ["Cele lokalne", "kościoły św. Krzyża i św. Trójcy, pomnik J. Ligonia, kapliczka w Łazach, Piekarniok, GOSiR, boisko w Strzebiniu, stacje napraw rowerów (przy boisku także WC); gastronomia – przykładowo (Zagroda u Czesi, Baza, Bistro Moderno; na mapach także Beczka i Pod Pałacem w Koszęcinie, restauracje w Piasku i Sośnicy)"],
], [44 * mm, W - 44 * mm]))
st.append(Spacer(1, 4))
st += bullets([
    "<b>Punkty gastronomiczne są tylko przykładowe</b> – rowerzystów na pewno interesują, ale lista powinna być ustalona wspólnie i na równych zasadach.",
    "<b>Lokalizacje i kierunki są do dyskusji</b> – z Radą Sołecką, mieszkańcami i zarządcami dróg.",
    "<b>Fundusz sołecki 2027</b> już obejmuje dwa miejsca odpoczynku dla rowerzystów ze stacjami naprawy (przy pomniku J. Ligonia i przy boisku) "
    "oraz dwie tablice o historii (Piekarniok, pomnik J. Ligonia) – oznakowanie HUB-u będzie do nich prowadzić."])

st.append(CondPageBreak(95 * mm)); st.append(Paragraph("Kosztorys (szacunkowy, brutto)", H2))
st.append(Paragraph("Kwoty oparte na cenach z ofert internetowych z listopada 2026 r. – wymagają zapytania ofertowego. Warianty: A – dibond 3 mm, płyta prostokątna; "
                    "B – dibond 3 mm z folią i laminatem UV, cięcie po obrysie; C – aluminium 2,5–3 mm z folią odblaskową.", SMALL))
st.append(Spacer(1, 3))
st.append(table([
    ["Część", "Słupki", "Tab.", "Wariant A", "Wariant B", "Wariant C"],
    ["1. Tabliczki na istniejących słupkach", f"{len(c_ex) + len(r1_ex)} istniejących", str(K1[0]), *map(rng, K1[2])],
    ["2. Nowe słupki z tabliczkami", f"{len(c_new)} {nowe(len(c_new))}", str(K2[0]), *map(rng, K2[2])],
    [f"3. Obwodnica DW 906 – lasy Sośnica–Piasek–Bukowiec (słupki {r1n(r1_las)})", f"{len(r1_las)} {nowe(len(r1_las))}", str(KD[0]), *map(rng, KD[2])],
    ["Etap 1 – Strzebiń i obwodnica DW 906", str(len(e1)), str(NE1), *map(rng, E1)],
    ["4. Trasy leśne – Nadleśnictwo Koszęcin", f"{len(o_K)} {nowe(len(o_K))}", str(KK[0]), *map(rng, KK[2])],
    ["5. Trasy leśne – Nadleśnictwo Boronów", f"{len(o_B)} {nowe(len(o_B))}", str(KB[0]), *map(rng, KB[2])],
    ["6. Uzupełnienia na terenie gminy", f"{len(o_gm)} {nowe(len(o_gm))}", str(KG[0]), *map(rng, KG[2])],
    ["Etap 2 – trasy leśne i uzupełnienia", str(NOPT), str(NPL - NE1), *map(rng, E2)],
    ["Razem etap 1 i 2", f"{NPOST} ({NNEW} {nowe(NNEW)})", str(NPL), *map(rng, ALL)],
], [52 * mm, 22 * mm, 10 * mm, (W - 84 * mm) / 3, (W - 84 * mm) / 3, (W - 84 * mm) / 3], bold_rows=(4, 8, 9)))
st.append(Spacer(1, 3))
st.append(Paragraph("Założenia: tabliczka z drukiem dwustronnym 70–200 zł zależnie od wariantu; mocowanie (obejmy i śruby nierdzewne) ok. 30 zł na tabliczkę; "
                    f"nowy słupek fi 60 mm z kotwą i montażem ok. 280 zł. Naklejki węzłów ({NPOST} szt.), paski tras (ok. {NPASK} szt.) i zapasowe kółka tras do doklejania – razem ok. 0,5–1 tys. zł dodatkowo. "
                    "Poza kosztorysem: ewentualne podsypanie i utwardzenie najgorszych odcinków (orientacyjnie 80–120 tys. zł za 1 km przy szerokości 3 m; "
                    "same odcinki trudne – ok. 0,7 km).", SMALL))

st.append(Paragraph("Skąd wziąć środki", H2))
st += bullets([
    "<b>Fundusz sołecki</b> – oznakowanie można ująć we wniosku na 2028 r. (fundusz na 2027 r. już rozdysponowano).",
    "<b>Konkurs marszałkowski „Inicjatywa Sołecka”</b> – kategoria turystyki i krajoznawstwa; wniosek składa gmina (w 2025 r. nabór do 21 lutego).",
    "<b>Budżet gminy</b> – zgodnie ze Strategią Rozwoju Gminy Koszęcin 2025–2035 (słabość: niewystarczająca sieć tras rowerowych; cel II.2: oznakowane szlaki).",
    "<b>Nadleśnictwa Koszęcin i Boronów</b> – etap 2, słupki i tabliczki na trasach leśnych realizowane wspólnie.",
    "<b>Partnerzy lokalni</b> – lokale i sklepy przy trasach mogą współfinansować przedsięwzięcie (np. ok. 2 tys. zł) w zamian za tabliczkę kierunkową do swojego "
    "lokalu na dwóch najbliższych słupkach na czas życia tabliczek; tabliczki pozostają własnością gminy, zasady jednakowe dla wszystkich. "
    "Cztery lokale pokryłyby znaczną część kosztu etapu 1.",
    "<b>Czyn społeczny</b> – montaż tabliczek na istniejących słupkach i przeglądy tras."])

st.append(Paragraph("Strzebiń jako pilotaż dla całej gminy", H2))
st.append(Paragraph("Projekt powstał tak, by dało się go wprowadzić w każdym sołectwie: ten sam wzór i kolory tabliczek, odległości liczone po drogach "
                    "z mapy OpenStreetMap, numery słupków jako węzły i te same mapy. Jeśli oznakowanie sprawdzi się w Strzebiniu, gmina może je rozszerzać "
                    "sołectwo po sołectwie, a trasy sąsiednich sołectw połączą się w jedną gminną sieć – bez zamawiania za każdym razem projektu od zera. "
                    "Już teraz trasy pokazowe prowadzą do Koszęcina, Kalet, Boronowa, Babienicy, Psar, Drutarni i Sośnicy – a Sośnica, z hotelem i restauracją, to naturalne miejsce wypadowe dla rowerzystów.", P))

st.append(Paragraph("Zawartość dokumentu i dalsze kroki", H2))
st.append(table([
    ["Strona", "Co zawiera"],
    ["Mapa 1 (A2)", "Proponowane trasy rowerowe z numerami słupków, w tym rowerowa obwodnica DW 906"],
    ["Mapa 2 (A2)", "Wszystkie słupki na tle szlaków – niebieskie: istniejące, pomarańczowe: nowe, fioletowe: opcjonalne"],
    ["Mapa 3 (A2)", "Powiększenie Strzebinia z okolicą, w tym zbliżenia Łaz i skrzyżowań przy torach"],
    ["Mapa 4 (A2)", "Stan dróg: odcinki średniej lub złej jakości (pomiary 2026) i drogi do sprawdzenia"],
    ["Naklejki i paski (A4)", "Każdy słupek z naklejką węzła i paskami tras w kolejności montażu, z legendą kolorów"],
    ["Katalog (A4)", "Każdy słupek z lokalizacją, uzgodnieniem i wszystkimi tabliczkami"],
], [32 * mm, W - 32 * mm]))
st.append(Spacer(1, 5))
st += bullets([
    "omówienie lokalizacji i kierunków – Rada Sołecka, zebranie wiejskie;",
    "objazd dróg omijających DW 906 i uzupełnienie pomiarów;",
    "rozmowa z Urzędem Gminy (zgody zarządcy dróg, forma współpracy z partnerami) i z nadleśnictwami (trasy leśne);",
    "zapytanie ofertowe na tabliczki i mocowania; wybór wariantu materiału."])
st.append(Spacer(1, 8))
st.append(Paragraph("Przygotował: Bartosz · Strzebiń, listopad 2026 · dane map © autorzy OpenStreetMap (ODbL), piktogramy Tabler Icons (MIT)", SMALL))
doc.build(st)

# złożenie całości
w = PdfWriter()
def add(path, title):
    start = len(w.pages)
    for pg in PdfReader(path).pages: w.add_page(pg)
    w.add_outline_item(title, start)
add(f"{O}/_tmp/opis.pdf", "Opis projektu i kosztorys")
add(f"{O}/drogowskazy_trasy.pdf", "Mapa 1 – proponowane trasy rowerowe")
mk = PdfReader(f"{O}/drogowskazy_mapy_komplet.pdf")
s0 = len(w.pages); w.add_page(mk.pages[0]); w.add_outline_item("Mapa 2 – wszystkie słupki", s0)
s0 = len(w.pages); w.add_page(mk.pages[1]); w.add_outline_item("Mapa 3 – Strzebiń (powiększenie)", s0)
add(f"{O}/drogowskazy_stan_drog.pdf", "Mapa 4 – stan dróg")
add(f"{O}/paski_na_slupkach_wykaz.pdf", "Naklejki węzłów i paski tras na słupkach")
add(f"{O}/drogowskazy_katalog.pdf", "Katalog słupków i tabliczek")
w.add_metadata({"/Title": "Sołectwo Strzebiń jako HUB rowerowy – projekt oznakowania", "/Author": "Bartosz"})
w.write(f"{O}/Solectwo_Strzebin_jako_HUB_rowerowy.pdf")
import shutil; shutil.copy(f"{O}/_tmp/opis.pdf", f"{O}/Solectwo_Strzebin_jako_HUB_rowerowy_opis_i_kosztorys.pdf")
print("ok", len(w.pages))
