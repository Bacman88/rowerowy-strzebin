# Rowerowy Strzebiń – HUB rowerowy

Propozycja oznakowania rowerowego dla **Sołectwa Strzebiń (gmina Koszęcin)**: tabliczki kierunkowe do miejscowości, szlaków i ciekawych miejsc, sieć ponumerowanych węzłów (słupków), dziewięć tras pokazowych – w tym rowerowy objazd drogi wojewódzkiej DW 906 – oraz mapa stanu dróg.

Projekt jest oddolny i ma charakter **propozycji do dyskusji** z sołectwem, gminą i nadleśnictwami. Przebieg tras wymaga potwierdzenia w terenie.

**Strona projektu:** gałąź [`strona`](../../tree/strona) (wdrażana automatycznie na hosting).

## Co jest w środku

| Folder | Zawartość |
|---|---|
| `skrypty/` | cały proces: dane → kierunki → tabliczki → mapy → trasy → paski → PDF → strona |
| `dane/` | wycinek OpenStreetMap, warstwa uMap z pomiarami dróg, zasięg Street View |
| `generator/` | generator tabliczek „HUB Strzebiń” (V21) – wzór graficzny tabliczek |
| `fonts/` | kroje: Inter, Fira Sans Condensed (licencja SIL OFL) |
| `vendor/leaflet/` | biblioteka mapy dla strony (BSD-2) |

## Jak przebudować wszystko

Wymagania: Python 3.10+, `rsvg-convert` (librsvg), `zip`, pakiety Pythona:

```bash
pip install networkx pyproj shapely geopandas matplotlib numpy reportlab pypdf pillow fonttools svgpath2mpl
```

Przebudowa (wszystkie wyniki trafiają do `out/`):

```bash
bash skrypty/rebuild.sh
```

Publikacja strony na gałąź `strona`:

```bash
bash skrypty/publikuj_strone.sh
```

## Najważniejsze wyniki (w `out/`)

- `Solectwo_Strzebin_jako_HUB_rowerowy.pdf` – komplet: opis, kosztorys, mapy, wykaz pasków, katalog
- `drogowskazy_trasy.pdf`, `drogowskazy_mapa.pdf`, `drogowskazy_mapa_strzebin.pdf`, `drogowskazy_stan_drog.pdf` – mapy A2 (+ wersje `A3_*`, `A4_*`)
- `tabliczki*/` – tabliczki do druku (SVG/PNG) w trzech wariantach płyty, z rysunkami montażowymi
- `naklejki_wezlow_*`, `paski_tras_*` – naklejki z numerami węzłów i paski tras na słupki
- `drogowskazy_objazd.pdf`, `objazd_gpx/` – odcinki do sprawdzenia w terenie
- `strona/` – strona internetowa projektu

## Gdzie co zmieniać

- słupki, statusy, cele lokalne: `skrypty/signs_data.py`
- kierunki na słupkach (przegląd ręczny): `skrypty/directions.py` (`MANUAL`)
- trasy pokazowe: `skrypty/trasy.py` (`ROUTES`), kolory tras: `skrypty/trasy_kolory.py`
- tekst opisu i kosztorys: `skrypty/opis_pdf.py`
- strona: `skrypty/strona_template.html`

## Licencje

- kod (`skrypty/`): MIT – plik `LICENSE`
- mapy, opisy i wzory tabliczek: CC BY 4.0 – z podaniem autora i źródła
- dane mapowe: © autorzy OpenStreetMap, licencja ODbL
- piktogramy: Tabler Icons (MIT), kroje: SIL OFL, Leaflet: BSD-2
