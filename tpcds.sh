#!/usr/bin/env bash
# Single entry point of the TPC-DS benchmark on Oracle (replaces run_load.sh,
# run_benchmark.sh and run_data_maintenance.sh). Oracle settings come from .env.
set -eu
cd "$(dirname "$0")"

SF_DIR="SupportingFiles"
PYTHON="${PYTHON:-python}"

usage() {
    cat <<'EOF'
Usage: ./tpcds.sh <command> [arguments]

Preparation
  build                      compile dsdgen and dsqgen (TPC-DS kit in TPCDS_TOOLS)
  generate SF [SF ...]       dsdgen: base data sf<SF> + refresh data sets 1-4 (not timed)
  validate                   compare the 99 qualification queries with the official answer sets (SF1)

Benchmark (spec 7.4.2: load, power, throughput 1, dm 1, throughput 2, dm 2)
  load SF                    drop the schema, create tables, load sf<SF>, statistics   -> T_Load
  power SF                   Power Test, stream 0                                      -> T_Power
  throughput SF 1|2          Throughput Test 1 (streams 1-4) or 2 (streams 5-8)        -> T_TT1 / T_TT2
  dm SF 1|2 [--rollback]     Data Maintenance Test 1 (refresh runs 1-2) or 2 (3-4)     -> T_DM1 / T_DM2
  all SF [SF ...]            the six tests above, in order, for each scale factor, then metrics
  metrics                    T_* and QphDS@SF of the latest complete run of each SF -> results/metrics.csv
  report                     final report (tables + figures + raw CSV) in Report/results/
  dm-setup                   recreate the data maintenance staging tables and views

Results: results/SF<SF>/<date>_<test>/
EOF
}

die() {
    echo "Error: $*" >&2
    exit 1
}

[[ -f .env ]] || die "missing .env, run 'cp .env.example .env' and put your Oracle settings in it"
set -a
source .env
set +a
: "${ORACLE_USER:?set ORACLE_USER in .env}" "${ORACLE_PASSWORD:?set ORACLE_PASSWORD in .env}"
ORACLE_HOST="${ORACLE_HOST:-localhost}"
ORACLE_PORT="${ORACLE_PORT:-1521}"
ORACLE_SERVICE="${ORACLE_SERVICE:-FREEPDB1}"
DATA_DIR="${DATA_DIR:-tpcds-data.nosync}"
TPCDS_TOOLS="${TPCDS_TOOLS:-tpcds/DSGen-software-code-4.0.0/tools}"
export ORACLE_DSN="$ORACLE_HOST:$ORACLE_PORT/$ORACLE_SERVICE"


new_output() {
    # results/SF<scale>/<timestamp>_<test>, never overwritten
    local dir
    dir="results/SF$1/$(TZ=Europe/Brussels date +%Y-%m-%d_%H-%M-%S)_$2"
    mkdir -p "results/SF$1"
    mkdir "$dir"
    echo "$dir"
}

now_ms() {
    # date +%s%3N does not work on macOS
    "$PYTHON" -c 'import time; print(time.time_ns() // 1_000_000)'
}

relative_to() {
    # dsdgen truncates long absolute paths: give it a path relative to the kit
    "$PYTHON" -c 'import os, sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$1" "$2"
}

run_sql() {
    "$PYTHON" - "$1" <<'EOF'
import os, sys
import oracledb
with oracledb.connect(user=os.environ["ORACLE_USER"], password=os.environ["ORACLE_PASSWORD"],
                      dsn=os.environ["ORACLE_DSN"]) as connection:
    connection.cursor().execute(sys.argv[1])
EOF
}

confirm_drop() {
    local answer
    read -r -p "This drops every table and view of $ORACLE_USER. Continue? [y/N] " answer
    [[ "$answer" == [yY] ]] || exit 1
}

check_scale() {
    [[ "${1:-}" =~ ^[0-9]+$ ]] || die "the scale factor must be an integer (dsdgen -scale)"
}


cmd_build() {
    [[ -d "$TPCDS_TOOLS" ]] || die "TPC-DS kit not found in $TPCDS_TOOLS"
    (
        cd "$TPCDS_TOOLS"
        [[ -f Makefile ]] || cp Makefile.suite Makefile
        if [[ "$(uname)" == Darwin ]]; then
            # The kit expects the Linux headers values.h and malloc.h
            mkdir -p macos_include
            printf '#include <limits.h>\n#include <float.h>\n#ifndef MAXINT\n#define MAXINT INT_MAX\n#endif\n' \
                > macos_include/values.h
            printf '#include <stdlib.h>\n' > macos_include/malloc.h
            # _FORTIFY_SOURCE=0: macOS aborts dsdgen -update from SF2 on a false buffer overflow
            make OS=LINUX LINUX_CFLAGS="-g -D_FORTIFY_SOURCE=0 -Wno-implicit-function-declaration -Wno-implicit-int \
                -Wno-int-conversion -Wno-deprecated-non-prototype -I$PWD/macos_include" dsdgen dsqgen
        else
            make OS=LINUX dsdgen dsqgen
        fi
    )
}

cmd_generate() {
    # Spec 3 (database population) and 5.2 (refresh data sets 1..Sq): not timed
    local sf="$1" base update n
    [[ -x "$TPCDS_TOOLS/dsdgen" ]] || die "dsdgen is not built, run './tpcds.sh build'"
    mkdir -p "$DATA_DIR/sf$sf" "$DATA_DIR/sf${sf}_update"
    base=$(relative_to "$DATA_DIR/sf$sf" "$TPCDS_TOOLS")
    update=$(relative_to "$DATA_DIR/sf${sf}_update" "$TPCDS_TOOLS")
    (
        cd "$TPCDS_TOOLS"
        ./dsdgen -scale "$sf" -dir "$base" -force Y
        for n in 1 2 3 4; do
            ./dsdgen -scale "$sf" -dir "$update" -update "$n" -force Y
        done
    )
}

cmd_metrics() {
    "$PYTHON" "$SF_DIR/Clause7/compute_metrics.py" results
}

cmd_report() {
    "$PYTHON" "$SF_DIR/Clause7/benchmark_report.py" results Report/results
}

cmd_validate() {
    "$PYTHON" "$SF_DIR/Clause4/check_queries.py" \
        --query-dir "$SF_DIR/Clause4/queries_archive/qualification" \
        --answers-dir "$TPCDS_TOOLS/../answer_sets" \
        --user "$ORACLE_USER" --password "$ORACLE_PASSWORD" \
        --host "$ORACLE_HOST" --port "$ORACLE_PORT" --service "$ORACLE_SERVICE"
}

cmd_dm_setup() {
    "$PYTHON" "$SF_DIR/Clause5/data_maintenance.py" setup
}

cmd_load() {
    local sf="$1" data="$DATA_DIR/sf$1" output start ms
    [[ -d "$data" ]] || die "no data in $data, run './tpcds.sh generate $sf'"
    [[ -f "$SF_DIR/Clause2/tpcds_oracle.sql" ]] || die "$SF_DIR/Clause2/tpcds_oracle.sql (table DDL) is missing"
    [[ "${ASSUME_YES:-0}" == 1 ]] || confirm_drop

    echo "Dropping existing tables and views (not timed)..."
    run_sql "BEGIN
        FOR v IN (SELECT view_name FROM user_views) LOOP
            EXECUTE IMMEDIATE 'DROP VIEW \"' || v.view_name || '\"';
        END LOOP;
        FOR t IN (SELECT table_name FROM user_tables) LOOP
            EXECUTE IMMEDIATE 'DROP TABLE \"' || t.table_name || '\" CASCADE CONSTRAINTS PURGE';
        END LOOP;
    END;"

    # T_Load (spec 7.4.3.7): tables, data, statistics and the objects needed by the
    # performance test (data maintenance staging tables and views)
    output=$(new_output "$sf" load)
    start=$(now_ms)
    "$PYTHON" "$SF_DIR/Clause3/load_data.py" --create-tables --data-dir "$data" \
        --user "$ORACLE_USER" --password "$ORACLE_PASSWORD" \
        --host "$ORACLE_HOST" --port "$ORACLE_PORT" --service "$ORACLE_SERVICE"
    echo "Gathering statistics..."
    run_sql "BEGIN DBMS_STATS.GATHER_SCHEMA_STATS(USER); END;"
    cmd_dm_setup
    ms=$(( $(now_ms) - start ))

    printf 'scale,T_load_s\n%s,%d.%03d\n' "$sf" $((ms / 1000)) $((ms % 1000)) > "$output/load.csv"
    printf 'T_Load = %d.%03ds\nRaw results: %s\n' $((ms / 1000)) $((ms % 1000)) "$output"
}

cmd_power() {
    local output
    output=$(new_output "$1" power)
    "$PYTHON" "$SF_DIR/Clause7/benchmark_queries.py" 0 "$output"
    echo "Raw results: $output"
}

cmd_throughput() {
    local sf="$1" first last output stream failed=0 pids=()
    case "${2:-}" in
        1) first=1; last=4 ;;
        2) first=5; last=8 ;;
        *) die "throughput test must be 1 (streams 1-4) or 2 (streams 5-8)" ;;
    esac
    output=$(new_output "$sf" "throughput$2")
    for stream in $(seq "$first" "$last"); do
        "$PYTHON" "$SF_DIR/Clause7/benchmark_queries.py" "$stream" "$output" &
        pids+=("$!")
    done
    for pid in "${pids[@]}"; do
        wait "$pid" || failed=1
    done
    (( failed == 0 )) || die "some streams failed"
    echo "Raw results: $output"
}

cmd_dm() {
    local sf="$1" test="${2:-}" first last output
    shift 2 || true
    case "$test" in
        1) first=1; last=2 ;;
        2) first=3; last=4 ;;
        *) die "data maintenance test must be 1 (refresh runs 1-2) or 2 (runs 3-4)" ;;
    esac
    [[ -d "$DATA_DIR/sf${sf}_update" ]] || die "no refresh data in $DATA_DIR/sf${sf}_update, run './tpcds.sh generate $sf'"
    output=$(new_output "$sf" "dm$test")
    "$PYTHON" "$SF_DIR/Clause5/data_maintenance.py" run "$first" "$last" "$output" \
        --data-dir "$DATA_DIR/sf${sf}_update" ${1+"$@"}
}

cmd_all() {
    # Spec 7.4.2 for each scale factor, without restarting the database in between (7.4.1.3)
    local sf
    for sf in "$@"; do
        check_scale "$sf"
        [[ -d "$DATA_DIR/sf$sf" && -d "$DATA_DIR/sf${sf}_update" ]] \
            || die "no data for SF$sf, run './tpcds.sh generate $sf'"
    done
    confirm_drop
    for sf in "$@"; do
        echo "===== Scale factor $sf ====="
        ASSUME_YES=1 cmd_load "$sf"
        cmd_power "$sf"
        cmd_throughput "$sf" 1
        cmd_dm "$sf" 1
        cmd_throughput "$sf" 2
        cmd_dm "$sf" 2
    done
    cmd_metrics
}


command="${1:-}"
shift || true
case "$command" in
    build)      cmd_build ;;
    generate)   [[ $# -gt 0 ]] || die "give at least one scale factor"
                for sf in "$@"; do check_scale "$sf"; cmd_generate "$sf"; done ;;
    validate)   cmd_validate ;;
    dm-setup)   cmd_dm_setup ;;
    load)       check_scale "${1:-}"; cmd_load "$1" ;;
    power)      check_scale "${1:-}"; cmd_power "$1" ;;
    throughput) check_scale "${1:-}"; cmd_throughput "$1" "${2:-}" ;;
    dm)         check_scale "${1:-}"; cmd_dm "$@" ;;
    all)        [[ $# -gt 0 ]] || die "give at least one scale factor"; cmd_all "$@" ;;
    metrics)    cmd_metrics ;;
    report)     cmd_report ;;
    ""|-h|--help|help) usage ;;
    *)          usage >&2; exit 1 ;;
esac