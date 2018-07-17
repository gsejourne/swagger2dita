#!/bin/bash

# Usage: ./build.sh SWAGGER_DIR_SRC RESOURCES_DIR
# RESOURCES DIR typically contains the structure map, and other side files, (images, ant build file, etc.) which get copied onto the dist/ directory
# SWAGGER_DIR_SRC contains the swagger definititions files

src="$1"
res="$2"
map="$2/map.ditamap"
rm -rf './dist'
mkdir -p './dist'

# Convert each swagger def to DITA
for d in `ls $src`; do
    echo '============================================='
    python py/swagger2dita.py -i $src'/'$d'/swagger.yaml'
done

# Copy resources to dist/ dir
cp -r "$res"/* dist/.

# Feed chapters to default map
sed -e '/__CHAPTERS_LIST__/ {
r ./dist/maps.list
d }' < "$map" > ./dist/map.ditamap
now=`date +%Y-%m-%d`
sed -ie "/__DATE__/$now/g" ./dist/map.ditamap