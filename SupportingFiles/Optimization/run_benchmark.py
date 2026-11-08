#!/usr/bin/env python3
"""Run TPC-DS queries N times on Oracle; save one JSON summary per (label, config)."""

import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from statistics import mean

import oracledb

QUERY_PATTERN = re.compile(r"^query(\d+)(?:\.(\d+))?\.sql$", re.IGNORECASE)


def load_env(path):
    """Minimal .env loader; real environment variables take precedence."""
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def find_queries(query_dir, start, end):
    """Return [(name, path)] sorted numerically: query14, query14.1, ..."""
    found = []
    for path in Path(query_dir).glob("query*.sql"):
        m = QUERY_PATTERN.match(path.name)
        if not m:
            continue
        base = int(m.group(1))
        part = int(m.group(2)) if m.group(2) else 0
        if start <= base <= end:
            name = f"query{base}" if part == 0 else f"query{base}.{part}"
            found.append((base, part, name, path))
    found.sort(key=lambda x: (x[0], x[1]))
    return [(name, path) for _, _, name, path in found]


def read_query(path):
    sql = path.read_text(encoding="utf-8").strip()
    return sql[:-1].rstrip() if sql.endswith(";") else sql


def connect(args):
    conn = oracledb.connect(
        user=args.user,
        password=args.password,
        dsn=f"{args.host}:{args.port}/{args.service}",
    )
    if args.query_rewrite:
        with conn.cursor() as cur:
            cur.execute("ALTER SESSION SET QUERY_REWRITE_ENABLED = TRUE")
    if args.timeout:
        conn.call_timeout = args.timeout * 1000
    return conn


def gather_stats(conn, schema):
    """Gather optimizer stats for the whole schema. Returns elapsed seconds."""
    start = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(
            "BEGIN DBMS_STATS.GATHER_SCHEMA_STATS(ownname => :o, cascade => TRUE); END;",
            o=schema.upper(),
        )
    return time.perf_counter() - start


def run_once(conn, sql, fetch_size):
    """Execute and fetch the full result. Returns (seconds, rows)."""
    start = time.perf_counter()
    rows = 0
    with conn.cursor() as cur:
        cur.arraysize = fetch_size
        cur.prefetchrows = fetch_size
        cur.execute(sql)
        if cur.description:
            while True:
                batch = cur.fetchmany()
                if not batch:
                    break
                rows += len(batch)
    return time.perf_counter() - start, rows


def main():
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--env-file", default=".env")
    known, _ = pre.parse_known_args()
    load_env(known.env_file)
    env = os.environ.get

    parser = argparse.ArgumentParser(
        parents=[pre],
        description="Run TPC-DS queries N times each on Oracle and save a JSON summary.",
    )
    parser.add_argument("--label", required=True, help="Scale factor label, e.g. sf1")
    parser.add_argument(
        "--config", help="Config name, e.g. nostats (default: 'stats' with "
        "--gather-stats, else 'baseline')",
    )
    parser.add_argument(
        "--gather-stats", action="store_true",
        help="Gather schema stats before running (not counted in query times)",
    )
    parser.add_argument("--results-dir", default="results")
    parser.add_argument(
        "--query-dir",
        default="SupportingFiles/Clause4/queries_archive/qualification",
    )
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=99)
    parser.add_argument("--runs", type=int, default=4)
    parser.add_argument("--host", default=env("ORACLE_HOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(env("ORACLE_PORT", "1521")))
    parser.add_argument("--service", default=env("ORACLE_SERVICE", "FREEPDB1"))
    parser.add_argument("--user", default=env("APP_USER", env("ORACLE_USER", "TPCDS")))
    parser.add_argument("--password", default=env("APP_USER_PASSWORD", env("ORACLE_PASSWORD")))
    parser.add_argument("--fetch-size", type=int, default=1000)
    parser.add_argument(
        "--query-rewrite", action="store_true",
        help="Enable Oracle materialized-view query rewrite for each benchmark session",
    )
    parser.add_argument(
        "--timeout", type=int, default=0,
        help="Per-query timeout in seconds (0 = none)",
    )
    args = parser.parse_args()

    if not args.password:
        parser.error("No password: set APP_USER_PASSWORD in .env or use --password")
    if args.start > args.end:
        parser.error("--start must be <= --end")
    config = args.config or ("stats" if args.gather_stats else "baseline")

    queries = find_queries(args.query_dir, args.start, args.end)
    if not queries:
        print(f"No query files found in {args.query_dir}")
        return 1

    sql = {name: read_query(path) for name, path in queries}
    data = {name: {"times": [], "attempts": [], "rows": None, "status": "ok", "error": ""}
            for name, _ in queries}
    failed = set()

    print(f"Label: {args.label} | Config: {config} | {len(queries)} queries x "
          f"{args.runs} runs | {args.user}@{args.host}:{args.port}/{args.service}")

    conn = connect(args)

    gather_secs = None
    if args.gather_stats:
        print("Gathering schema stats...")
        gather_secs = gather_stats(conn, args.user)
        print(f"Stats gathered in {gather_secs:.1f}s")

    for run in range(1, args.runs + 1):
        print(f"\n--- Run {run}/{args.runs} ---")
        for name, _ in queries:
            if name in failed:
                continue
            attempt_start = time.perf_counter()
            try:
                secs, rows = run_once(conn, sql[name], args.fetch_size)
                data[name]["times"].append(secs)
                data[name]["rows"] = rows
                data[name]["attempts"].append({
                    "run": run, "elapsed_s": secs, "status": "ok", "rows": rows,
                })
                print(f"[OK]   {name:<12} {secs:8.2f}s  {rows} rows")
            except oracledb.Error as exc:
                failed.add(name)
                msg = str(exc).strip().splitlines()[0]
                elapsed = time.perf_counter() - attempt_start
                timed_out = "timeout" in msg.lower() or "DPI-1067" in msg
                status = "timed_out" if timed_out else "fail"
                data[name]["status"] = status
                data[name]["error"] = msg
                data[name]["attempts"].append({
                    "run": run, "elapsed_s": elapsed, "status": status, "error": msg,
                })
                print(f"[{'TIMEOUT' if timed_out else 'FAIL'}] {name:<12} "
                      f"{elapsed:8.2f}s  {msg}")
                try:  # the connection may be unusable after an error/timeout
                    conn.close()
                except Exception:
                    pass
                conn = connect(args)

    conn.close()

    # Summary (avg excludes run 1 = cold)
    for name, _ in queries:
        d = data[name]
        t = d["times"]
        if d["status"] == "ok" and len(t) == args.runs:
            warm = t[1:] or t
            d["avg"], d["min"] = mean(warm), min(t)
        elif d["status"] == "ok":
            d["status"] = "fail"

    ok = [n for n, _ in queries if data[n]["status"] == "ok"]
    totals = [sum(data[n]["times"][i] for n in ok) for i in range(args.runs)]

    print("\n" + "=" * 78)
    print(f"Summary ({args.label} / {config}) - seconds; avg excludes run 1 (cold)")
    print("=" * 78)
    print(f"{'query':<12}" + "".join(f"{'run' + str(i):>9}" for i in range(1, args.runs + 1))
          + f"{'avg':>9}{'min':>9}")
    for name, _ in queries:
        d = data[name]
        if d["status"] != "ok":
            print(f"{name:<12}  FAILED")
            continue
        print(f"{name:<12}" + "".join(f"{x:9.2f}" for x in d["times"])
              + f"{d['avg']:9.2f}{d['min']:9.2f}")
    print("-" * 78)
    print(f"{'TOTAL':<12}" + "".join(f"{x:9.2f}" for x in totals))

    # Save (overwrites any previous run with the same label + config)
    out_dir = Path(args.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.label}__{config}.json"
    out.write_text(json.dumps({
        "label": args.label,
        "config": config,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "runs": args.runs,
        "gather_stats": args.gather_stats,
        "query_rewrite": args.query_rewrite,
        "gather_seconds": gather_secs,
        "queries": data,
    }, indent=2), encoding="utf-8")

    print(f"\nPassed {len(ok)}/{len(queries)}. Saved to {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())