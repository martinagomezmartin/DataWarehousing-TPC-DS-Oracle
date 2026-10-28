import argparse
import csv
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from compute_metrics import SQ, TESTS, latest_benchmark, qphds, read_csv

# Reference palette (light): one hue for magnitude, ordinal blue ramp for scale factors,
# categorical slots 1-4 for the data maintenance phases
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
REFERENCE = "#8f8e88"
ORDINAL = ["#86b6ef", "#5598e7", "#3987e5", "#256abf", "#1c5cab", "#104281", "#0d366b"]
PHASES = [("Load refresh data", "#2a78d6"), ("Deletes (DF_*)", "#eb6834"),
          ("Inserts (LF_*)", "#1baf7a"), ("Commit", "#eda100")]
THROUGHPUT = [("throughput1", "Throughput Test 1", "#2a78d6"),
              ("throughput2", "Throughput Test 2", "#eb6834")]
PROFILES = ["linear", "superlinear", "erratic"]
LABELS = {"load": "Load Test (T_Load)", "power": "Power Test (T_Power)",
          "throughput1": "Throughput Test 1 (T_TT1)", "dm1": "Data Maintenance 1 (T_DM1)",
          "throughput2": "Throughput Test 2 (T_TT2)", "dm2": "Data Maintenance 2 (T_DM2)"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": TEXT_SECONDARY, "axes.titlecolor": TEXT,
    "xtick.color": TEXT_SECONDARY, "ytick.color": TEXT_SECONDARY, "text.color": TEXT,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
})


def ordinal_colors(count):
    """Evenly spaced steps of the blue ramp, light (smallest SF) to dark (largest SF)"""
    if count == 1:
        return [ORDINAL[3]]
    return [ORDINAL[round(i * (len(ORDINAL) - 1) / (count - 1))] for i in range(count)]


def collect(results_dir):
    """Latest complete benchmark of every scale factor: times, run folders, metric"""
    runs = []
    for scale_dir in sorted(results_dir.glob("SF*"), key=lambda p: int(p.name[2:])):
        found = latest_benchmark(scale_dir)
        if found is None:
            print(f"{scale_dir.name}: no complete benchmark, skipped")
            continue
        run_start, times = found
        folders = {"load": scale_dir / f"{run_start}_load"}
        folders.update({test: scale_dir / f"{times['_' + test]}_{test}" for test in TESTS[1:]})
        sf = int(scale_dir.name[2:])
        runs.append({"sf": sf, "times": times, "folders": folders, "qphds": qphds(sf, times)[-1]})
    return runs


def plot_times(runs, output):
    """One panel per test (different magnitudes, never a dual axis), with a linear reference"""
    sfs = [r["sf"] for r in runs]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5))
    for ax, test in zip(axes.flat, TESTS):
        values = [r["times"][test] for r in runs]
        ax.plot(sfs, [values[0] * sf / sfs[0] for sf in sfs], color=REFERENCE, linewidth=1.2,
                linestyle="--", label=f"linear from SF{sfs[0]}")
        ax.plot(sfs, values, color=BLUE, linewidth=2, marker="o", markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label="measured")
        for sf, value in zip(sfs, values):
            ax.annotate(f"{value:.0f}s", (sf, value), textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=8, color=TEXT_SECONDARY)
        ax.set_title(LABELS[test], fontsize=10, loc="left")
        ax.set_xticks(sfs, [f"SF{sf}" for sf in sfs])
        ax.set_ylabel("seconds")
        ax.set_ylim(bottom=0, top=max(values + [values[0] * sfs[-1] / sfs[0]]) * 1.18)
    axes.flat[0].legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("Elapsed time of each test by scale factor", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_qphds(runs, output):
    sfs = [f"SF{r['sf']}" for r in runs]
    values = [r["qphds"] for r in runs]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar(sfs, values, color=BLUE, width=0.55)
    for bar, value in zip(bars, values):
        ax.annotate(f"{value:,}", (bar.get_x() + bar.get_width() / 2, value),
                    textcoords="offset points", xytext=(0, 4), ha="center", fontsize=9)
    ax.set_title("QphDS@SF by scale factor (clause 7.6.3)", loc="left", fontsize=12)
    ax.set_ylabel("QphDS@SF")
    ax.grid(axis="x", visible=False)
    ax.set_ylim(top=max(values) * 1.15)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def power_query_times(run):
    rows = read_csv(run["folders"]["power"] / "stream_0.csv")
    return {int(r["query_id"]): float(r["elapsed_s"]) for r in rows}


def plot_power_queries(runs, per_query, output, top=15):
    """Slowest Power Test queries at the largest scale factor, compared across scale factors"""
    largest = runs[-1]["sf"]
    queries = sorted(per_query[largest], key=per_query[largest].get, reverse=True)[:top]
    colors = ordinal_colors(len(runs))
    height = 0.8 / len(runs)
    fig, ax = plt.subplots(figsize=(9, 0.42 * top + 1.6))
    for i, (run, color) in enumerate(zip(runs, colors)):
        positions = [q_index + i * height for q_index in range(len(queries))]
        ax.barh(positions, [per_query[run["sf"]][q] for q in queries], height=height * 0.9,
                color=color, label=f"SF{run['sf']}")
    ax.set_yticks([q_index + 0.4 - height / 2 for q_index in range(len(queries))],
                  [f"Q{q}" for q in queries])
    ax.invert_yaxis()
    ax.set_xscale("log")  # one query can be 100x slower than the others
    ax.set_xlabel("seconds (log scale)")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"{top} slowest Power Test queries at SF{largest}", loc="left", fontsize=12)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_throughput_vs_power(runs, output):
    """T_TT / T_Power: 1 = the streams fully in parallel, Sq = the streams one after the other.
    A ratio, so that an outlier in the Power Test does not hide the comparison"""
    sfs = [r["sf"] for r in runs]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for factor, text in ((1, "streams fully in parallel"), (2, "2 x Power Test"),
                         (SQ, "streams one after the other")):
        ax.axhline(factor, color=REFERENCE, linewidth=1.2, linestyle="--")
        ax.annotate(f"{factor}: {text}", (sfs[-1], factor), textcoords="offset points",
                    xytext=(10, 3), va="bottom", fontsize=8, color=TEXT_SECONDARY)
    ratios = {test: [r["times"][test] / r["times"]["power"] for r in runs] for test, _, _ in THROUGHPUT}
    for test, label, color in THROUGHPUT:
        values = ratios[test]
        others = [ratios[t] for t in ratios if t != test][0]
        ax.plot(sfs, values, color=color, linewidth=2, marker="o", markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=label)
        for sf, value, other in zip(sfs, values, others):  # label on the side away from the other line
            ax.annotate(f"{value:.2f}", (sf, value), textcoords="offset points",
                        xytext=(0, 8 if value >= other else -16), ha="center", fontsize=8,
                        color=TEXT_SECONDARY)
    ax.set_xticks(sfs, [f"SF{sf}" for sf in sfs])
    ax.set_xlim(right=sfs[-1] + (sfs[-1] - sfs[0]) * 0.45)  # room for the reference labels
    ax.set_ylim(0, SQ + 0.6)
    ax.set_ylabel("T_TT / T_Power")
    ax.set_title(f"Throughput Tests ({SQ} streams) relative to the Power Test", loc="left",
                 fontsize=12)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def classify(times, data_ratio):
    """linear: time ratio up to 2x the data ratio; superlinear: more; erratic: the time drops
    by more than half from one scale factor to the next (on a query of at least 1 s)"""
    if any(a >= 1 and b < 0.5 * a for a, b in zip(times, times[1:])):
        return "erratic"
    if times[0] > 0 and times[-1] / times[0] > 2 * data_ratio:
        return "superlinear"
    return "linear"


def query_profiles(runs, per_query):
    sfs = [r["sf"] for r in runs]
    profiles = {name: [] for name in PROFILES}
    for q in range(1, 100):
        times = [per_query[sf].get(q, 0) for sf in sfs]
        profiles[classify(times, sfs[-1] / sfs[0])].append(q)
    return profiles


def plot_query_profiles(runs, per_query, profiles, output, examples=3):
    """Small multiples: the slowest queries of each profile, Power Test time by scale factor"""
    sfs = [r["sf"] for r in runs]
    colors = ordinal_colors(len(runs))
    fig, axes = plt.subplots(len(PROFILES), examples, figsize=(10, 2.6 * len(PROFILES)),
                             squeeze=False)
    for row, name in enumerate(PROFILES):
        if name == "erratic":  # largest jump first
            key = lambda q: max(per_query[sf][q] for sf in sfs) / max(min(per_query[sf][q] for sf in sfs), 1e-3)
        elif name == "superlinear":  # worst ratio first, among the queries that last 1 s or more
            key = lambda q: (per_query[sfs[-1]][q] >= 1,
                             per_query[sfs[-1]][q] / max(per_query[sfs[0]][q], 1e-3))
        else:  # slowest first
            key = lambda q: per_query[sfs[-1]][q]
        chosen = sorted(profiles[name], key=key, reverse=True)[:examples]
        for col in range(examples):
            ax = axes[row][col]
            if col >= len(chosen):
                ax.set_visible(False)
                continue
            q = chosen[col]
            values = [per_query[sf][q] for sf in sfs]
            labels = [f"SF{sf}" for sf in sfs]
            ax.bar(labels, values, color=colors, width=0.6)
            ax.plot(labels, [values[0] * sf / sfs[0] for sf in sfs], color=REFERENCE,
                    linewidth=1.2, linestyle="--")
            ax.set_title(f"Q{q}", loc="left", fontsize=10)
            ax.grid(axis="x", visible=False)
            ax.tick_params(labelsize=8)
            if col == 0:
                ax.set_ylabel(f"{name} ({len(profiles[name])})\nseconds", fontsize=9)
    fig.suptitle("Power Test time by scale factor: linear, superlinear and erratic queries "
                 "(dashed: linear from SF" + str(sfs[0]) + ")", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def plot_distribution(runs, per_query, output):
    """Distribution of the 99 Power Test query times per scale factor (log scale)"""
    sfs = [r["sf"] for r in runs]
    data = [[t for t in per_query[sf].values() if t > 0] for sf in sfs]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    boxes = ax.boxplot(data, patch_artist=True, widths=0.5,
                       medianprops={"color": TEXT, "linewidth": 1.5},
                       whiskerprops={"color": TEXT_SECONDARY}, capprops={"color": TEXT_SECONDARY},
                       flierprops={"marker": "o", "markersize": 4, "markerfacecolor": REFERENCE,
                                   "markeredgecolor": SURFACE})
    for patch, color in zip(boxes["boxes"], ordinal_colors(len(runs))):
        patch.set_facecolor(color)
        patch.set_edgecolor(SURFACE)
    for i, sf in enumerate(sfs, start=1):
        times = per_query[sf]
        median = sorted(data[i - 1])[len(data[i - 1]) // 2]
        ax.annotate(f"median {median:.2f}s", (i + 0.28, median), va="center", fontsize=8,
                    color=TEXT_SECONDARY)
        slowest = max(times, key=times.get)
        ax.annotate(f"Q{slowest}", (i, times[slowest]), textcoords="offset points",
                    xytext=(6, 0), va="center", fontsize=8, color=TEXT)
    ax.set_xticks(range(1, len(sfs) + 1), [f"SF{sf}" for sf in sfs])
    ax.set_yscale("log")
    ax.set_ylabel("seconds (log scale)")
    ax.grid(axis="x", visible=False)
    ax.set_title("Distribution of the 99 Power Test query times", loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def dm_phases(run):
    """Seconds spent in each data maintenance phase over DM1 + DM2"""
    totals = dict.fromkeys([name for name, _ in PHASES], 0.0)
    for test in ("dm1", "dm2"):
        for row in read_csv(run["folders"][test] / "data_maintenance.csv"):
            step, seconds = row["step"], float(row["elapsed_s"])
            if step.startswith("load_"):
                totals["Load refresh data"] += seconds
            elif step.startswith("DF_"):
                totals["Deletes (DF_*)"] += seconds
            elif step.startswith("LF_") or step == "set_offsets":
                totals["Inserts (LF_*)"] += seconds
            elif step == "commit":
                totals["Commit"] += seconds
    return totals


def plot_dm(runs, output):
    labels = [f"SF{r['sf']}" for r in runs]
    phases = [dm_phases(r) for r in runs]
    fig, ax = plt.subplots(figsize=(9, 0.6 * len(runs) + 1.8))
    left = [0.0] * len(runs)
    for name, color in PHASES:
        widths = [p[name] for p in phases]
        ax.barh(labels, widths, left=left, color=color, label=name, height=0.55,
                edgecolor=SURFACE, linewidth=2)
        left = [a + b for a, b in zip(left, widths)]
    for y, total in enumerate(left):
        ax.annotate(f"{total:.0f}s", (total, y), textcoords="offset points", xytext=(4, 0),
                    va="center", fontsize=9, color=TEXT_SECONDARY)
    ax.invert_yaxis()
    ax.set_xlabel("seconds (DM1 + DM2)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Data maintenance time by phase", loc="left", fontsize=12)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.25))
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def write_tables(runs, per_query, profiles, output_dir):
    base = runs[0]
    with (output_dir / "summary.csv").open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["scale_factor"] + [f"T_{t}_s" for t in TESTS] + ["QphDS"])
        for r in runs:
            writer.writerow([r["sf"]] + [round(r["times"][t], 1) for t in TESTS] + [r["qphds"]])
    with (output_dir / "power_queries.csv").open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["query"] + [f"SF{r['sf']}_s" for r in runs])
        for q in range(1, 100):
            writer.writerow([q] + [round(per_query[r["sf"]].get(q, 0), 3) for r in runs])

    lines = ["# TPC-DS benchmark results", "",
             f"Sq = {SQ} query streams per Throughput Test, Oracle Database Free.", "",
             "## Elapsed times (seconds) and QphDS@SF", "",
             "| SF | " + " | ".join(LABELS[t] for t in TESTS) + " | QphDS@SF |",
             "|---" * (len(TESTS) + 2) + "|"]
    for r in runs:
        lines.append(f"| {r['sf']} | " + " | ".join(f"{r['times'][t]:.1f}" for t in TESTS)
                     + f" | {r['qphds']:,} |")
    lines += ["", f"## Scaling relative to SF{base['sf']}",
              "", f"Time ratio T(SF) / T(SF{base['sf']}) next to the data ratio SF / SF{base['sf']}"
              " (a value equal to the data ratio means linear scaling).", "",
              "| SF | data ratio | " + " | ".join(t for t in TESTS) + " |",
              "|---" * (len(TESTS) + 2) + "|"]
    for r in runs:
        lines.append(f"| {r['sf']} | {r['sf'] / base['sf']:.1f} | "
                     + " | ".join(f"{r['times'][t] / base['times'][t]:.2f}" for t in TESTS) + " |")
    lines += ["", "## Throughput Tests against the Power Test", "",
              f"T_TT / T_Power: 1 = the {SQ} streams fully in parallel, {SQ} = one after the other.", "",
              "| SF | TT1 / Power | TT2 / Power |", "|---|---|---|"]
    for r in runs:
        lines.append(f"| {r['sf']} | {r['times']['throughput1'] / r['times']['power']:.2f} | "
                     f"{r['times']['throughput2'] / r['times']['power']:.2f} |")
    data_ratio = runs[-1]["sf"] / base["sf"]
    lines += ["", f"## Query profiles (Power Test, SF{base['sf']} to SF{runs[-1]['sf']})", "",
              f"linear: time ratio up to {2 * data_ratio:.0f} (2x the data ratio {data_ratio:.0f}); "
              "superlinear: above; erratic: the time drops by more than half from one scale factor "
              "to the next.", "", "| profile | queries | count |", "|---|---|---|"]
    for name in PROFILES:
        lines.append(f"| {name} | " + ", ".join(f"Q{q}" for q in profiles[name])
                     + f" | {len(profiles[name])} |")
    largest = runs[-1]["sf"]
    slowest = sorted(per_query[largest], key=per_query[largest].get, reverse=True)[:10]
    lines += ["", f"## 10 slowest Power Test queries at SF{largest} (seconds)", "",
              "| query | " + " | ".join(f"SF{r['sf']}" for r in runs) + " |",
              "|---" * (len(runs) + 1) + "|"]
    for q in slowest:
        lines.append(f"| Q{q} | " + " | ".join(f"{per_query[r['sf']][q]:.2f}" for r in runs) + " |")
    lines += ["", "## Figures", "", "![Times](times_by_sf.png)", "", "![QphDS](qphds_by_sf.png)", "",
              "![Throughput vs Power](throughput_vs_power.png)", "",
              "![Power Test queries](power_queries.png)", "",
              "![Query profiles](query_profiles.png)", "",
              "![Query time distribution](query_distribution.png)", "",
              "![Data maintenance](dm_phases.png)", ""]
    (output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Final TPC-DS benchmark report (tables + figures)")
    parser.add_argument("results_dir", type=Path, nargs="?", default=Path("results"))
    parser.add_argument("output_dir", type=Path, nargs="?", default=Path("Report/results"))
    args = parser.parse_args()

    runs = collect(args.results_dir)
    if not runs:
        raise SystemExit("No complete benchmark found: run './tpcds.sh all <SF ...>' first")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_query = {r["sf"]: power_query_times(r) for r in runs}
    profiles = query_profiles(runs, per_query)

    plot_times(runs, args.output_dir / "times_by_sf.png")
    plot_qphds(runs, args.output_dir / "qphds_by_sf.png")
    plot_throughput_vs_power(runs, args.output_dir / "throughput_vs_power.png")
    plot_power_queries(runs, per_query, args.output_dir / "power_queries.png")
    plot_query_profiles(runs, per_query, profiles, args.output_dir / "query_profiles.png")
    plot_distribution(runs, per_query, args.output_dir / "query_distribution.png")
    plot_dm(runs, args.output_dir / "dm_phases.png")
    write_tables(runs, per_query, profiles, args.output_dir)

    # Keep the raw CSV files of the runs used in the report
    for r in runs:
        for folder in r["folders"].values():
            shutil.copytree(folder, args.output_dir / "raw" / f"SF{r['sf']}" / folder.name,
                            dirs_exist_ok=True)

    print(f"Report: {args.output_dir / 'report.md'} (+ 7 figures, summary.csv, power_queries.csv, raw/)")


if __name__ == "__main__":
    main()