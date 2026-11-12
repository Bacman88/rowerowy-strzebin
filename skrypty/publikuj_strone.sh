#!/usr/bin/env bash
# Publikuje zbudowaną stronę (out/strona) na gałąź "strona" – jeden commit, nadpisywany przy każdej publikacji.
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SRC="$ROOT/out/strona"
[ -f "$SRC/index.html" ] || { echo "Najpierw: bash skrypty/rebuild.sh"; exit 1; }
TMP=$(mktemp -d); cp -r "$SRC"/. "$TMP"/
[ -f "$ROOT/CNAME" ] && cp "$ROOT/CNAME" "$TMP/"
cd "$TMP"; git init -q -b strona; git add -A
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" commit -qm "Strona: $(date +%F)"
git push -f "$(git -C "$ROOT" remote get-url origin)" strona:strona
rm -rf "$TMP"; echo "Opublikowano gałąź 'strona'"
