#!/usr/bin/env bash
# Kopiuje pliki nawigacji „Jedź” z opublikowanej strony (gałąź `strona`, katalog public/) do www/ aplikacji
# i podmienia linki względne na adresy strony (w aplikacji nie ma reszty witryny).
# Użycie: bash przygotuj.sh <ścieżka do public/>
set -euo pipefail
SRC="$1"; DST="$(dirname "$0")/www"
rm -rf "$DST"; mkdir -p "$DST/lib/fonts" "$DST/stan"
cp "$SRC/jedz.html" "$DST/index.html"
cp "$SRC/data.js" "$SRC/favicon.svg" "$SRC/ikona-192.png" "$SRC/apple-touch-icon.png" "$DST/"
cp "$SRC"/lib/{jedz.js,leaflet.js,leaflet.css,ikony.js,tabliczka-dane.js,tabliczka.js} "$DST/lib/"
mkdir -p "$DST/lib/jedz" && cp "$SRC"/lib/jedz/*.js "$DST/lib/jedz/"
cp "$SRC/lib/fonts/FiraSansCondensed-SemiBold.ttf" "$DST/lib/fonts/"
[ -d "$SRC/lib/images" ] && cp -r "$SRC/lib/images" "$DST/lib/"
cp "$SRC/stan/odcinki.js" "$SRC/stan/jedz.js" "$DST/stan/"
[ -f "$SRC/stan/podklad.js" ] && cp "$SRC/stan/podklad.js" "$DST/stan/" || echo "window.PODKLAD=null;" > "$DST/stan/podklad.js"
[ -f "$SRC/stan/wysokosci.js" ] && cp "$SRC/stan/wysokosci.js" "$DST/stan/" || echo "window.WYS=null;" > "$DST/stan/wysokosci.js"
STRONA="https://rowerowy-strzebin.smart-ant.pl/"
sed -i -e "s|href=\"\./\"|href=\"$STRONA\"|g" -e "s|href=\"polityka-prywatnosci.html\"|href=\"${STRONA}polityka-prywatnosci.html\"|g" \
       -e 's|<link rel="manifest" href="jedz.webmanifest">||' "$DST/index.html"
# biblioteka Capacitora (bez bundlera): udostępnia wtyczki natywne – BackgroundGeolocation, TextToSpeech, LocalNotifications
cp "$(dirname "$0")/node_modules/@capacitor/core/dist/capacitor.js" "$DST/capacitor-core.js"
sed -i 's|<script src="lib/jedz.js"></script>|<script src="capacitor-core.js"></script>\n<script src="lib/jedz.js"></script>|' "$DST/index.html"
grep -q capacitor-core.js "$DST/index.html" || { echo "brak capacitor-core.js w index.html"; exit 1; }
echo "www gotowe: $(du -sh "$DST" | cut -f1)"
