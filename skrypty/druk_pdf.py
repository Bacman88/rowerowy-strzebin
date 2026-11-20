"""20.11.2026: wersja skrócona do druku A4 (wg Bartosza) – koncepcja, jedna tabliczka, jedna mapa tras.
Tekst czarny (przyjazny drukarce), kolorowe tylko tabliczka, paski tras i mapa.
Wynik: ../out/Solectwo_Strzebin_HUB_rowerowy_do_druku.pdf (4 strony A4: opis · jak to działa · mapa tras · koszty i kroki)."""
import json, csv, subprocess, collections
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader, PdfWriter
from shapely.geometry import shape
from shapely.ops import unary_union, transform
import warnings; warnings.filterwarnings("ignore", category=DeprecationWarning)
from pyproj import Transformer

S, O = "..", "../out"
for w in ("Regular", "SemiBold", "Bold"):
    pdfmetrics.registerFont(TTFont(f"Inter-{w}", f"{S}/fonts/Inter-{w}.ttf"))
registerFontFamily("Inter-Regular", normal="Inter-Regular", bold="Inter-Bold", italic="Inter-Regular", boldItalic="Inter-Bold")
INK, GREY, LINE, BG = colors.HexColor("#111111"), colors.HexColor("#444444"), colors.HexColor("#bbbbbb"), colors.HexColor("#f1f1f1")

base = dict(fontName="Inter-Regular", fontSize=10, leading=14, textColor=INK)
P = ParagraphStyle("p", **base, spaceAfter=5)
LEAD = ParagraphStyle("lead", **{**base, "fontSize": 11.3, "leading": 15.6}, spaceAfter=8)
H1 = ParagraphStyle("h1", fontName="Inter-Bold", fontSize=26, leading=30, textColor=INK, spaceAfter=3)
SUB = ParagraphStyle("sub", **{**base, "fontSize": 12, "leading": 16, "textColor": GREY}, spaceAfter=10)
KICK = ParagraphStyle("k", fontName="Inter-SemiBold", fontSize=9, leading=12, textColor=GREY, spaceAfter=3)
H2 = ParagraphStyle("h2", fontName="Inter-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=10, spaceAfter=5, keepWithNext=1)
BUL = ParagraphStyle("b", **base, leftIndent=11, bulletIndent=1, spaceAfter=3)
SMALL = ParagraphStyle("s", **{**base, "fontSize": 8.4, "leading": 11, "textColor": GREY}, spaceAfter=3)
CELL = ParagraphStyle("c", **{**base, "fontSize": 8.8, "leading": 11})
CELLB = ParagraphStyle("cb", **{**base, "fontName": "Inter-Bold", "fontSize": 8.8, "leading": 11})
BOXH = ParagraphStyle("bh", fontName="Inter-Bold", fontSize=10.5, leading=13, textColor=INK, spaceAfter=5)

def bullets(items, st=BUL): return [Paragraph(t, st, bulletText="•") for t in items]
def ramka(flow, W):
    t = Table([[flow]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BG), ("LINEBEFORE", (0, 0), (0, -1), 2.5, INK),
                           ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                           ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t
def table(rows, widths, bold_rows=()):
    data = [[Paragraph(c, CELLB) for c in rows[0]]] + [[c if not isinstance(c, str) else Paragraph(c, CELLB if i in bold_rows else CELL) for c in r]
                                                        for i, r in enumerate(rows[1:], 1)]
    t = Table(data, colWidths=widths)
    st = [("LINEBELOW", (0, 0), (-1, 0), 1, INK), ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    for i in bold_rows: st.append(("BACKGROUND", (0, i), (-1, i), BG))
    t.setStyle(TableStyle(st)); return t

STRONY = {1: 1, 2: 2, 3: 4}   # strona dokumentu → numer w złożonym PDF (strona 3 to mapa)
def footer(c, d):
    c.saveState(); c.setFont("Inter-Regular", 7.5); c.setFillColor(GREY)
    c.drawString(18 * mm, 10 * mm, "HUB rowerowy Strzebiń – koncepcja oznakowania · propozycja do dyskusji · wersja skrócona · listopad 2026")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, str(STRONY.get(d.page, d.page))); c.restoreState()

doc = BaseDocTemplate(f"{O}/_tmp/druk.pdf", pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=17 * mm,
                      title="HUB rowerowy Strzebiń – koncepcja (wersja do druku)", author="Bartosz")
doc.addPageTemplates([PageTemplate(frames=[Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="f")], onPage=footer)])
W = doc.width

# ---------- liczby z danych (te same reguły co opis_pdf.py) ----------
DP = json.load(open("signs_prop.json")); MF = json.load(open(f"{O}/tabliczki/manifest.json"))
TR = [r for r in json.load(open(f"{O}/drogowskazy_trasy.json")) if not r.get("alt")]
np_ = lambda p: len(MF.get(str(p["nr"]), []))
needpole = lambda p: p["pole"] == "nowy" or (p["pole"] == "opcjonalny" and not p.get("slup_jest"))
VAR = [(70, 110), (110, 160), (140, 200)]
def cost(ps):
    n = sum(np_(p) for p in ps); poles = sum(needpole(p) for p in ps)
    return [(poles * 280 + n * 30 + n * a, poles * 280 + n * 30 + n * b) for a, b in VAR]
f1 = lambda v: f"{v / 1000:.1f}".replace(".", ",")
rng = lambda ab: f"{f1(ab[0])}–{f1(ab[1])} tys. zł"
km = lambda v: f"{v:.1f}".replace(".", ",")
R1 = {k for k in TR[0]["seq"] if isinstance(k, int)}
e1 = [p for p in DP["posts"] if p["pole"] != "opcjonalny" or p["nr"] in R1]
e2 = [p for p in DP["posts"] if p not in e1]
E1, E2, ALL = cost(e1), cost(e2), cost(DP["posts"])
NPOST = len(DP["posts"]); NPL = sum(np_(p) for p in DP["posts"]); NE1 = sum(np_(p) for p in e1)
NEX1 = sum(1 for p in e1 if not needpole(p))
lo_hi = lambda v: f"{f1(v[0][0])}–{f1(v[2][1])} tys. zł"
_tf = Transformer.from_crs(4326, 2180, always_xy=True).transform
_las = transform(_tf, unary_union([shape(f["geometry"]).buffer(0) for f in json.load(open(f"{S}/dane/osm2_clean.geojson"))["features"]
                                   if f["geometry"]["type"] in ("Polygon", "MultiPolygon") and (f["properties"].get("landuse") == "forest" or f["properties"].get("natural") == "wood")])).buffer(15)
_siec = unary_union([transform(_tf, shape(f["geometry"])) for f in json.load(open(f"{O}/drogowskazy_trasy.geojson"))["features"] if str(f["properties"].get("alt")) != "True"])
KM_SIEC, KM_LAS = _siec.length / 1000, _siec.intersection(_las).length / 1000
N_LAS = sum(1 for p in DP["posts"] if p["who"] == "nadl_K")
T1 = TR[0]
SLOW = ['', 'jedną', 'dwie', 'trzy', 'cztery', 'pięć', 'sześć', 'siedem', 'osiem', 'dziewięć', 'dziesięć']

# ---------- strona 1: na czym polega projekt ----------
st = [Paragraph("SOŁECTWO STRZEBIŃ · GMINA KOSZĘCIN", KICK), Paragraph("HUB rowerowy Strzebiń", H1),
      Paragraph("Koncepcja oznakowania tras rowerowych wokół Strzebinia – wersja skrócona", SUB)]
st.append(ramka([Paragraph("W SKRÓCIE", BOXH)] + bullets([
    f"<b>{NPOST} węzłów z numerami i {NPL} tabliczek kierunkowych</b> – nazwa miejscowości lub miejsca, odległość po drogach i strzałka.",
    f"<b>{len(TR)} tras pokazowych, razem ok. {km(KM_SIEC)} km</b> – istniejącymi drogami, do Koszęcina, Kalet, Boronowa, Łaz, Psar, Babienicy, Drutarni i Sośnicy.",
    f"<b>Rowerowa obwodnica DW 906 – {km(T1['km'])} km</b> z Sośnicy przez Piasek, Bukowiec i Strzebiń do Prądów bocznymi ulicami i drogami leśnymi; "
    f"jezdnią drogi wojewódzkiej tylko ok. {T1['dw'] * 1000:.0f} m.",
    f"<b>Etap 1 – Strzebiń i obwodnica DW 906: {lo_hi(E1)}</b> ({len(e1)} słupków, w tym {NEX1} już stojących słupków z nazwami ulic).",
    f"<b>Etap 2 – trasy leśne z Nadleśnictwem Koszęcin: {lo_hi(E2)}</b>.",
], ParagraphStyle("bb", parent=BUL, spaceAfter=3.5)), W))
st.append(Spacer(1, 9))
st.append(Paragraph("Strzebiń jest ze wszystkich stron otoczony szlakami rowerowymi – od południa Leśno Rajza, od północy Liswarciański Szlak Rowerowy – "
                    "i w naturalny sposób stał się miejscem, w którym te trasy się spotykają. Proponuję ten HUB oznakować prostymi tabliczkami "
                    "kierunkowymi dla rowerzystów.", LEAD))
st.append(Paragraph("Czym jest projekt", H2))
st.append(Paragraph("<b>Lokalnym systemem informacji kierunkowej dla rowerzystów</b> – drogowskazami w miejscach, gdzie trzeba wybrać kierunek jazdy. "
                    "System <b>uzupełnia</b> istniejącą infrastrukturę: nie zastępuje znaków drogowych ani oficjalnych szlaków turystycznych.", P))
st += bullets([
    "<b>Węzły</b> – tabliczki w punktach rozjazdów; każdy słupek ma swój numer, ten sam na mapie, w aplikacji i na słupku.",
    "<b>Kierunki i odległości</b> – mówią, dokąd prowadzi droga i ile to kilometrów, niezależnie od konkretnej trasy.",
    "<b>Trasy pokazowe</b> – propozycje przejazdu istniejącymi drogami, a nie nowe szlaki do utrzymywania.",
    "<b>Własny, spójny wygląd</b> – wyraźnie inny niż znaki drogowe i szlaki PTTK."])
st.append(Paragraph("Po co to robimy", H2))
st += bullets([
    "<b>Bezpieczny objazd DW 906</b> – brak drogi rowerowej Bukowiec – Strzebiń – Prądy – Koszęcin to temat, który wraca od lat. "
    "Oznakowanie bocznych dróg, z utwardzeniem najgorszych odcinków, jest szybkie i wielokrotnie tańsze niż budowa drogi rowerowej.",
    "<b>Dla wszystkich mieszkańców</b> – także dla starszych osób i dzieci: po tabliczkach jedzie się bez telefonu i bez mapy.",
    "<b>Połączenia, o których mało kto wie</b> – wiele osób zna tylko główne drogi.",
    "<b>Turystyka i lokalne miejsca</b> – tabliczki poprowadzą do zabytków, miejsc odpoczynku i gastronomii; rowerzyści ze szlaków zatrzymają się w sołectwie.",
    "<b>Stan dróg</b> – mieszkańcy na bieżąco oceniają drogi na wspólnej mapie, więc wiadomo, które odcinki wymagają naprawy."])
st.append(PageBreak())

# ---------- strona 2: jak to działa – jedna tabliczka ----------
PL = f"{O}/_tmp/druk_tabliczka.png"
subprocess.run(["rsvg-convert", "-w", "2400", f"{O}/tabliczki/svg/S25_T1_lewo_800.svg", "-o", PL], check=True)
st.append(Paragraph("Jak to działa – przykładowa tabliczka", ParagraphStyle("h2t", parent=H2, spaceBefore=0)))
st.append(Paragraph("Tabliczka ze słupka nr 25 w centrum Strzebinia (skrzyżowanie przy DW 906). Wymiar 800 × 200 mm, nadruk dwustronny.", P))
st.append(Spacer(1, 3))
st.append(Image(PL, width=W * 0.86, height=W * 0.86 / 4, hAlign="CENTER"))
st.append(Spacer(1, 6))
OPIS = ParagraphStyle("op", **{**base, "fontSize": 9.6, "leading": 13.2}, spaceAfter=3)
st.append(table([["Element", "Co oznacza"],
    ["Strzałka (kształt tabliczki)", "kierunek jazdy – tabliczka sama wskazuje drogę"],
    ["Nazwa i odległość", "dokąd prowadzi droga i ile to kilometrów – liczone po drogach, a nie w linii prostej"],
    ["Kolorowe kółka z numerami", "trasy pokazowe jadące w tę stronę, w tych samych kolorach co na mapie (tu: trasa 1 do Prądów, trasy 4 i 6 do Koszęcina)"],
    ["Kolor tabliczki", "rodzaj celu: niebieski – miejscowości, zielony – szlaki, brązowy – historia i kultura, grafitowy – infrastruktura (np. stacja napraw), "
                        "pomarańczowy – sport, czerwony – gastronomia"],
    ["Piktogram", "rower, a przy celach lokalnych symbol miejsca (kościół, boisko, stacja napraw)"]],
    [44 * mm, W - 44 * mm]))
st.append(Spacer(1, 5))
st.append(Table([[Image(f"{O}/paski_demo.png", width=30 * mm, height=30 * 660 / 720 * mm),
    [Paragraph("Numer węzła i paski tras na słupku", BOXH),
     Paragraph("Numer słupka jest na opasce wokół słupka, widoczny z każdej strony. Pod nim paski w kolorach tras, które przez ten węzeł przebiegają. "
               "Rowerzysta jadący np. czerwoną trasą 1 na każdym słupku widzi swój czerwony pasek z „1”.", OPIS),
     Paragraph(f"<b>Montaż:</b> w etapie 1 aż {NEX1} z {len(e1)} słupków to już stojące słupki z nazwami ulic – tabliczki zawisłyby tuż pod nazwą ulicy, nie zasłaniając jej. "
               "Nowe słupki tylko tam, gdzie żadnego słupka nie ma.", OPIS)]]],
    colWidths=[35 * mm, W - 35 * mm], style=[("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
st.append(Paragraph("Trasy pokazowe (mapa na następnej stronie)", H2))
def kropka(c, n):
    t = Table([[Paragraph(f"<font color='white'><b>{n}</b></font>", ParagraphStyle("kk", **{**base, "fontSize": 8, "leading": 9.5, "alignment": 1}))]],
              colWidths=[5.4 * mm], rowHeights=[5.4 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(c)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return t
st.append(table([["", "Trasa", "km"]] + [[kropka(r["c"], r["id"]), f"<b>{r['name']}</b>" + (f" – {r['sub']}" if r["sub"] else ""), km(r["km"])] for r in TR],
                [9 * mm, W - 25 * mm, 16 * mm]))
st.append(PageBreak())

# ---------- strona 4: koszty, Nadleśnictwo, kolejne kroki ----------
st.append(Paragraph("Koszty (szacunkowe, brutto)", ParagraphStyle("h2k", parent=H2, spaceBefore=0)))
cw = (W - 62 * mm) / 3
st.append(table([["", "Wariant A – ekonomiczny", "Wariant B – standard", "Wariant C – najtrwalszy"],
                 [f"<b>Etap 1</b> – Strzebiń i obwodnica DW 906 ({len(e1)} słupków, {NE1} tabliczek)", *map(rng, E1)],
                 [f"<b>Etap 2</b> – trasy leśne i uzupełnienia ({len(e2)} słupków, {NPL - NE1} tabliczek)", *map(rng, E2)],
                 [f"Razem ({NPOST} słupków, {NPL} tabliczek)", *map(rng, ALL)]],
                [62 * mm, cw, cw, cw], bold_rows=(3,)))
st.append(Spacer(1, 4))
st += bullets([
    f"<b>A</b> – dibond, prostokąt z nadrukiem UV, ok. 3–5 lat ({VAR[0][0]}–{VAR[0][1]} zł za tabliczkę); "
    f"<b>B</b> – dibond cięty po obrysie, folia z laminatem UV, ok. 7 lat ({VAR[1][0]}–{VAR[1][1]} zł); "
    f"<b>C</b> – aluminium, folia odblaskowa, ok. 10–12 lat ({VAR[2][0]}–{VAR[2][1]} zł). Warianty można łączyć.",
    "W kwotach: tabliczki, mocowania (ok. 30 zł/szt.) i nowe słupki z montażem (ok. 280 zł/szt.). Ceny z ofert internetowych z listopada 2026 r. – do potwierdzenia zapytaniem ofertowym.",
    "Poza kosztorysem: ewentualne utwardzenie najgorszych odcinków dróg."], ParagraphStyle("bs", parent=BUL, fontSize=9.2, leading=12.6))
st.append(Spacer(1, 6))
st.append(ramka([Paragraph("TRASY LEŚNE – RAZEM Z NADLEŚNICTWEM KOSZĘCIN", BOXH), Paragraph(
    f"Około {KM_LAS / KM_SIEC * 100:.0f}% sieci tras ({km(KM_LAS)} z {km(KM_SIEC)} km) prowadzi drogami leśnymi, a {N_LAS} z {NPOST} proponowanych słupków "
    "stanęłoby w lasach Nadleśnictwa Koszęcin. Słupki w lasach wymagają jego zgody i wskazania dróg, po których można jeździć rowerem. "
    "Etap 1 prawie w całości dotyczy dróg gminnych, a trasy leśne z etapu 2 można uzgodnić w dalszej kolejności. "
    "Gmina i Nadleśnictwo mają siedziby w Koszęcinie, co ułatwia rozmowy.", P)], W))
st.append(Paragraph("Skąd wziąć środki", H2))
st += bullets([
    "<b>Fundusz sołecki</b> – oznakowanie można ująć we wniosku na 2028 r.",
    "<b>Konkurs marszałkowski „Inicjatywa Sołecka”</b> – kategoria turystyki i krajoznawstwa; wniosek składa gmina.",
    "<b>Budżet gminy</b> – zgodnie ze Strategią Rozwoju Gminy Koszęcin 2025–2035 (cel: oznakowane szlaki).",
    "<b>Partnerzy lokalni i czyn społeczny</b> – współfinansowanie przez lokale przy trasach na równych zasadach; montaż na istniejących słupkach i przeglądy tras."])
st.append(Paragraph("Kolejne kroki", H2))
KR = ParagraphStyle("kr", parent=BUL, leftIndent=14, bulletIndent=0)
st += [Paragraph(t, KR, bulletText=f"{i}.") for i, t in enumerate([
    "Omówienie koncepcji z Gminą Koszęcin, Radą Sołecką i mieszkańcami – wybór lokalizacji, celów i wariantu tabliczek.",
    "Uzgodnienie lokalizacji z zarządcami dróg, a tras leśnych z Nadleśnictwem Koszęcin.",
    "Zabezpieczenie środków na etap 1 i zapytanie ofertowe.",
    "Montaż etapu 1 i ustalenie, kto dba o tabliczki po montażu (zgłaszanie uszkodzeń, wymiana).",
    "Etap 2 – trasy leśne, po uzgodnieniach z Nadleśnictwem."], 1)]
st.append(Spacer(1, 8))
st.append(ramka([Paragraph("Pełna wersja projektu – mapy wszystkich słupków, katalog tabliczek, kosztorys szczegółowy i mapa stanu dróg – "
                           "oraz wspólna mapa, na której mieszkańcy oceniają drogi: <b>rowerowy-strzebin.smart-ant.pl</b>", P)], W))
doc.build(st)

# ---------- złożenie: strony 1–2 opisu, mapa tras A4 (pionowo), strona z kosztami ----------
r, m = PdfReader(f"{O}/_tmp/druk.pdf"), PdfReader(f"{O}/A4_mapa_trasy.pdf")
assert len(r.pages) == 3, f"opis do druku ma {len(r.pages)} stron zamiast 3 – skróć tekst"
w = PdfWriter()
for pg in (r.pages[0], r.pages[1], m.pages[0], r.pages[2]): w.add_page(pg)
w.add_metadata({"/Title": "HUB rowerowy Strzebiń – koncepcja (wersja skrócona do druku)", "/Author": "Bartosz"})
with open(f"{O}/Solectwo_Strzebin_HUB_rowerowy_do_druku.pdf", "wb") as f: w.write(f)
print("druk: 4 strony A4 →", f"{O}/Solectwo_Strzebin_HUB_rowerowy_do_druku.pdf")
