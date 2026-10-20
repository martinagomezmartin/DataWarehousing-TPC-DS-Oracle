# TPC-DS + Oracle setup



## 1. Get the TPC-DS data

Follow the instructions in:
- /Docs/TPCDS_SETUP_GUIDE


Use `dsdgen` to generate the TPC-DS `.dat` files.


## 2. Install Oracle

Install Oracle Database 

Create a database/schema that we will use for TPC-DS.


## 3. Create the TPC-DS tables

Use the `tpcds.sql` file to create the tables. It is in the DSDGen software in ./tools directory


Main change from the original TPC-DS table definition:

```text
TIME -> VARCHAR2(8)
```
TIME format didn't work for me in Oracle so I change it to VARCHAR
 

## 4. Load the `.dat` files into Oracle

The Python loader is in:

```text
scripts/load_data.py
```


To run it add your oracle configuration:

```bash
python scripts/load_data.py \
    --data-dir ./data \
    --user TPCDS \
    --password "YOUR_PASSWORD" \
    --host localhost \
    --port 1521 \
    --service FREEPDB1 \
    --batch-size 10000
```

The script will read the `.dat` files from `data/` and load them into the Oracle TPC-DS schema.



## Project files

```text
Docs/        -> setup/generation documentation
scripts/     -> Python data-loading script
queries/     -> generated Oracle SQL queries
```


## Changes in Quries
Date Type. 
with CAST Oracle is trying to convert a string to a date using a format that doesn’t match the string instead use racle’s format-independent date literal:
```
CAST('1998-08-04' AS DATE) -> DATE '1998-08-04'

CAST(('1998-08-04' AS DATE) + 14 days )->
DATE '1998-08-04' + 14
```

```
cast(d_date as date) -> (d_date)
```



In queries 14, 21, 24 did not work, there were 2 separate queries I have splitted into 2 sub-queries

### Changes by Amine (queries 40, 58, 69, 77, 80 and tests 50 to 75)

Comparing a DATE column with a string relies on the session date format and fails.
Use a date literal instead (query 58):

```
d_date = '1998-02-19' -> d_date = DATE '1998-02-19'
```

Queries 40, 58, 77 and 80 were fixed with these rules. Query 69 needed no change.
Queries 50 to 75 all run successfully on SF=1.

### Changes by Imad  (queries 32, 37, 39 and tests 25 to 50)

Queries 32 and 37: `CAST('...' AS DATE) + N days` -> `DATE '...' + N`. Query 39 contained 2 queries, split into `query39.1.sql` and `query39.2.sql`.
Queries 25 to 50 all run successfully on SF=1.

## Gather statistics after loading (Amine)

After loading the data, run:

BEGIN
  DBMS_STATS.GATHER_SCHEMA_STATS('TPCDS');
END;

Without statistics, the optimizer picks bad execution plans.
Example: query 69 took about 440 s without statistics and 0.41 s with them.


# TPC-DS Query Benchmark

### Setup
Run from the DataWarehousing-TPC-DS-Oracle/ directory :
```bash
export ORACLE_USER=TPCDS
export ORACLE_DSN=localhost:1521/FREEPDB1
read ORACLE_PASSWORD
export ORACLE_PASSWORD

# Dependencies (install once)
pip install oracledb sqlparse
chmod +x run_benchmark.sh
```

### Run Benchmark

```bash
./run_benchmark.sh 1 0      # Power Test
./run_benchmark.sh 1 1 4    # Throughput Test 1
./run_benchmark.sh 1 5 8    # Throughput Test 2
```

- First argument: Scale
- Other arguments: stream range
- Output: `results/SF1/` (CSV files per stream)
