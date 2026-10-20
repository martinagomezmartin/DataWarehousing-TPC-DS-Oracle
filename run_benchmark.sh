#!/usr/bin/env bash
set -eu 
cd "$(dirname "$0")"


SCALE="${1:?Usage: bash run_benchmark.sh SCALE }"
FIRST="${2:?Specify the first stream}"
LAST="${3:-$FIRST}"

if [[ "$FIRST" == 0 && "$LAST" == 0 ]]; then
    TEST="power"
elif [[ "$FIRST" == 1 && "$LAST" == 4 ]]; then
    TEST="throughput1"
elif [[ "$FIRST" == 5 && "$LAST" == 8 ]]; then
    TEST="throughput2"
else
    echo "Choose stream 0, streams 1-4, or streams 5-8." >&2
    exit 1
fi

OUTPUT="results/SF${SCALE}/$(TZ=Europe/Brussels date +%Y-%m-%d_%H-%M-%S)_${TEST}"
mkdir -p "results/SF${SCALE}"
mkdir "$OUTPUT"  # Do not overwrite results of a previous run.

if [[ "$FIRST" == 0 ]]; then
    python benchmark_queries.py 0 "$OUTPUT"
else
    pids=()
    for stream in $(seq "$FIRST" "$LAST"); do
        python benchmark_queries.py "$stream" "$OUTPUT" &
        pids+=("$!")
    done
    failed=0
    for pid in "${pids[@]}"; do
        wait "$pid" || failed=1
    done
    if (( failed )); then
        echo "Some streams failed" >&2
        exit 1
    fi
fi

echo "Raw results: $OUTPUT"
