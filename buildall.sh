#!/bin/sh

for school in zs ss any; do
  mkdir -p "build/$school"

  for science in mat fyz inf other any; do
    python build.py --science $science --school $school -o "build/$school/$science.ics" --data-source http://data.kockatykalendar.sk/2020_21.json
  done
done
