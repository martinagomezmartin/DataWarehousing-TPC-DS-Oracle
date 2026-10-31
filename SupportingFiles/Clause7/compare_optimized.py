import argparse
import csv
import hashlib
import os
import random
import statistics
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import oracledb
import sqlparse

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "SupportingFiles" / "Clause4" / "queries"
OPTIMIZED = ROOT / "SupportingFiles" / "Clause4" / "queries_optimized"
DATA_DIR = ROOT / os.environ.get("DATA_DIR", "tpcds-data.nosync")
CONTAINER = os.environ.get("ORACLE_CONTAINER", "oracle-tpcds")
COLUMNS = ["sf", "query_id", "version", "cache", "run", "elapsed_s", "status", "hash"]
COLORS = {"original": "#eb6834", "optimized": "#2a78d6"}
LABELS = {"original": "Original", "optimized": "Optimized"}

plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
    "axes.edgecolor": "#e4e3df", "axes.labelcolor": "#52514e", "xtick.color": "#52514e",
    "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
})


def connect():
    return oracledb.connect(user=os.environ["ORACLE_USER"], password=os.environ["ORACLE_PASSWORD"],
                            dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"))


def sysdba(sql):
    """Statements that need the administrator (flush the cache, resize a file)"""
    subprocess.run(["docker", "exec", "-i", CONTAINER, "sqlplus", "-s", "/", "as", "sysdba"],
                   input=f"alter session set container = FREEPDB1;\n{sql}\nexit\n",
                   text=True, check=True, capture_output=True)


def statements(path):
    sql = path.read_text(encoding="utf-8-sig")
    parts = [s.strip().removesuffix(";").strip() for s in sqlparse.split(sql)]
    return [s for s in parts if s]


def loaded_scale(scales):
    """The customer table is never changed by the data maintenance: its row count identifies the SF"""
    with connect() as connection:
        try:
            count = connection.cursor().execute("SELECT COUNT(*) FROM customer").fetchone()[0]
        except oracledb.DatabaseError:
            return None
    for sf in scales:
        with open(DATA_DIR / f"sf{sf}" / "customer.dat", "rb") as f:
            if sum(1 for _ in f) == count:
                return sf
    return None


def load(sf):
    """Same steps as './tpcds.sh load', without writing a load folder in results/"""
    print(f"===== Loading SF{sf} =====", flush=True)
    with connect() as connection:
        connection.cursor().execute("""BEGIN
            FOR v IN (SELECT view_name FROM user_views) LOOP
                EXECUTE IMMEDIATE 'DROP VIEW "' || v.view_name || '"';
            END LOOP;
            FOR t IN (SELECT table_name FROM user_tables) LOOP
                EXECUTE IMMEDIATE 'DROP TABLE "' || t.table_name || '" CASCADE CONSTRAINTS PURGE';
            END LOOP;
        END;""")
    # give the space of the previous SF back, so that the 12 GB limit of Oracle Free is not reached
    sysdba("alter database datafile '/opt/oracle/oradata/FREE/FREEPDB1/tpcds_data01.dbf' resize 200m;")
    python = os.environ.get("PYTHON", "python")
    subprocess.run([python, str(ROOT / "SupportingFiles" / "Clause3" / "load_data.py"), "--create-tables",
                    "--data-dir", str(DATA_DIR / f"sf{sf}"), "--user", os.environ["ORACLE_USER"],
                    "--password", os.environ["ORACLE_PASSWORD"], "--host", os.environ.get("ORACLE_HOST", "localhost"),
                    "--port", os.environ.get("ORACLE_PORT", "1521"),
                    "--service", os.environ.get("ORACLE_SERVICE", "FREEPDB1")],
                   check=True, stdout=subprocess.DEVNULL)
    with connect() as connection:
        connection.cursor().execute("BEGIN DBMS_STATS.GATHER_SCHEMA_STATS(USER); END;")
    subprocess.run([python, str(ROOT / "SupportingFiles" / "Clause5" / "data_maintenance.py"), "setup"],
                   check=True, stdout=subprocess.DEVNULL)


def result_hash(rows):
    """Numbers rounded to 2 decimals: a rewrite may sum in another order"""
    norm = lambda v: f"{float(v):.2f}" if isinstance(v, (float, Decimal)) else str(v)
    return hashlib.sha256("\n".join("|".join(map(norm, r)) for r in rows).encode()).hexdigest()[:12]


def run_once(sqls, timeout_s):
    """New session and new plan at every run, like the single execution of the Power Test"""
    rows, status = [], "OK"
    start = time.perf_counter()
    try:
        with connect() as connection:
            connection.call_timeout = timeout_s * 1000
            start = time.perf_counter()
            with connection.cursor() as cursor:
                for sql in sqls:
                    cursor.execute(f"/* {random.random()} */ {sql}")
                    if cursor.description is not None:
                        rows.extend(cursor.fetchall())
    except oracledb.Error as exc:
        status = "TIMEOUT" if "DPY-4024" in str(exc) else "ERROR"
        print(f"    {exc}", flush=True)
    elapsed = time.perf_counter() - start
    return elapsed, status, result_hash(rows) if status == "OK" else ""


def compare(sf, query_ids, runs, timeout_s, writer):
    """One run with an empty buffer cache, then alternated runs with a warm cache"""
    versions = {q: {"original": statements(ORIGINAL / f"query{q:02d}.sql"),
                    "optimized": statements(OPTIMIZED / f"query{q:02d}.sql")} for q in query_ids}
    plan = [("cold", 1)] + [("warm", i) for i in range(1, runs + 1)]
    for q in query_ids:
        timed_out = set()
        for cache, run in plan:
            for version, sqls in versions[q].items():
                if version in timed_out:
                    continue  # it would only time out again
                if cache == "cold":
                    sysdba("alter system flush buffer_cache;")
                elapsed, status, digest = run_once(sqls, timeout_s)
                if status == "TIMEOUT":
                    timed_out.add(version)
                writer.writerow([sf, q, version, cache, run, round(elapsed, 3), status, digest])
                print(f"SF{sf} Q{q:02d} {version:9} {cache} {elapsed:8.3f}s {status}", flush=True)


def summarize(rows):
    """Median time per (query, sf, version, cache) and whether both versions return the same rows"""
    times, hashes, timeouts = defaultdict(list), defaultdict(set), set()
    for r in rows:
        key = (int(r["query_id"]), int(r["sf"]))
        if r["status"] == "OK":
            times[key + (r["version"], r["cache"])].append(float(r["elapsed_s"]))
            hashes[key + (r["version"],)].add(r["hash"])
        elif r["status"] == "TIMEOUT":
            timeouts.add(key + (r["version"],))
    summary = []
    for q, sf in sorted({(int(r["query_id"]), int(r["sf"])) for r in rows}):
        line = {"query_id": q, "sf": sf}
        for version in COLORS:
            for cache in ("cold", "warm"):
                values = times.get((q, sf, version, cache))
                line[f"{version}_{cache}_s"] = round(statistics.median(values), 3) if values else ""
            line[f"{version}_timeout"] = (q, sf, version) in timeouts
        both = hashes.get((q, sf, "original"), set()) | hashes.get((q, sf, "optimized"), set())
        complete = hashes.get((q, sf, "original")) and hashes.get((q, sf, "optimized"))
        line["same_result"] = ("yes" if len(both) == 1 else "NO") if complete else "?"
        summary.append(line)
    return summary


def plot(query_id, lines, timeout_s, output):
    """Original against optimized at each SF, empty cache and warm cache side by side"""
    sfs = [line["sf"] for line in lines]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    width = 0.38
    for ax, cache, title in [(axes[0], "cold", "Empty buffer cache"), (axes[1], "warm", "Warm cache (median)")]:
        for i, version in enumerate(COLORS):
            for x, line in enumerate(lines):
                value = line[f"{version}_{cache}_s"]
                timeout = value == "" and line[f"{version}_timeout"]
                if value == "" and not timeout:
                    continue
                height = timeout_s if timeout else value
                pos = x + (i - 0.5) * width
                ax.bar(pos, height, width, color=COLORS[version], hatch="//" if timeout else None,
                       edgecolor="#fcfcfb", label=LABELS[version] if x == 0 else None)
                ax.annotate(f">{timeout_s}s" if timeout else f"{value:.2f}s", (pos, height),
                            textcoords="offset points", xytext=(0, 3), ha="center", fontsize=8,
                            color="#52514e")
        ax.set_yscale("log")
        ax.set_xticks(range(len(sfs)), [f"SF{sf}" for sf in sfs])
        ax.set_title(title, loc="left", fontsize=10)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("seconds (log scale)")
    axes[0].legend(frameon=False)
    fig.suptitle(f"Query {query_id}: original and optimized version by scale factor", x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def report(output_dir, timeout_s):
    with (output_dir / "runs.csv").open(encoding="utf-8") as f:
        summary = summarize(list(csv.DictReader(f)))
    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    for q in sorted({line["query_id"] for line in summary}):
        lines = [line for line in summary if line["query_id"] == q]
        plot(q, lines, timeout_s, output_dir / f"query{q:02d}.png")
        print(f"\nQuery {q}")
        print(f"{'SF':>4} {'original cold':>14} {'optimized cold':>15} {'original warm':>14} "
              f"{'optimized warm':>15}  same result")
        for line in lines:
            cells = [str(line[f"{v}_{c}_s"]) or ("timeout" if line[f"{v}_timeout"] else "-")
                     for c in ("cold", "warm") for v in COLORS]
            print(f"{line['sf']:>4} {cells[0]:>14} {cells[1]:>15} {cells[2]:>14} {cells[3]:>15}  "
                  f"{line['same_result']}")
    print(f"\nCharts and CSV files: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Time the original and the optimized queries at several scale factors")
    parser.add_argument("--scales", type=int, nargs="+", default=[1, 2, 3, 5, 7])
    parser.add_argument("--queries", type=int, nargs="*", help="default: every file of Clause4/queries_optimized")
    parser.add_argument("--runs", type=int, default=3, help="runs with a warm cache, after the empty-cache run")
    parser.add_argument("--timeout", type=int, default=1800, help="seconds before a run is stopped")
    parser.add_argument("--output", type=Path, help="default: results/optimization/<date>")
    parser.add_argument("--plot-only", action="store_true", help="redraw the charts of --output")
    args = parser.parse_args()

    output_dir = args.output or ROOT / "results" / "optimization" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if args.plot_only:
        report(output_dir, args.timeout)
        return

    query_ids = args.queries or sorted(int(p.stem[5:]) for p in OPTIMIZED.glob("query*.sql"))
    missing = [q for q in query_ids if not (OPTIMIZED / f"query{q:02d}.sql").exists()]
    if not query_ids or missing:
        raise SystemExit(f"no optimized version in {OPTIMIZED} for {missing or 'any query'}")

    # start with the SF already in the database: one load less
    current = loaded_scale(args.scales)
    scales = sorted(args.scales, key=lambda sf: sf != current)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "runs.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        for sf in scales:
            if sf != current:
                load(sf)
                current = sf
            compare(sf, query_ids, args.runs, args.timeout, writer)
            f.flush()
    report(output_dir, args.timeout)


if __name__ == "__main__":
    main()