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

## Nawigacja „Jedź” (beta) – `jedz.html`
Osobna strona do nawigacji na telefonie (można dodać do ekranu głównego jak aplikację – PWA).
- Trasa liczona w telefonie po drogach z mapy wspólnej (`stan/odcinki.js`), tryby: **Bezpieczna** (drogi wojewódzkie i krajowe ×6 – krótki odcinek przejdzie, dłuższy objedzie; poza odcinkami z drogą rowerową obok; trasy HUB ×0,9) i **Najkrótsza** (sama długość).
- `skrypty/jedz_dane.py` (po `odcinki.py`) → `stan/jedz.js`: odcinki na trasach i odcinki DW z ciągiem pieszo-rowerowym (z pomiarów uMap).
- Prowadzenie „następny kierunek”: przy przyszłych drogowskazach – tabliczka tak, jak widzi ją nadjeżdżający; poza nimi – skręty z nazwami ulic. Zejście z trasy → przeliczenie od bieżącej pozycji.
- Kierunek tabliczki: pole `g` (azymut) w `data.js` (strona.py). Symulacja przejazdu do testów w domu.
- Profil trasy: wykres wysokości (pole w kolorach nawierzchni) i pasek nawierzchni; przeciąganie palcem pokazuje miejsce na mapie.
  `skrypty/wysokosci.py` (po `jedz_dane.py`) → `stan/wysokosci.js`: wysokości co 25 m wzdłuż odcinków z NMT GUGiK (siatka 5 m).
  Model terenu (`dane/nmt.npz`, poza repo) pobiera się sam z wydania `nmt` – tworzy je workflow NMT na gałęzi `wysokosci` (WCS GUGiK).
- Czas jazdy: prędkość zależna od nawierzchni (17 km/h utwardzona, 13 średnia/bez oceny, 9 trudna) i nachylenia (pod górę wolniej, z górki szybciej);
  tryb **Szosowa** (pojawia się przy rowerze szosowym): „prawie jak autem” – asfalt i drogi główne, także wojewódzkie i krajowe; nieutwardzone mocno omija (autostrad i ekspresówek nie ma w sieci dróg);
  rodzaj roweru (miejski – domyślny, trekkingowy, szosowy, gravel, górski, elektryczny) zmienia tylko czas: prędkość na gorszych nawierzchniach,
  podjazdy i prędkość maksymalną – trasy nie zmienia; szosówka dostaje ostrzeżenie o odcinkach nieutwardzonych, inne rowery (poza górskim i gravelem) o trudnych;
  suwak „Twoje tempo na płaskim” (8–40 km/h, domyślnie 16, zapamiętany w telefonie) skaluje te prędkości;
  w trakcie jazdy czas dojazdu i godzina przyjazdu dopasowują się do Twojego tempa (postoje się nie liczą).

- **Mapa offline**: własny podkład rysowany w telefonie (`lib/jedz/podklad.js`) z `stan/podklad.js` – lasy, wody, zabudowa, budynki, tory, nazwy
  z OpenStreetMap (workflow „Podklad” na gałęzi `wysokosci` → wydanie `podklad`; `skrypty/podklad.py` w rebuild) + nasze drogi. Leży pod kafelkami OSM:
  bez zasięgu widać ją sama, można też wybrać „zawsze offline”. Kafelków OSM nie pobieramy hurtowo (zakazują tego zasady serwerów OSM).
- **Kod**: `lib/jedz/wspolne.js` → `graf.js` (trasowanie) → `profil.js` (rower, tempo, wysokości, czas, wykres) → `manewry.js` → `podklad.js` → `lib/jedz.js` (interfejs);
  wspólna przestrzeń `window.JZ`. Testy tras bez przeglądarki: `node skrypty/test_jedz.js out/strona` (koniec rebuild.sh), interfejsu w trybie strony
  i udawanej aplikacji: `skrypty/test_jedz_ui.js` (Playwright) – oba uruchamia `publikuj_strone.sh` i przerywa publikację przy błędzie.
- Mapa offline jest **na życzenie**: przycisk „Pobierz mapę offline (2,8 MB)” na ekranie startowym i w podglądzie trasy; bez tego rysujemy tylko nasze drogi.

- **Zgłoś błąd / sugestię**: `lib/uwagi.js` (okienko wspólne dla strony i Jedź, także w aplikacji) → `api/uwagi.php` (CORS dla aplikacji) → tabela `uwagi`,
  zakładka „Uwagi i błędy” w panelu i e-mail (bez kontaktu i bez trasy). Trasa (start/cel/tryb/rower) tylko po zaznaczeniu „Dołącz tę trasę”.

## Aplikacja na Androida (`aplikacja/`)
Capacitor opakowuje stronę „Jedź” w aplikację z lokalizacją w tle (usługa z powiadomieniem – nawigacja na zgaszonym ekranie) i głosem (syntezator telefonu).
- Budowanie: GitHub Actions (`.github/workflows/apk.yml`) po każdej publikacji strony; pliki brane z gałęzi `strona` (`aplikacja/przygotuj.sh`), APK trafia do wydań („Releases”).
- `beta-debug.keystore` – klucz tylko do wersji testowych instalowanych poza sklepem (żeby aktualizacje instalowały się na starą wersję). Do Sklepu Play – osobny klucz w sekretach repozytorium.
