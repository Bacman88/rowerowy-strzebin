"""Wersje A3/A4 map A2 (skalowanie wektorowe)."""
from pypdf import PdfReader, PdfWriter, Transformation, PageObject
O = "../out"
MAPS = [("drogowskazy_trasy.pdf", "mapa_trasy"), ("drogowskazy_mapa.pdf", "mapa_wszystkie_slupki"), ("drogowskazy_mapa_strzebin.pdf", "mapa_strzebin"),
        ("drogowskazy_stan_drog.pdf", "mapa_stan_drog")]
for fmt, k in (("A3", 1 / 2 ** 0.5), ("A4", 0.5)):
    allw = PdfWriter()
    for src, name in MAPS:
        pg = PdfReader(f"{O}/{src}").pages[0]
        W, H = float(pg.mediabox.width), float(pg.mediabox.height)
        new = PageObject.create_blank_page(width=W * k, height=H * k)
        new.merge_transformed_page(pg, Transformation().scale(k, k))
        w = PdfWriter(); w.add_page(new); w.write(f"{O}/{fmt}_{name}.pdf"); allw.add_page(new)
    allw.write(f"{O}/{fmt}_mapy_komplet.pdf")
print("ok A3/A4")
