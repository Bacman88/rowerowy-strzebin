# Rowerowy Strzebiń – HUB rowerowy

Propozycja oznakowania rowerowego dla **Sołectwa Strzebiń (gmina Koszęcin)**: tabliczki kierunkowe do miejscowości, szlaków i ciekawych miejsc, sieć ponumerowanych węzłów (słupków), dziewięć tras pokazowych – w tym rowerowy objazd drogi wojewódzkiej DW 906 – oraz mapa stanu dróg.

Projekt jest oddolny i ma charakter **propozycji do dyskusji** z sołectwem, gminą i Nadleśnictwem Koszęcin. Przebieg tras wymaga potwierdzenia w terenie.

**Strona projektu:** https://rowerowy-strzebin.smart-ant.pl – gałąź [`strona`](../../tree/strona), folder `public/`. Hosting (Joton): katalog publikacji pusty, skrypt budowy `cp -r public/. ../../public_html/`, document root `/public_html`.

## Co jest w środku

| Folder | Zawartość |
|---|---|
| `skrypty/` | cały proces: dane → kierunki → tabliczki → mapy → trasy → paski → PDF → strona |
| `dane/` | wycinki OpenStreetMap (`osm2_clean` – okolice Strzebinia, do map PDF i tabliczek; `osm_gmina` – cała gmina Koszęcin z okolicą, do strony; `przygotuj_gmine.py`), granica gminy, warstwa uMap z pomiarami dróg, zasięg Street View, historia odcinków mapy wspólnej |
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

## Mapa wspólna (strona główna, sekcja 1) – stan dróg i miejsca od mieszkańców

Tryby: **Oceń drogi** i **Dodaj miejsce** (ławka, wiata, piknik/ognisko, punkt widokowy, ciekawe miejsce, serwis rowerowy – kliknięciem na mapie albo z lokalizacji telefonu). Miejsca: stałe w `dane/miejsca.geojson` + planowane stacje napraw + wiaty/widoki z OSM + zatwierdzone zgłoszenia; warstwy „serwis rowerowy” i „miejsca odpoczynku” na mapie głównej (`skrypty/www/lib/miejsca.js`).


Każdy może zaznaczyć odcinki dróg i ocenić ich stan (dobra / średnia / trudna / nieprzejezdna). Zgłoszenia trafiają do moderacji, na mapie pojawiają się po zatwierdzeniu w panelu `/admin/`.

- odcinki: `skrypty/odcinki.py` (wszystkie drogi z OSM w okolicy słupków, cięte na skrzyżowaniach i co ~400 m; stan początkowy z pomiarów w uMap),
- strona i API: `skrypty/www/` (`stan.html`, `api/*.php`, `admin/index.php`) – PHP 8, baza SQLite (domyślnie) albo MySQL.

Na serwerze, **obok** katalogu `public_html` (nie w nim), utwórz plik `hub_config.php`:

```php
<?php return [
  'admin_haslo' => 'długie-hasło-do-panelu',
  'sol'         => 'dowolny-losowy-ciąg',
  // 'powiadom' => 'adres@do.powiadomien',          // e-mail przy każdym nowym zgłoszeniu
  // MySQL zamiast SQLite:
  // 'dsn' => 'mysql:host=localhost;dbname=NAZWA;charset=utf8mb4', 'db_user' => '...', 'db_pass' => '...',
];
```

Trzeci tryb – **Tabliczki** (edytor węzłów): klik w węzeł → jego kierunki, usuń/dodaj kierunek (odległość, strzałka i kółka tras liczone w przeglądarce: `skrypty/www/lib/trasowanie.js`), podgląd tabliczek tym samym układem co `plates.py` (`skrypty/www/lib/tabliczka.js`); klik w puste miejsce → propozycja nowego węzła. Zatwierdzone zmiany: panel `/admin/` → „eksport węzłów” (JSON) – do wdrożenia w projekcie.

Czwarty tryb – **Twoja trasa** (kreator): kliknięte punkty łączone drogami z mapy wspólnej (to samo trasowanie co w edytorze, omija drogi trudne i nieprzejezdne), długość, udział nawierzchni/stanu, węzły po drodze; pobranie GPX, link `…/#trasa=lat,lon;lat,lon` i propozycja trasy (`api/trasy.php`, zakładka „Trasy” w panelu). Zatwierdzone trasy widać na mapie jako „trasy mieszkańców”.

Na mapie wspólnej: przełącznik **Zaznaczanie / Tylko oglądanie** i przycisk **Wyczyść** (zaznaczenia, pinezka, punkty trasy, punkt lokalizacji). Znaczniki każdego trybu są widoczne tylko w tym trybie.

**Edycja miejsc w panelu** (`/admin/?t=mapa`, „Miejsca na mapie – edycja”): każde miejsce na mapie (z OSM, z projektu, cele lokalne, zatwierdzone zgłoszenia) można przeciągnąć, zmienić mu rodzaj, nazwę i opis albo usunąć z mapy. Poprawki trafiają do tabeli `korekty_miejsc` (klucz miejsca `k` z `data.js`, np. `osm:node/123`, `poi:Zagroda u Czesi`, `db:12`) i działają od razu na stronie (`api/miejsca.php` zwraca je razem z miejscami). Cele lokalne są też na tabliczkach i mapach PDF – ich poprawki przenosi się do projektu z „eksport poprawek miejsc”.

**Zdjęcia**: przy ocenie drogi i nowym miejscu można dołączyć jedno zdjęcie. Przeglądarka zmniejsza je (najdłuższy bok 1280 px, JPEG ok. 100–400 kB), serwer zapisuje je w `hub_dane/zdjecia/` (poza `public_html`), widzi je tylko administrator w panelu i są **usuwane po zatwierdzeniu albo odrzuceniu** zgłoszenia.

Baza SQLite i kopie dobowe (JSON, ostatnie 60) zapisują się w `hub_dane/` obok `public_html` – wdrożenie ich nie nadpisuje. Kontakty są kasowane po roku, skróty IP po 30 dniach.

## Licencje

- kod (`skrypty/`): MIT – plik `LICENSE`
- mapy, opisy i wzory tabliczek: CC BY 4.0 – z podaniem autora i źródła
- dane mapowe: © autorzy OpenStreetMap, licencja ODbL
- piktogramy: Tabler Icons (MIT), kroje: SIL OFL, Leaflet: BSD-2
