#!/usr/bin/env python3

import argparse
import datetime
import re
from collections import defaultdict
from pathlib import Path

from run_queries import (
    create_connection,
    find_query_files,
    read_query,
)


DASH_LINE = re.compile(r"^-+( +-+)*\s*$")
OUTPUT_LINE = re.compile(r"^-+\s*OUTPUT", re.IGNORECASE)

# Lines that are not data: row counts, SQL*Plus / DB2 messages, echoed query
NOISE_LINE = re.compile(
    r"^(\d+ rows? selected\.|no rows selected|\(\d+ rows?\)|\d+ record\(s\) selected\."
    r"|SQL\*Plus:|SQL>|Copyright|Elapsed:|Connected|Disconnected|select\s)",
    re.IGNORECASE,
)

# Markers used for NULL in the answer sets (NULL gives no token on our side)
NULL_MARKERS = {"%", "-", "[NULL]"}


def find_answer_files(answers_dir: Path, base_number: int):
    """
    Returns the candidate answer files for a query.

    Oracle sorts NULLs last in ascending order, so the
    NULLS_LAST version is tried first.
    """

    candidates = [
        answers_dir / f"{base_number}.ans",
        answers_dir / f"{base_number}_NULLS_LAST.ans",
        answers_dir / f"{base_number}_NULLS_FIRST.ans",
    ]

    return [path for path in candidates if path.exists()]


def parse_answer_file(path: Path):
    """
    Read a TPC-DS .ans file and return its data rows as lists of tokens.

    Two formats exist in the answer sets:
        - SQL*Plus fixed width: header line, then a line of dashes
        - pipe separated: header line, then values separated by |

    Headers, dash lines, blank lines, row counts and SQL*Plus / DB2
    messages are ignored. NULL markers (%, -, [NULL]) give no token.
    """

    raw = path.read_bytes()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    lines = text.expandtabs(8).splitlines()

    rows = []
    previous_blank = True

    # SQL*Plus wraps long rows over several lines. In that case the header
    # is wrapped too (several header/dash pairs), one pair per line of a row.
    lines_per_row = 1
    in_header = False
    pending_tokens = []
    pending_lines = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        if not stripped:
            previous_blank = True
            continue

        if re.match(r"^(SQL>\s*)?Disconnected", stripped):
            # End of a SQL*Plus session: the rest is the Oracle banner
            break

        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""

        if next_line and DASH_LINE.match(next_line):
            # Header line (fixed width format)
            lines_per_row = lines_per_row + 1 if in_header else 1
            in_header = True
            pending_tokens, pending_lines = [], 0
            continue

        if DASH_LINE.match(stripped):
            continue

        in_header = False

        if "|" in stripped and previous_blank:
            # Header line (pipe format): first line of a section
            previous_blank = False
            lines_per_row = 1
            continue

        previous_blank = False

        if OUTPUT_LINE.match(stripped) or NOISE_LINE.match(stripped):
            continue

        fields = stripped.split("|") if "|" in stripped else [stripped]

        pending_tokens.extend(
            token
            for field in fields
            for token in field.split()
            if token not in NULL_MARKERS
        )
        pending_lines += 1

        if pending_lines == lines_per_row:
            rows.append(pending_tokens)
            pending_tokens, pending_lines = [], 0

    return rows


def value_to_tokens(value):
    """
    Convert an Oracle value to tokens, the same way as the .ans rows.
    NULL gives no token (it is shown as an empty field in the .ans).
    """

    if value is None:
        return []

    if isinstance(value, datetime.datetime):
        if value.time() == datetime.time(0, 0):
            return [value.strftime("%Y-%m-%d")]
        return value.strftime("%Y-%m-%d %H:%M:%S").split()

    return str(value).split()


def tokens_equal(actual: str, expected: str):
    """
    Numbers are compared with the precision shown in the .ans file
    (the answer sets contain rounded values).
    """

    if actual == expected:
        return True

    try:
        a = float(actual)
        b = float(expected)
    except ValueError:
        return False

    decimals = len(expected.split(".")[1]) if "." in expected and "e" not in expected.lower() else 0
    tolerance = max(0.5 * 10 ** -decimals, abs(b) * 1e-6) + 1e-9

    return abs(a - b) <= tolerance


def rows_equal(actual_row, expected_row):
    if len(actual_row) != len(expected_row):
        return False

    return all(tokens_equal(a, b) for a, b in zip(actual_row, expected_row))


def compare_rows(actual, expected):
    """
    Returns (success, message).

    Rows are first compared in order. If that fails, they are compared
    ignoring the order (ties in ORDER BY can be returned differently).
    """

    if len(actual) != len(expected):
        # Some .ans files wrap a long row over several lines: compare all the
        # values in order, whatever the line breaks
        actual_values = [token for row in actual for token in row]
        expected_values = [token for row in expected for token in row]

        if expected_values and rows_equal(actual_values, expected_values):
            return True, f"{len(actual)} rows identical (rows wrapped in the .ans)"

        return False, f"{len(actual)} rows, expected {len(expected)}"

    first_difference = None

    for index, (actual_row, expected_row) in enumerate(zip(actual, expected), start=1):
        if not rows_equal(actual_row, expected_row):
            first_difference = (index, actual_row, expected_row)
            break

    if first_difference is None:
        return True, f"{len(actual)} rows identical"

    remaining = list(expected)

    for actual_row in actual:
        match = next((r for r in remaining if rows_equal(actual_row, r)), None)

        if match is None:
            break

        remaining.remove(match)

    if not remaining:
        return True, f"{len(actual)} rows identical (different order)"

    index, actual_row, expected_row = first_difference

    return False, (
        f"row {index} differs\n"
        f"         got      : {' '.join(actual_row)}\n"
        f"         expected : {' '.join(expected_row)}"
    )


def run_query(connection, path: Path):
    sql = read_query(path)

    if not sql:
        raise ValueError("SQL file is empty")

    with connection.cursor() as cursor:
        cursor.execute(sql)

        if not cursor.description:
            return []

        return [
            [token for value in row for token in value_to_tokens(value)]
            for row in cursor.fetchall()
        ]


def main():
    parser = argparse.ArgumentParser(
        description="Run TPC-DS queries and compare their results with the official answer sets."
    )

    parser.add_argument("--query-dir", default="SupportingFiles/Clause4/queries_archive/qualification", help="Directory containing query*.sql files")
    parser.add_argument(
        "--answers-dir",
        default=str(Path.home() / "tpcds-kit" / "answer_sets"),
        help="Directory containing the TPC-DS .ans files",
    )
    parser.add_argument("--start", type=int, default=1, help="First base query number")
    parser.add_argument("--end", type=int, default=99, help="Last base query number")
    parser.add_argument("--host", default="localhost", help="Oracle host")
    parser.add_argument("--port", type=int, default=1521, help="Oracle port")
    parser.add_argument("--service", default="FREEPDB1", help="Oracle service name")
    parser.add_argument("--user", default="TPCDS", help="Oracle username")
    parser.add_argument("--password", required=True, help="Oracle password")

    args = parser.parse_args()

    query_dir = Path(args.query_dir)
    answers_dir = Path(args.answers_dir).expanduser()

    if not query_dir.exists():
        parser.error(f"Query directory does not exist: {query_dir}")

    if not answers_dir.exists():
        parser.error(f"Answers directory does not exist: {answers_dir}")

    # query14.1.sql and query14.2.sql are compared together with 14.ans
    queries = defaultdict(list)

    for base_number, _, path in find_query_files(query_dir, args.start, args.end):
        queries[base_number].append(path)

    if not queries:
        print(f"No query files found for range {args.start}-{args.end} in {query_dir}")
        return 1

    print()
    print("=" * 70)
    print("TPC-DS Answer Checker")
    print("=" * 70)
    print(f"Queries : {query_dir}")
    print(f"Answers : {answers_dir}")
    print(f"Range   : {args.start} - {args.end}")
    print("=" * 70)
    print()

    results = {"SUCCESS": [], "FAILED": [], "ERROR": [], "NO ANSWER": []}

    connection = create_connection(args)

    try:
        for base_number in sorted(queries):
            paths = queries[base_number]
            name = f"query{base_number}"

            answer_files = find_answer_files(answers_dir, base_number)

            if not answer_files:
                print(f"[SKIP]    {name:10} no .ans file")
                results["NO ANSWER"].append(name)
                continue

            try:
                actual = []

                for path in paths:
                    actual.extend(run_query(connection, path))

            except Exception as exc:
                print(f"[ERROR]   {name:10} {exc}")
                results["ERROR"].append(name)
                continue

            outcome = None

            for answer_file in answer_files:
                success, message = compare_rows(actual, parse_answer_file(answer_file))

                if success or outcome is None:
                    outcome = (success, message, answer_file.name)

                if success:
                    break

            success, message, answer_name = outcome

            if success:
                print(f"[SUCCESS] {name:10} {message} ({answer_name})")
                results["SUCCESS"].append(name)
            else:
                print(f"[FAILED]  {name:10} {message} ({answer_name})")
                results["FAILED"].append(name)

    finally:
        connection.close()

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)

    for status, names in results.items():
        print(f"{status:10}: {len(names)}")

        if names and status != "SUCCESS":
            print(f"            {', '.join(names)}")

    print("=" * 70)

    return 0 if not results["FAILED"] and not results["ERROR"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
