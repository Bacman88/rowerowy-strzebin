#!/usr/bin/env bash
# Publikuje zbudowaną stronę (out/strona) na gałąź "strona" – jeden commit, nadpisywany przy każdej publikacji.
# Układ gałęzi: public/ (strona) + scripts/publish-webroot.mjs + package.json.
# Joton: katalog publikacji PUSTY, skrypt budowy "node scripts/publish-webroot.mjs public",
#        document root /public_html (skrypt kopiuje public/ do ../../public_html).
# Opcjonalnie: TRAILER="..." dopisuje linie na końcu opisu commita.
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SRC="$ROOT/out/strona"
[ -f "$SRC/index.html" ] || { echo "Najpierw: bash skrypty/rebuild.sh"; exit 1; }
TMP=$(mktemp -d); mkdir -p "$TMP/public" "$TMP/scripts"
cp -r "$SRC"/. "$TMP/public"/
cp "$ROOT/joton/.htaccess" "$TMP/public/"
cp "$ROOT/joton/publish-webroot.mjs" "$TMP/scripts/"
cp "$ROOT/joton/package.json" "$TMP/"
[ -f "$ROOT/CNAME" ] && cp "$ROOT/CNAME" "$TMP/public/"
# próba na sucho: czy skrypt kopiujący działa na tym, co wypychamy
W=$(mktemp -d); ( cd "$TMP" && WEBROOT="$W" node scripts/publish-webroot.mjs public ); rm -rf "$W"
MSG="Strona: $(date +%F)"
[ -n "$TRAILER" ] && MSG="$MSG

$TRAILER"
cd "$TMP"; git init -q -b strona; git add -A
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" commit -qm "$MSG"
git push -q -f "$(git -C "$ROOT" remote get-url origin)" strona:strona
rm -rf "$TMP"; echo "Opublikowano gałąź 'strona'"
