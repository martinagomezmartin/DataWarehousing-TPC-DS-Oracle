import argparse
import csv
import os
import time
from datetime import datetime
from decimal import Decimal

import oracledb


def get_table_columns(connection, table_name):
    """
    Get the columns of an Oracle table in their defined order.
    """

    sql = """
        SELECT
            column_name,
            data_type,
            data_length,
            data_precision,
            data_scale
        FROM user_tab_columns
        WHERE table_name = :table_name
        ORDER BY column_id
    """

    with connection.cursor() as cursor:
        cursor.execute(
            sql,
            table_name=table_name.upper()
        )
        columns = cursor.fetchall()

    if not columns:
        raise RuntimeError(
            f"Oracle table '{table_name.upper()}' does not exist."
        )

    return columns


def convert_value(value, column):
    """
    Convert a value from the .dat file according to the
    Oracle column type.
    """

    column_name = column[0]
    data_type = column[1]
    data_scale = column[4]

    # Empty TPC-DS field = NULL
    if value == "":
        return None

    # NUMBER
    if data_type == "NUMBER":

        try:
            if data_scale is not None and data_scale > 0:
                return Decimal(value)

            return int(value)

        except ValueError as exc:
            raise ValueError(
                f"Invalid NUMBER '{value}' "
                f"for column {column_name}"
            ) from exc

    # DATE
    if data_type == "DATE":

        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        raise ValueError(
            f"Invalid DATE '{value}' "
            f"for column {column_name}"
        )

    # CHAR / VARCHAR2
    if data_type in (
        "CHAR",
        "VARCHAR2",
        "VARCHAR",
        "NCHAR",
        "NVARCHAR2"
    ):
        return value

    return value


def build_insert_sql(table_name, columns):

    column_names = [
        column[0]
        for column in columns
    ]

    columns_sql = ", ".join(column_names)

    binds_sql = ", ".join(
        f":{i}"
        for i in range(1, len(columns) + 1)
    )

    return f"""
        INSERT INTO {table_name.upper()}
        ({columns_sql})
        VALUES ({binds_sql})
    """


def load_file(connection, file_path, batch_size):

    # customer.dat -> CUSTOMER
    table_name = os.path.splitext(
        os.path.basename(file_path)
    )[0].upper()

    print()
    print("=" * 70)
    print(f"TABLE: {table_name}")
    print(f"FILE:  {file_path}")
    print("=" * 70)

    # Get Oracle schema
    columns = get_table_columns(
        connection,
        table_name
    )

    expected_columns = len(columns)

    print(f"Oracle columns: {expected_columns}")

    insert_sql = build_insert_sql(
        table_name,
        columns
    )

    total_rows = 0
    batch = []

    start_time = time.time()

    with open(
        file_path,
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.reader(
            file,
            delimiter="|"
        )

        with connection.cursor() as cursor:

            for line_number, row in enumerate(
                reader,
                start=1
            ):

                # Ignore empty lines
                if not row:
                    continue

                # TPC-DS rows end with '|'
                #
                # Example:
                #
                # 1|ABC|123|
                #
                # csv.reader produces:
                #
                # ['1', 'ABC', '123', '']
                #
                # Remove the final empty field.
                if row[-1] == "":
                    row = row[:-1]

                if len(row) != expected_columns:

                    raise ValueError(
                        f"\nColumn mismatch!\n"
                        f"Table:    {table_name}\n"
                        f"File:     {file_path}\n"
                        f"Line:     {line_number}\n"
                        f"Expected: {expected_columns}\n"
                        f"Found:    {len(row)}\n"
                        f"Row:      {row}"
                    )

                converted_row = [
                    convert_value(value, column)
                    for value, column
                    in zip(row, columns)
                ]

                batch.append(converted_row)

                if len(batch) >= batch_size:

                    cursor.executemany(
                        insert_sql,
                        batch
                    )

                    connection.commit()

                    total_rows += len(batch)

                    elapsed = time.time() - start_time

                    rate = (
                        total_rows / elapsed
                        if elapsed > 0
                        else 0
                    )

                    print(
                        f"  {total_rows:,} rows "
                        f"({rate:,.0f} rows/sec)"
                    )

                    batch.clear()

            # Remaining rows
            if batch:

                cursor.executemany(
                    insert_sql,
                    batch
                )

                connection.commit()

                total_rows += len(batch)

    elapsed = time.time() - start_time

    rate = (
        total_rows / elapsed
        if elapsed > 0
        else 0
    )

    print()
    print(
        f"Finished {table_name}: "
        f"{total_rows:,} rows "
        f"in {elapsed:.2f}s "
        f"({rate:,.0f} rows/sec)"
    )

    return total_rows

def create_tables(connection):
    path = os.path.join(os.path.dirname(__file__), "tpcds_oracle.sql")

    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM user_tables")

        if cursor.fetchone()[0] != 0:
            raise RuntimeError("The database already contains tables")

        with open(path, encoding="utf-8") as sql_file:
            sql = "".join(
                line for line in sql_file
                if not line.lstrip().startswith("--")
            )

        for statement in sql.split(";"):
            if statement.strip():
                cursor.execute(statement.strip())

def main():

    parser = argparse.ArgumentParser(
        description="Automatically load all TPC-DS .dat files into Oracle."
    )

    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory containing the .dat files"
    )

    parser.add_argument(
        "--host",
        default="localhost"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=1521
    )

    parser.add_argument(
        "--service",
        default="FREEPDB1"
    )

    parser.add_argument(
        "--user",
        default="TPCDS"
    )

    parser.add_argument(
        "--password",
        required=True
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10000
    )

    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate each table before loading"
    )

    parser.add_argument(
        "--create-tables",
        action="store_true"
    )
    
    args = parser.parse_args()

    # ------------------------------------------------------------
    # Find all .dat files
    # ------------------------------------------------------------

    data_dir = os.path.abspath(
        args.data_dir
    )

    if not os.path.isdir(data_dir):
        raise RuntimeError(
            f"Data directory does not exist: {data_dir}"
        )

    files = sorted(
        os.path.join(data_dir, filename)
        for filename in os.listdir(data_dir)
        if filename.lower().endswith(".dat")
    )

    if not files:
        raise RuntimeError(
            f"No .dat files found in {data_dir}"
        )

    print()
    print("=" * 70)
    print("TPC-DS AUTOMATIC LOADER")
    print("=" * 70)
    print(f"Data directory: {data_dir}")
    print(f"Files found:    {len(files)}")
    print(f"Oracle:         {args.host}:{args.port}/{args.service}")
    print(f"User:           {args.user}")
    print(f"Batch size:     {args.batch_size}")
    print("=" * 70)

    print()
    print("Files to load:")

    for file_path in files:
        print(
            f"  {os.path.basename(file_path)}"
        )

    # ------------------------------------------------------------
    # Connect
    # ------------------------------------------------------------

    print()
    print("Connecting to Oracle...")

    dsn = oracledb.makedsn(
        args.host,
        args.port,
        service_name=args.service
    )

    connection = oracledb.connect(
        user=args.user,
        password=args.password,
        dsn=dsn
    )

    print("Connected successfully.")

    # ------------------------------------------------------------
    # Load every file
    # ------------------------------------------------------------

    overall_start = time.time()

    results = {}

    try:

        #creating the tables
        if args.create_tables:
            create_tables(connection)
            
        for file_path in files:

            table_name = os.path.splitext(
                os.path.basename(file_path)
            )[0].upper()

            try:

                if args.truncate:

                    print()
                    print(
                        f"Truncating {table_name}..."
                    )

                    with connection.cursor() as cursor:
                        cursor.execute(
                            f"TRUNCATE TABLE {table_name}"
                        )

                    connection.commit()

                row_count = load_file(
                    connection,
                    file_path,
                    args.batch_size
                )

                results[table_name] = row_count

            except Exception as exc:

                connection.rollback()

                print()
                print("=" * 70)
                print(f"ERROR loading {table_name}")
                print("=" * 70)
                print(str(exc))

                raise

    finally:

        connection.close()

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    elapsed = time.time() - overall_start

    print()
    print()
    print("=" * 70)
    print("LOAD SUMMARY")
    print("=" * 70)

    total_rows = 0

    for table_name, count in results.items():

        print(
            f"{table_name:<30} "
            f"{count:>15,} rows"
        )

        total_rows += count

    print("-" * 70)

    print(
        f"{'TOTAL':<30} "
        f"{total_rows:>15,} rows"
    )

    print()
    print(
        f"Total loading time: {elapsed:.2f} seconds"
    )

    print()
    print("All files loaded successfully.")


if __name__ == "__main__":
    main()
