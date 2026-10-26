#!/usr/bin/env python3

import argparse
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import oracledb


QUERY_PATTERN = re.compile(r"^query(\d+)(?:\.(\d+))?\.sql$", re.IGNORECASE)


def parse_query_file(path: Path):
    """
    Returns:
        (base_number, part_number)

    Examples:
        query14.sql   -> (14, 0)
        query14.1.sql -> (14, 1)
        query14.2.sql -> (14, 2)
    """
    match = QUERY_PATTERN.match(path.name)

    if not match:
        return None

    base_number = int(match.group(1))
    part_number = int(match.group(2)) if match.group(2) else 0

    return base_number, part_number


def find_query_files(query_dir: Path, start: int, end: int):
    """
    Find all query files whose base query number is between start and end.

    Example:
        start=14, end=14

    will find:
        query14.sql
        query14.1.sql
        query14.2.sql
        query14.3.sql
    """

    files = []

    for path in query_dir.glob("query*.sql"):
        parsed = parse_query_file(path)

        if parsed is None:
            continue

        base_number, part_number = parsed

        if start <= base_number <= end:
            files.append((base_number, part_number, path))

    # Sort numerically:
    # query14.sql
    # query14.1.sql
    # query14.2.sql
    # query15.sql
    files.sort(key=lambda x: (x[0], x[1]))

    return files


def read_query(path: Path):
    """
    Read a SQL file.

    Each .sql file must contain exactly ONE SQL statement.
    """

    sql = path.read_text(encoding="utf-8").strip()

    # Remove a trailing semicolon because oracledb.execute()
    # expects the SQL statement without SQL*Plus-style terminators.
    if sql.endswith(";"):
        sql = sql[:-1].rstrip()

    return sql


def create_connection(args):
    dsn = oracledb.makedsn(
        args.host,
        args.port,
        service_name=args.service,
    )

    return oracledb.connect(
        user=args.user,
        password=args.password,
        dsn=dsn,
    )


def execute_query(path: Path, args):
    """
    Execute one SQL file using its own Oracle connection.

    Returns:
        {
            "file": path,
            "success": True/False,
            "elapsed": seconds,
            "error": error_message
        }
    """

    start_time = time.perf_counter()

    connection = None
    cursor = None

    try:
        sql = read_query(path)

        if not sql:
            raise ValueError("SQL file is empty")

        connection = create_connection(args)
        cursor = connection.cursor()

        cursor.execute(sql)

        # If this is a SELECT, fetch all rows in batches.
        #
        # This is important because execute() can return before
        # the database has actually produced the complete result.
        if cursor.description:
            while True:
                rows = cursor.fetchmany(args.fetch_size)

                if not rows:
                    break

        elapsed = time.perf_counter() - start_time

        return {
            "file": path,
            "success": True,
            "elapsed": elapsed,
            "error": None,
        }

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        return {
            "file": path,
            "success": False,
            "elapsed": elapsed,
            "error": str(exc),
        }

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def format_query_name(path: Path):
    parsed = parse_query_file(path)

    if parsed is None:
        return path.name

    base_number, part_number = parsed

    if part_number == 0:
        return f"query{base_number}"

    return f"query{base_number}.{part_number}"


def main():
    parser = argparse.ArgumentParser(
        description="Run Oracle SQL query files concurrently."
    )

    parser.add_argument(
        "--query-dir",
        default="SupportingFiles/Clause4/queries_archive/qualification",
        help="Directory containing query*.sql files",
    )

    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="First base query number",
    )

    parser.add_argument(
        "--end",
        type=int,
        default=25,
        help="Last base query number",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of queries to run concurrently",
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="Oracle host",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=1521,
        help="Oracle port",
    )

    parser.add_argument(
        "--service",
        default="FREEPDB1",
        help="Oracle service name",
    )

    parser.add_argument(
        "--user",
        default="TPCDS",
        help="Oracle username",
    )

    parser.add_argument(
        "--password",
        required=True,
        help="Oracle password",
    )

    parser.add_argument(
        "--fetch-size",
        type=int,
        default=1000,
        help="Number of rows fetched at a time",
    )

    args = parser.parse_args()

    if args.start > args.end:
        parser.error("--start must be <= --end")

    query_dir = Path(args.query_dir)

    if not query_dir.exists():
        parser.error(f"Query directory does not exist: {query_dir}")

    files = find_query_files(
        query_dir,
        args.start,
        args.end,
    )

    if not files:
        print(
            f"No query files found for range "
            f"{args.start}-{args.end} in {query_dir}"
        )
        return 1

    print()
    print("=" * 70)
    print("Oracle Query Runner")
    print("=" * 70)
    print(f"Directory : {query_dir}")
    print(f"Range     : {args.start} - {args.end}")
    print(f"Workers   : {args.workers}")
    print(f"User      : {args.user}")
    print(f"Service   : {args.service}")
    print()
    print("Queries found:")

    for base_number, part_number, path in files:
        print(f"  {format_query_name(path):15} {path}")

    print()
    print("=" * 70)
    print()

    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:

        future_to_file = {
            executor.submit(
                execute_query,
                path,
                args,
            ): path
            for _, _, path in files
        }

        for future in as_completed(future_to_file):
            path = future_to_file[future]

            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "file": path,
                    "success": False,
                    "elapsed": 0,
                    "error": str(exc),
                }

            results.append(result)

            query_name = format_query_name(path)

            if result["success"]:
                print(
                    f"[OK]   {query_name:15} "
                    f"{result['elapsed']:.2f}s"
                )
            else:
                print(
                    f"[FAIL] {query_name:15} "
                    f"{result['elapsed']:.2f}s"
                )
                print(f"       {result['error']}")

    # Sort results in query order for the summary
    results.sort(
        key=lambda r: (
            parse_query_file(r["file"])[0],
            parse_query_file(r["file"])[1],
        )
    )

    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    print(f"Total  : {len(results)}")
    print(f"Passed : {len(successful)}")
    print(f"Failed : {len(failed)}")

    if failed:
        print()
        print("FAILED QUERIES:")
        print("-" * 70)

        for result in failed:
            print(format_query_name(result["file"]))
            print(result["error"])
            print()

    print("=" * 70)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())