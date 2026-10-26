# TPC-DS benchmark on Oracle

Implementation of the [TPC-DS](https://www.tpc.org/tpcds/) decision support benchmark (specification
v4.0.0) on Oracle Database Free, for Part I of the Data Warehouses group project.

The whole benchmark runs through a single script, `tpcds.sh`: it compiles the TPC-DS tools, generates
the data, loads it into Oracle and executes the benchmark sequence of the specification (clause 7.4.2):

```text
Load Test -> Power Test -> Throughput Test 1 -> Data Maintenance 1 -> Throughput Test 2 -> Data Maintenance 2
```

> **Before running anything: put your own Oracle settings in a `.env` file.**
>
> ```bash
> cp .env.example .env
> ```
>
> Then open `.env` and set `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_HOST`, `ORACLE_PORT`,
> `ORACLE_SERVICE`, `DATA_DIR` and `TPCDS_TOOLS` for your machine. `.env` is ignored by Git:
> never commit it. `tpcds.sh` reads it automatically, no `export` needed.

---

## 1. Requirements

| Component | Version used | Notes |
|---|---|---|
| Docker Desktop | latest | runs the Oracle container |
| Oracle Database Free | 23ai / 26ai (`gvenzl/oracle-free` image) | limited to 2 CPU threads, 2 GB RAM, 12 GB of user data |
| Python | 3.10+ | packages in `requirements.txt` (`oracledb`, `sqlparse`) |
| C compiler + make | Xcode Command Line Tools (macOS) or gcc (Linux) | to build `dsdgen` / `dsqgen` |
| TPC-DS kit | DSGen 4.0.0 | free download from tpc.org (not redistributed in this repository) |

## 2. Installation

### 2.1 Oracle in Docker

```bash
docker run -d --name oracle-tpcds -p 1521:1521 \
    -e ORACLE_PASSWORD=<admin_password> \
    -e APP_USER=TPCDS -e APP_USER_PASSWORD=<tpcds_password> \
    gvenzl/oracle-free
```

This creates the pluggable database `FREEPDB1` with the schema `TPCDS`. Afterwards, start it with
`docker start oracle-tpcds`.

### 2.2 TPC-DS kit

Download *TPC-DS Tools 4.0.0* from tpc.org and unzip it in `tpcds/`, so that the tools are in
`tpcds/DSGen-software-code-4.0.0/tools` (or set another path in `TPCDS_TOOLS`).

### 2.3 Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2.4 Configuration

```bash
cp .env.example .env      # then edit .env with your values
chmod +x tpcds.sh
```

## 3. Running the benchmark

Every command is run from the project root, with the virtual environment active.

### 3.1 Preparation (once)

```bash
./tpcds.sh build             # compile dsdgen and dsqgen (macOS headers are handled)
./tpcds.sh generate 1        # base data sf1 + refresh data sets 1-4 (repeat for each scale factor)
./tpcds.sh validate          # 99 qualification queries vs the official answer sets (SF1)
```

### 3.2 Full benchmark for one scale factor

```bash
./tpcds.sh all 1
```

### 3.3 Individual tests

```bash
./tpcds.sh load 1            # drop the schema, create tables, load sf1, gather statistics -> T_Load
./tpcds.sh power 1           # Power Test, stream 0                                     -> T_Power
./tpcds.sh throughput 1 1    # Throughput Test 1, streams 1-4 in parallel                -> T_TT1
./tpcds.sh dm 1 1            # Data Maintenance Test 1, refresh runs 1-2                 -> T_DM1
./tpcds.sh throughput 1 2    # Throughput Test 2, streams 5-8 in parallel                -> T_TT2
./tpcds.sh dm 1 2            # Data Maintenance Test 2, refresh runs 3-4                 -> T_DM2

./tpcds.sh dm 1 1 --rollback # test the data maintenance and undo it (database unchanged)
./tpcds.sh dm-setup          # recreate the data maintenance staging tables and views
./tpcds.sh help              # list every command
```

The first argument is the scale factor. Data is read from `DATA_DIR/sf<SF>/` and
`DATA_DIR/sf<SF>_update/`.

> The data maintenance **modifies the database**. After a run without `--rollback`, reload the data
> (`./tpcds.sh load <SF>`) before starting a new benchmark.

### 3.4 Results

Each test writes its raw results in `results/SF<SF>/<date>_<test>/`:

| Test | File | Content |
|---|---|---|
| load | `load.csv` | T_Load in seconds |
| power, throughput | `stream_<n>.csv` | one row per query: position, query id, elapsed time, row count, status, start/end timestamps |
| dm | `data_maintenance.csv` | one row per step of each refresh run (load, DF_*, LF_*, commit) + one `TOTAL` row per run |

`results/` is ignored by Git. The CSV files of the final runs are copied to `Report/results/`.

## 4. Benchmark configuration

| Parameter | Value | Specification |
|---|---|---|
| Scale factors | 1, 2, 5 and the reference scale factor (largest that fits the machine) | 3.1, project statement |
| Query streams per Throughput Test (Sq) | 4 | 7.4.6.9 (even, at least 4) |
| Stream order | Appendix D, stored in `SupportingFiles/Clause7/streams_order.json` | 7.4.4.4, 7.4.6.11 |
| Refresh runs per Data Maintenance Test | Sq / 2 = 2 | 7.4.8.3 |
| Refresh data sets | 4 (`dsdgen -update 1..4`) | 5.1.1, 5.2.1 |

Performance metric (clause 7.6.3), times in hours:

```text
QphDS@SF = floor( SF * Q / (T_PT * T_TT * T_DM * T_LD) ^ (1/4) )

Q    = Sq * 99
T_PT = T_Power * Sq
T_TT = T_TT1 + T_TT2
T_DM = T_DM1 + T_DM2
T_LD = 0.01 * Sq * T_Load
```

T_Load covers table creation, data load, statistics and the creation of the data maintenance objects
(clause 7.4.3.7). Data generation with `dsdgen` is not timed (clauses 7.4.3.8.1 and 5.2.3).

## 5. Repository layout

The supporting files follow the clause numbering of the specification (clauses 10.2.4 and 10.9).

```text
.
├── README.md
├── .env.example                 template of the Oracle settings (.env is ignored by Git)
├── requirements.txt
├── tpcds.sh                     single entry point
├── Report/                      final report (PDF) and results of the final runs
└── SupportingFiles/
    ├── Introduction/            installation guide
    ├── Clause2/                 table creation: tpcds_oracle.sql
    ├── Clause3/                 database population: load_data.py, dsdgen validation data
    ├── Clause4/                 queries
    │   ├── queries/             the 99 benchmark queries (query01.sql ... query99.sql)
    │   ├── queries_archive/     previous versions: original, imad, qualification, oracle_fixed
    │   ├── check_queries.py     comparison with the official answer sets
    │   └── run_queries.py       runs a range of queries and reports OK / FAIL
    ├── Clause5/                 data maintenance: data_maintenance.py, create_staging.sql, views.sql
    └── Clause7/                 benchmark driver: benchmark_queries.py, streams_order.json
```

## 6. Oracle adaptations

### 6.1 Tables (Clause 2)

`SupportingFiles/Clause2/tpcds_oracle.sql` is `tools/tpcds.sql` from the kit with one change:

```text
TIME -> VARCHAR2(8)
```

The `TIME` type does not exist in Oracle.

### 6.2 Queries (Clause 4)

The queries are generated with `dsqgen -qualify Y -dialect oracle` and adapted to Oracle with minor
query modifications (clause 4.2.3).

Dates: `CAST` depends on the session date format (`DD-MON-RR` by default), so date literals are used:

```text
CAST('1998-08-04' AS DATE)            -> DATE '1998-08-04'
CAST('1998-08-04' AS DATE) + 14 days  -> DATE '1998-08-04' + 14
cast(d_date as date)                  -> d_date
d_date = '1998-02-19'                 -> d_date = DATE '1998-02-19'
```

Queries 14, 23, 24 and 39 contain two SQL statements. In `queries/` both statements are in one file,
so that they are executed and timed as one query (clause 7.1.12).

Contributions:
- Amine: queries 40, 58, 69, 77, 80; tests of queries 50 to 75.
- Imad: queries 32, 37, 39; tests of queries 25 to 50.

`./tpcds.sh validate` compares the 99 qualification queries with the official answer sets of the kit
(clause 7.3): 99/99 match on SF1.

### 6.3 Statistics

Statistics are gathered at the end of the load (`DBMS_STATS.GATHER_SCHEMA_STATS`), as part of T_Load
(clause 7.2.9). Without statistics the optimizer picks bad execution plans: query 69 took about 440 s
without statistics and 0.41 s with them.

### 6.4 Data maintenance (Clause 5)

Each refresh run (`SupportingFiles/Clause5/data_maintenance.py`):

1. loads the 10 flat files of the refresh data set into the source schema tables `s_*` (5.2.5);
2. reads the 3 date ranges of `delete_<n>.dat` and `inventory_delete_<n>.dat`;
3. deletes the returns then the sales of these dates (DF_SS, DF_CS, DF_WS) and the inventory (DF_I),
   all deletes before any insert (5.1.3, 5.3.8, 5.3.9);
4. inserts the new rows through the views of clause 5.3.11 (LF_SS, LF_SR, LF_CS, LF_CR, LF_WS, LF_WR,
   LF_I) (5.3.7);
5. commits and prints a time-stamped message (5.1.3, 5.1.4).

Adaptations of the views and staging tables:
- `cast(x as date)` -> `to_date(x, 'YYYY-MM-DD')`;
- dsdgen 4.0.0 restarts the ticket / order numbers at 1 in every refresh set, which violates the
  primary keys of the fact tables: the numbers are shifted after the current maximum (table `dm_offset`);
- `s_web_returns` is missing from `tools/tpcds_source.sql`: created from Appendix A (Table A-9);
- `s_catalog_returns`: dsdgen writes the warehouse id before the catalog page id;
- `csv`: dsdgen writes the catalog page surrogate key in `clin_catalog_page_number`, so catalog_page is
  joined on `cp_catalog_page_sk`.

## 7. Deviations and limitations

- The same qualification parameters are used in every query stream (the specification generates
  different substitution parameters per stream with `dsqgen -streams`).
- dsdgen writes an invalid call center id in `s_catalog_order`: in the inserted catalog sales,
  `cs_call_center_sk` and the tax columns that depend on it are NULL.
- No data accessibility test (Clause 6) and no pricing (Clauses 7.6.5 and 9): not part of the project.
- Oracle Database Free limits the reference scale factor (12 GB of user data, 2 GB of RAM).