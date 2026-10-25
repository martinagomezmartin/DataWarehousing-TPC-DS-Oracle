#!/bin/bash
set -eu
source oracle.env

SF="${1:?Usage : bash run_load.sh SCALE}"

DEBUT=$(date +%s%3N)

python Scripts/load_data.py \
    --create-tables \
    --data-dir "data/SF$SF" \
    --user "$ORACLE_USER" \
    --password "$ORACLE_PASSWORD"

MS=$(( $(date +%s%3N) - DEBUT ))

mkdir -p results
[[ -f results/load.csv ]] || echo "scale,T_load_s" > results/load_SF$SF.csv

printf '%s,%d.%03d\n' \
    "$SF" "$((MS/1000))" "$((MS%1000))" >> results/load_SF$SF.csv