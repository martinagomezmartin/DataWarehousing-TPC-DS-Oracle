import argparse
import csv
import json
import os
import time
from pathlib import Path

import oracledb
import sqlparse

ROOT = Path(__file__).resolve().parent
QUERIES = ROOT / "Queries"
ORDERS = ROOT / "streams_order.json"
CSV_COLUMNS = ["stream_id", "position", "query_id", "elapsed_s", "row_count","status", "error", "start_ns", "end_ns",]


def load_statements(query_id):
    """Read all SQL statements belonging to one logical query"""
    path = QUERIES / f"query{query_id:02d}.sql"
    sql = path.read_text(encoding="utf-8-sig")
    statements = [s.strip().removesuffix(";").strip() for s in sqlparse.split(sql)]
    statements = [s for s in statements if s]
    if not statements:
        raise ValueError(f"empty sql file: {path}")
    return statements


def prepare_stream(stream_id):
    """Load the 99 queries in this stream's prescribed order (json file : according to the doc)"""
    orders = json.loads(ORDERS.read_text(encoding="utf-8"))
    query_ids = orders[str(stream_id)]
    if len(query_ids) != 99 or set(query_ids) != set(range(1, 100)):
        raise ValueError(f"Invalid order for stream {stream_id}")
    return [
        (position, query_id, load_statements(query_id))
        for position, query_id in enumerate(query_ids, start=1)
    ]


def measure_query(cursor, statements):
    """Measure one query"""
    row_count = 0
    error = ""
    start_ns = time.perf_counter_ns()
    try:
        for sql in statements:
            cursor.execute(sql)
            if cursor.description is not None:
                while rows := cursor.fetchmany():
                    row_count += len(rows)
    except Exception as exc:
        error = str(exc)
    end_ns = time.perf_counter_ns()

    return {
        "elapsed_s": (end_ns - start_ns) / 1_000_000_000,
        "row_count": row_count,
        "status": "ERROR" if error else "OK",
        "error": error,
        "start_ns": start_ns,
        "end_ns": end_ns,
    }


def run_stream(stream_id, output_dir):
    """Execute one stream sequentially with one Oracle session and one CSV"""
    queries = prepare_stream(stream_id)  # Read files before measuring SQL.
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"stream_{stream_id}.csv"

    with oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
    ) as connection:
        with connection.cursor() as cursor, output_file.open(
            "w", newline="", encoding="utf-8"
        ) as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            for position, query_id, statements in queries:
                print(f"[Stream {stream_id}] Q{query_id:02d}...", flush=True)
                measurement = measure_query(cursor, statements)
                writer.writerow({
                    "stream_id": stream_id,
                    "position": position,
                    "query_id": query_id,
                    **measurement,
                })
                csv_file.flush()  # Preserve earlier rows if another query fails.

                if measurement["status"] == "ERROR":
                    print(measurement["error"], flush=True)
                    raise SystemExit(1)

    print(f"[Stream {stream_id}] Finished: {output_file}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="TPC-DS oracle query collector")
    parser.add_argument("stream_id", type=int, choices=range(9))
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    run_stream(args.stream_id, args.output_dir)


if __name__ == "__main__":
    main()
