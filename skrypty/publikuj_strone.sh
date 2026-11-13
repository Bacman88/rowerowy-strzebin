#!/usr/bin/env bash
# Publikuje zbudowaną stronę (out/strona) na gałąź "strona" – jeden commit, nadpisywany przy każdej publikacji.
# Układ gałęzi: public/ (strona) + .github/workflows/apk.yml (budowanie APK).
# Joton: katalog publikacji PUSTY, skrypt budowy "cp -r public/. ../../public_html/",
#        document root /public_html (kopiuje z deploys/<commit>/ do public_html).
# Opcjonalnie: TRAILER="..." dopisuje linie na końcu opisu commita.
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SRC="$ROOT/out/strona"
[ -f "$SRC/index.html" ] || { echo "Najpierw: bash skrypty/rebuild.sh"; exit 1; }
# strona.py czyści out/strona – bez odcinki.py mapa wspólna nie ma dróg
[ -f "$SRC/stan/odcinki.js" ] && [ -f "$SRC/api/_odcinki.json" ] && [ -f "$SRC/stan/jedz.js" ] || { echo "Brak stan/odcinki.js lub stan/jedz.js – uruchom odcinki.py i jedz_dane.py (koniec rebuild.sh)"; exit 1; }
TMP=$(mktemp -d); mkdir -p "$TMP/public"
cp -r "$SRC"/. "$TMP/public"/
cp "$ROOT/joton/.htaccess" "$TMP/public/"
[ -f "$ROOT/CNAME" ] && cp "$ROOT/CNAME" "$TMP/public/"
# budowanie aplikacji na Androida po każdej publikacji (GitHub uruchamia workflow z gałęzi, na którą wypchnięto zmiany)
mkdir -p "$TMP/.github/workflows" && cp "$ROOT/.github/workflows/apk.yml" "$TMP/.github/workflows/"
MSG="Strona: $(date +%F)"
[ -n "$TRAILER" ] && MSG="$MSG

$TRAILER"
cd "$TMP"; git init -q -b strona; git add -A
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" commit -qm "$MSG"
git push -q -f "$(git -C "$ROOT" remote get-url origin)" strona:strona
rm -rf "$TMP"; echo "Opublikowano gałąź 'strona'"
