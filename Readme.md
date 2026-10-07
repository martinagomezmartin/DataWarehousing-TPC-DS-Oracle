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
