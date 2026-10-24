import argparse
import csv
import os
import time
from datetime import date
from pathlib import Path

import oracledb
import sqlparse

ROOT = Path(__file__).resolve().parent
DM_DIR = ROOT / "DataMaintenance"
CSV_COLUMNS = ["refresh_run", "step", "elapsed_s", "row_count", "start_ns", "end_ns"]

# Source schema tables loaded from the refresh data set (spec Table 5-1)
STAGING_TABLES = [
    "s_purchase", "s_purchase_lineitem", "s_store_returns",
    "s_catalog_order", "s_catalog_order_lineitem", "s_catalog_returns",
    "s_web_order", "s_web_order_lineitem", "s_web_returns",
    "s_inventory",
]

# Method 2 (spec 5.3.8): returns R first, then sales S, for d_date between Date1 and Date2
SALES_DELETES = [
    ("DF_SS", "store_returns", "sr_item_sk, sr_ticket_number",
     "store_sales", "ss_item_sk, ss_ticket_number", "ss_sold_date_sk"),
    ("DF_CS", "catalog_returns", "cr_item_sk, cr_order_number",
     "catalog_sales", "cs_item_sk, cs_order_number", "cs_sold_date_sk"),
    ("DF_WS", "web_returns", "wr_item_sk, wr_order_number",
     "web_sales", "ws_item_sk, ws_order_number", "ws_sold_date_sk"),
]

# Method 1 (spec 5.3.7): insert every row of view V into fact table F
INSERTS = [
    ("LF_SS", "store_sales", "ssv"),
    ("LF_SR", "store_returns", "srv"),
    ("LF_CS", "catalog_sales", "csv"),
    ("LF_CR", "catalog_returns", "crv"),
    ("LF_WS", "web_sales", "wsv"),
    ("LF_WR", "web_returns", "wrv"),
    ("LF_I", "inventory", "iv"),
]

SET_OFFSETS = """
update dm_offset set
    ss_k = (select nvl(max(ss_ticket_number), 0) from store_sales),
    cs_k = (select nvl(max(cs_order_number), 0) from catalog_sales),
    ws_k = (select nvl(max(ws_order_number), 0) from web_sales)
"""


def connect():
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ.get("ORACLE_DSN", "localhost:1521/FREEPDB1"),
    )


def run_sql_file(cursor, path):
    """Execute every statement of a .sql file (comment-only chunks are skipped)"""
    for sql in sqlparse.split(path.read_text(encoding="utf-8")):
        sql = sql.strip().removesuffix(";").strip()
        if sqlparse.format(sql, strip_comments=True).strip():
            cursor.execute(sql)


def setup():
    """Create the staging tables and the views (not timed, done once)"""
    with connect() as connection, connection.cursor() as cursor:
        for table in STAGING_TABLES + ["dm_offset"]:
            try:
                cursor.execute(f"drop table {table} purge")
            except oracledb.DatabaseError:
                pass  # Table did not exist yet.
        run_sql_file(cursor, DM_DIR / "create_staging.sql")
        run_sql_file(cursor, DM_DIR / "views.sql")
    print("Staging tables and views created.")


def read_dat(path):
    """Rows of a dsdgen flat file: '|' separated, trailing '|', empty field = NULL"""
    with path.open(encoding="latin-1") as dat_file:
        for line in dat_file:
            fields = line.rstrip("\r\n").split("|")
            if fields and fields[-1] == "":
                fields.pop()
            yield [field if field != "" else None for field in fields]


def load_staging(cursor, table, path, batch_size=10000):
    """Empty one staging table and load its refresh file into it"""
    cursor.execute(f"truncate table {table}")
    column_count = cursor.execute(
        "select count(*) from user_tab_columns where table_name = :1", [table.upper()]
    ).fetchone()[0]
    sql = f"insert into {table} values ({', '.join(f':{i}' for i in range(1, column_count + 1))})"
    rows = 0
    batch = []
    for fields in read_dat(path):
        batch.append(fields)
        if len(batch) == batch_size:
            cursor.executemany(sql, batch)
            rows += len(batch)
            batch = []
    if batch:
        cursor.executemany(sql, batch)
        rows += len(batch)
    return rows


def read_dates(path):
    """The 3 (Date1, Date2) pairs of delete_<n>.dat / inventory_delete_<n>.dat"""
    return [(date.fromisoformat(d1), date.fromisoformat(d2)) for d1, d2 in read_dat(path)]


def delete_sales(cursor, returns, returns_key, sales, sales_key, date_col, dates):
    rows = 0
    for date1, date2 in dates:
        cursor.execute(
            f"""delete from {returns} where ({returns_key}) in (
                    select {sales_key} from {sales}
                    join date_dim on {date_col} = d_date_sk
                    where d_date between :1 and :2)""",
            [date1, date2],
        )
        rows += cursor.rowcount
        cursor.execute(
            f"""delete from {sales} where {date_col} in (
                    select d_date_sk from date_dim where d_date between :1 and :2)""",
            [date1, date2],
        )
        rows += cursor.rowcount
    return rows


def delete_inventory(cursor, dates):
    rows = 0
    for date1, date2 in dates:
        cursor.execute(
            """delete from inventory where inv_date_sk in (
                   select d_date_sk from date_dim where d_date between :1 and :2)""",
            [date1, date2],
        )
        rows += cursor.rowcount
    return rows


def run_refresh(connection, refresh_run, data_dir, writer, rollback):
    """One refresh run: load refresh set n, all deletes, then all inserts, commit"""
    cursor = connection.cursor()
    run_start = time.perf_counter_ns()

    def step(name, action):
        start_ns = time.perf_counter_ns()
        row_count = action()
        end_ns = time.perf_counter_ns()
        writer.writerow({
            "refresh_run": refresh_run, "step": name,
            "elapsed_s": (end_ns - start_ns) / 1_000_000_000,
            "row_count": row_count, "start_ns": start_ns, "end_ns": end_ns,
        })
        print(f"[Refresh {refresh_run}] {name}: {row_count} rows, "
              f"{(end_ns - start_ns) / 1e9:.2f}s", flush=True)

    # 1. Load the refresh data set into the staging area (timed, spec 5.2.5)
    for table in STAGING_TABLES:
        path = data_dir / f"{table}_{refresh_run}.dat"
        step(f"load_{table}", lambda: load_staging(cursor, table, path))
    sales_dates = read_dates(data_dir / f"delete_{refresh_run}.dat")
    inventory_dates = read_dates(data_dir / f"inventory_delete_{refresh_run}.dat")

    # 2. All deletes before any insert (spec 5.1.3 d)
    for name, returns, returns_key, sales, sales_key, date_col in SALES_DELETES:
        step(name, lambda: delete_sales(cursor, returns, returns_key, sales,
                                        sales_key, date_col, sales_dates))
    step("DF_I", lambda: delete_inventory(cursor, inventory_dates))

    # 3. Inserts (ticket/order numbers shifted after the current max, see views.sql)
    step("set_offsets", lambda: cursor.execute(SET_OFFSETS) or cursor.rowcount)
    for name, table, view in INSERTS:
        step(name, lambda: cursor.execute(f"insert into {table} select * from {view}")
             or cursor.rowcount)

    # 4. Make the changes visible (or undo them in test mode)
    if rollback:
        step("rollback", lambda: connection.rollback() or 0)
    else:
        step("commit", lambda: connection.commit() or 0)

    run_end = time.perf_counter_ns()
    writer.writerow({
        "refresh_run": refresh_run, "step": "TOTAL",
        "elapsed_s": (run_end - run_start) / 1_000_000_000,
        "row_count": "", "start_ns": run_start, "end_ns": run_end,
    })
    print(f"[Refresh {refresh_run}] Finished at {time.strftime('%Y-%m-%d %H:%M:%S')} "
          f"({(run_end - run_start) / 1e9:.2f}s)", flush=True)
    return run_start, run_end


def run(first, last, output_dir, data_dir, rollback):
    """Execute refresh runs first..last one after the other (spec 7.4.8.6)"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "data_maintenance.csv"
    with connect() as connection, output_file.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        times = [run_refresh(connection, n, data_dir, writer, rollback)
                 for n in range(first, last + 1)]
    elapsed = (times[-1][1] - times[0][0]) / 1_000_000_000
    print(f"T_DM (refresh runs {first}-{last}) = {elapsed:.2f}s"
          + ("  [ROLLBACK: database unchanged]" if rollback else ""))
    print(f"Raw results: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="TPC-DS Oracle data maintenance")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup", help="create staging tables and views (once)")
    run_parser = sub.add_parser("run", help="execute refresh runs FIRST..LAST")
    run_parser.add_argument("first", type=int)
    run_parser.add_argument("last", type=int)
    run_parser.add_argument("output_dir", type=Path)
    run_parser.add_argument("--data-dir", type=Path, required=True,
                            help="directory with the dsdgen -update files")
    run_parser.add_argument("--rollback", action="store_true",
                            help="test mode: undo the deletes/inserts at the end")
    args = parser.parse_args()

    if args.command == "setup":
        setup()
    else:
        run(args.first, args.last, args.output_dir, args.data_dir, args.rollback)


if __name__ == "__main__":
    main()
