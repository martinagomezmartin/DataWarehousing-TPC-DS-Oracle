import argparse
import csv
import math
import re
from pathlib import Path

SQ = 4                      # query streams per Throughput Test (spec 7.4.6.9)
QUERIES_PER_STREAM = 99
TESTS = ["load", "power", "throughput1", "dm1", "throughput2", "dm2"]
RUN_DIR = re.compile(r"^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_(" + "|".join(TESTS) + r")$")
COLUMNS = ["scale_factor", "run_start", "T_Load_s", "T_Power_s", "T_TT1_s", "T_DM1_s",
           "T_TT2_s", "T_DM2_s", "T_PT_h", "T_TT_h", "T_DM_h", "T_LD_h", "QphDS"]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def query_test_seconds(folder, streams):
    """Power / Throughput Test: first query submitted to last answer received (7.4.5, 7.4.7)"""
    rows = []
    for stream in streams:
        path = folder / f"stream_{stream}.csv"
        if not path.exists():
            return None
        stream_rows = read_csv(path)
        if len(stream_rows) != QUERIES_PER_STREAM or any(r["status"] != "OK" for r in stream_rows):
            return None  # incomplete or failed stream
        rows += stream_rows
    return (max(int(r["end_ns"]) for r in rows) - min(int(r["start_ns"]) for r in rows)) / 1e9


def dm_test_seconds(folder):
    """Data Maintenance Test: start of the first refresh run to end of the last (7.4.9.3)"""
    path = folder / "data_maintenance.csv"
    if not path.exists():
        return None
    rows = read_csv(path)
    if any(r["step"] == "rollback" for r in rows):
        return None  # test run with --rollback, not a real data maintenance
    totals = [r for r in rows if r["step"] == "TOTAL"]
    if len(totals) != SQ // 2:
        return None
    return (max(int(r["end_ns"]) for r in totals) - min(int(r["start_ns"]) for r in totals)) / 1e9


def load_seconds(folder):
    path = folder / "load.csv"
    return float(read_csv(path)[0]["T_load_s"]) if path.exists() else None


def measure(test, folder):
    if test == "load":
        return load_seconds(folder)
    if test == "power":
        return query_test_seconds(folder, [0])
    if test == "throughput1":
        return query_test_seconds(folder, range(1, SQ + 1))
    if test == "throughput2":
        return query_test_seconds(folder, range(SQ + 1, 2 * SQ + 1))
    return dm_test_seconds(folder)


def latest_benchmark(scale_dir):
    """Most recent load followed by valid power, throughput 1, dm 1, throughput 2, dm 2 runs"""
    runs = sorted((m.group(1), m.group(2), d) for d in scale_dir.iterdir()
                  if d.is_dir() and (m := RUN_DIR.match(d.name)))
    loads = [(stamp, folder) for stamp, test, folder in runs if test == "load"]
    for load_stamp, load_folder in reversed(loads):
        times = {"load": measure("load", load_folder)}
        for test in TESTS[1:]:
            # first valid run of each test after this load, in benchmark order
            previous = max(t for t in [load_stamp] + [times.get(f"_{x}") for x in TESTS] if t)
            found = next(((stamp, folder) for stamp, name, folder in runs
                          if name == test and stamp >= previous and measure(test, folder) is not None),
                         None)
            if found is None:
                break
            times[f"_{test}"] = found[0]
            times[test] = measure(test, found[1])
        if all(times.get(test) is not None for test in TESTS):
            return load_stamp, times
    return None


def qphds(scale_factor, t):
    """Primary performance metric QphDS@SF (spec 7.6.3), times converted to hours"""
    hours = {k: v / 3600 for k, v in t.items() if not k.startswith("_")}
    t_pt = hours["power"] * SQ
    t_tt = hours["throughput1"] + hours["throughput2"]
    t_dm = hours["dm1"] + hours["dm2"]
    t_ld = 0.01 * SQ * hours["load"]
    q = SQ * QUERIES_PER_STREAM
    return t_pt, t_tt, t_dm, t_ld, math.floor(scale_factor * q / (t_pt * t_tt * t_dm * t_ld) ** 0.25)


def main():
    parser = argparse.ArgumentParser(description="TPC-DS metrics (QphDS@SF) from the raw results")
    parser.add_argument("results_dir", type=Path, nargs="?", default=Path("results"))
    args = parser.parse_args()

    rows = []
    for scale_dir in sorted(args.results_dir.glob("SF*"), key=lambda p: int(p.name[2:])):
        scale_factor = int(scale_dir.name[2:])
        found = latest_benchmark(scale_dir)
        if found is None:
            print(f"SF{scale_factor}: no complete benchmark (load, power, throughput 1-2, dm 1-2)")
            continue
        run_start, t = found
        t_pt, t_tt, t_dm, t_ld, metric = qphds(scale_factor, t)
        rows.append({
            "scale_factor": scale_factor, "run_start": run_start,
            "T_Load_s": round(t["load"], 1), "T_Power_s": round(t["power"], 1),
            "T_TT1_s": round(t["throughput1"], 1), "T_DM1_s": round(t["dm1"], 1),
            "T_TT2_s": round(t["throughput2"], 1), "T_DM2_s": round(t["dm2"], 1),
            "T_PT_h": round(t_pt, 4), "T_TT_h": round(t_tt, 4),
            "T_DM_h": round(t_dm, 4), "T_LD_h": round(t_ld, 4), "QphDS": metric,
        })

    if not rows:
        return
    output = args.results_dir / "metrics.csv"
    with output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"{'SF':>4} {'T_Load':>9} {'T_Power':>9} {'T_TT1':>9} {'T_DM1':>8} {'T_TT2':>9} {'T_DM2':>8} {'QphDS@SF':>10}")
    for r in rows:
        print(f"{r['scale_factor']:>4} {r['T_Load_s']:>8}s {r['T_Power_s']:>8}s {r['T_TT1_s']:>8}s "
              f"{r['T_DM1_s']:>7}s {r['T_TT2_s']:>8}s {r['T_DM2_s']:>7}s {r['QphDS']:>10}")
    print(f"Metrics: {output}")


if __name__ == "__main__":
    main()
    