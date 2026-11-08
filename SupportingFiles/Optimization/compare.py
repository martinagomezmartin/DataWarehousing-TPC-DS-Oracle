#!/usr/bin/env python3
"""Compare saved benchmark summaries. First file is the baseline.

Usage:
  python compare.py results/sf1__nostats.json results/sf1__stats.json
  python compare.py base.json a.json b.json --metric min --csv diff.csv
"""

import argparse
import csv
import json
import re
from pathlib import Path


def load(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return f"{d['label']}/{d['config']}", d["queries"]


def natural_key(name):
    return [int(x) for x in re.findall(r"\d+", name)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="Baseline first, then 1+ configs to compare")
    ap.add_argument("--metric", choices=["avg", "min"], default="avg",
                    help="avg = mean of warm runs (default), min = best run")
    ap.add_argument("--csv", help="Also write the comparison to this CSV")
    args = ap.parse_args()

    if len(args.files) < 2:
        ap.error("Need at least two result files")

    runs = [load(f) for f in args.files]
    base_name, base = runs[0]
    others = runs[1:]

    def val(queries, q):
        d = queries.get(q)
        return d[args.metric] if d and d.get("status") == "ok" else None

    # Only queries that succeeded in every config
    common = sorted(
        (q for q in base if all(val(qs, q) is not None for _, qs in runs)),
        key=natural_key,
    )
    skipped = len(base) - len(common)

    header = ["query", base_name] + [h for n, _ in others for h in (n, "speedup")]
    rows = []
    for q in common:
        b = val(base, q)
        row = [q, b]
        for _, qs in others:
            v = val(qs, q)
            row += [v, b / v if v else float("inf")]
        rows.append(row)

    tot_b = sum(r[1] for r in rows)
    total = ["TOTAL", tot_b]
    for i in range(len(others)):
        tv = sum(r[2 + 2 * i] for r in rows)
        total += [tv, tot_b / tv if tv else float("inf")]

    # Print
    print(f"Metric: {args.metric} (seconds) | baseline: {base_name} | "
          f"{len(common)} common queries" + (f" ({skipped} skipped: failed/missing)" if skipped else ""))
    w = max(12, *(len(h) for h in header[1:]))
    print(f"{'query':<12}" + "".join(f"{h:>{w + 2}}" for h in header[1:]))
    print("-" * (12 + (w + 2) * (len(header) - 1)))
    for r in rows + [None, total]:
        if r is None:
            print("-" * (12 + (w + 2) * (len(header) - 1)))
            continue
        cells = [f"{r[1]:{w + 2}.2f}"]
        for i in range(len(others)):
            cells += [f"{r[2 + 2 * i]:{w + 2}.2f}", f"{r[3 + 2 * i]:>{w + 1}.2f}x"]
        print(f"{r[0]:<12}" + "".join(cells))

    for i, (name, _) in enumerate(others):
        sp = [r[3 + 2 * i] for r in rows]
        print(f"\n{name}: {sum(s > 1.05 for s in sp)} faster, "
              f"{sum(s < 0.95 for s in sp)} slower, "
              f"{sum(0.95 <= s <= 1.05 for s in sp)} about the same (+/-5%) vs {base_name}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w_ = csv.writer(f)
            w_.writerow(header)
            w_.writerows(rows + [total])
        print(f"\nWritten to {args.csv}")


if __name__ == "__main__":
    main()