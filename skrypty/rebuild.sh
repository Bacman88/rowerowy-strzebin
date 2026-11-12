#!/usr/bin/env bash
# Przebudowa całego projektu: dane -> kierunki -> tabliczki -> mapy -> trasy -> paski -> PDF -> strona.
# Uruchom z dowolnego miejsca:  bash skrypty/rebuild.sh      (wyniki w out/)
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; cd "$HERE"
D=../dane; O=../out; GEN=../generator/generator_drogowskazow.html
SV=$D/umap_mapa_rowerowa.geojson; M1=$D/streetview_zasieg_1.png; M2=$D/streetview_zasieg_2.png
mkdir -p $O/_tmp
python3 -I signs_data.py $D/osm2_clean.geojson "$SV" signs.json 2>&1 | grep POI || true
python3 -I directions.py $D/osm2_clean.geojson signs.json signs_prop.json kierunki_raport.json "$SV" >/dev/null
# trasy przed tabliczkami: V22 – numery tras w kółkach na tabliczkach wg przebiegu tras
python3 -I trasy.py $D/osm2_clean.geojson "$SV" signs_prop.json $O/drogowskazy | tail -1
for v in "tabliczki" "tabliczki_pojedyncze --single" "tabliczki_prostokatne --plate=rect" "tabliczki_prostokatne_zaokraglone --plate=roundrect"; do
  set -- $v; python3 -I plates.py signs_prop.json $GEN $O/$1 $2 | head -1
done
python3 -I signs_render.py $D/osm2_clean.geojson "$SV" signs_prop.json $O/drogowskazy $M1 $M2 --manifest=$O/tabliczki/manifest.json | tail -1
python3 -I signs_render.py $D/osm2_clean.geojson "$SV" signs_prop.json $O/drogowskazy $M1 $M2 --zoom --manifest=$O/tabliczki/manifest.json | tail -1
rm -rf $O/_tmp/S; mkdir -p $O/_tmp/S
python3 -I signs_render.py $D/osm2_clean.geojson "$SV" signs_prop.json $O/_tmp/S/drogowskazy $M1 $M2 --single --manifest=$O/tabliczki_pojedyncze/manifest.json | tail -1
mv $O/_tmp/S/drogowskazy_katalog.pdf $O/drogowskazy_katalog_pojedyncze.pdf
python3 -I gaps.py $D/osm2_clean.geojson "$SV" signs_prop.json $O/drogowskazy | tail -1
python3 paski.py
python3 kropki.py
python3 -I skaluj_mapy.py
( cd $O && python3 -c "
from pypdf import PdfWriter;w=PdfWriter();[w.append(f) for f in ['drogowskazy_mapa.pdf','drogowskazy_mapa_strzebin.pdf']];w.write('drogowskazy_mapy_komplet.pdf')"
  rm -f tabliczki_SVG.zip; zip -qr tabliczki_SVG.zip tabliczki tabliczki_pojedyncze tabliczki_prostokatne tabliczki_prostokatne_zaokraglone -x '*/png/*' )
python3 -I export_umap.py
python3 -I opis_pdf.py
python3 -I trasy.py $D/osm2_clean.geojson "$SV" signs_prop.json $O/drogowskazy --objazd | tail -1
python3 strona.py
python3 -I -W ignore odcinki.py $D/osm2_clean.geojson "$SV" signs_prop.json $O/strona
echo "Gotowe – wyniki w $(cd $O && pwd)"
