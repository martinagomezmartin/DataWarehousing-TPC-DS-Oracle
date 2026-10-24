#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"


SCALE="${1:?Usage: ./run_data_maintenance.sh SCALE FIRST_RUN LAST_RUN [--rollback]}"
FIRST="${2:?Specify the first refresh run}"
LAST="${3:-$FIRST}"

if [[ "$FIRST" == 1 && "$LAST" == 2 ]]; then
    TEST="dm1"
elif [[ "$FIRST" == 3 && "$LAST" == 4 ]]; then
    TEST="dm2"
else
    echo "Choose refresh runs 1-2 (DM1) or 3-4 (DM2)." >&2
    exit 1
fi

OUTPUT="results/SF${SCALE}/$(TZ=Europe/Brussels date +%Y-%m-%d_%H-%M-%S)_${TEST}"
mkdir -p "results/SF${SCALE}"
mkdir "$OUTPUT"  # Do not overwrite results of a previous run.

python data_maintenance.py run "$FIRST" "$LAST" "$OUTPUT" \
    --data-dir "tpcds-data.nosync/sf${SCALE}_update" "${@:4}"
