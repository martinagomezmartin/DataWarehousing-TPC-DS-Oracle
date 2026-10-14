# Qualification templates for Oracle: changes per template

The folder `tpcds/DSGen-software-code-4.0.0/query_templates_qualification/` is a copy of the
kit's `query_templates/` (the originals are not modified). In the copy, every template was
changed so that `dsqgen` directly generates queries that:

- use the **official qualification parameters** (Appendix B of the TPC-DS specification),
- run on **Oracle**,
- return exactly the **official answer sets** (`answer_sets/*.ans`) on the SF=1 database.

The queries of this folder are generated from these templates:

```bash
cd tpcds/DSGen-software-code-4.0.0/tools
for t in ../query_templates_qualification/query*.tpl; do
  name=$(basename "$t" .tpl)
  ./dsqgen -template "$name.tpl" -directory ../query_templates_qualification \
           -dialect oracle -scale 1 -output_dir ../../../Queries/queries_templates_qualifications/
  mv ../../../Queries/queries_templates_qualifications/query_0.sql \
     "../../../Queries/queries_templates_qualifications/${name/_/.}.sql"
done
cd ../../..
```

Relative paths are required: `dsqgen` truncates long absolute paths.

Check the result (99/99 SUCCESS on our SF=1 database):

```bash
python3 Scripts/check_queries.py --query-dir Queries/queries_templates_qualifications \
    --answers-dir tpcds/DSGen-software-code-4.0.0/answer_sets --password password
```

### Building dsqgen 4.0.0 on macOS

The kit expects the Linux headers `values.h` and `malloc.h`. Small replacement headers
are enough (the kit sources are not modified):

```bash
cd tpcds/DSGen-software-code-4.0.0/tools
mkdir -p macos_include
printf '#include <limits.h>\n#include <float.h>\n#ifndef MAXINT\n#define MAXINT INT_MAX\n#endif\n' > macos_include/values.h
printf '#include <stdlib.h>\n' > macos_include/malloc.h
cp Makefile.suite Makefile
make OS=LINUX LINUX_CFLAGS="-g -Wno-implicit-function-declaration -Wno-implicit-int -Wno-int-conversion -Wno-deprecated-non-prototype -I$PWD/macos_include" dsqgen
```

## How the templates were changed

1. **Appendix B values written into the query text.** In a template, `[NAME]` (or `[NAME.k]`
   for a list) is replaced by `dsqgen` with a random value chosen by the `define NAME = ...;`
   line. In the qualification templates, these references are replaced by the Appendix B value
   (for example `and dt.d_moy=[MONTH]` → `and dt.d_moy=11`). The `define` lines are kept
   unchanged (some are used to compute other parameters), they simply have no effect anymore.
2. **Oracle adaptations** in the query text (dates, `days`, `EXCEPT`, ...).
3. **Templates with 2 statements split in two** (`queryN_1.tpl`, `queryN_2.tpl`), because
   the Python driver runs one statement per file.
4. Each modified template starts with a 2-line comment pointing to this file.

## Changes outside the query templates

- oracle.tpl: added `define _BEGIN = "";` and `define _END = "";`. `dsqgen` 4.0.0 requires these two substitutions, which the kit's Oracle dialect
  does not define. Empty values also remove the `-- start query` / `-- end query` comments.
- `templates.lst`: query14.tpl replaced by query14_1.tpl, query14_2.tpl
- `templates.lst`: query23.tpl replaced by query23_1.tpl, query23_2.tpl
- `templates.lst`: query24.tpl replaced by query24_1.tpl, query24_2.tpl
- `templates.lst`: query39.tpl replaced by query39_1.tpl, query39_2.tpl

## Changes per template

A parameter marked *(not in the query text)* is only used to compute another parameter
(for example `YEAR` to compute `SDATE`); the other parameter already has its Appendix B value.

### query1.tpl

- Appendix B values: `YEAR` = `2000`, `STATE` = `TN`, `AGG_FIELD` = `SR_RETURN_AMT`

### query2.tpl

- Appendix B values: `YEAR` = `2001`

### query3.tpl

- Appendix B values: `MONTH` = `11`, `MANUFACT` = `128`, `AGGC` = `ss_ext_sales_price`

### query4.tpl

- Appendix B values: `YEAR` = `2001`, `SELECTONE` = `t_s_secyear.customer_preferred_cust_flag`

### query5.tpl

- Appendix B values: `SALES_DATE` = `2000-08-23`, `YEAR` = `2000` *(not in the query text)*
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query6.tpl

- Appendix B values: `MONTH` = `1`, `YEAR` = `2001`

### query7.tpl

- Appendix B values: `YEAR` = `2000`, `ES` = `College`, `MS` = `S`, `GEN` = `M`

### query8.tpl

- Appendix B values (402): `ZIP.01` = `24128`, `ZIP.81` = `57834`, `ZIP.161` = `13354`, `ZIP.241` = `15734`, `ZIP.321` = `78668`, `ZIP.02` = `76232`, `ZIP.82` = `62878`, `ZIP.162` = `45375`, `ZIP.242` = `63435`, `ZIP.322` = `22245`, … (392 more of the same list)

### query9.tpl

- Appendix B values: `AGGCTHEN` = `ss_ext_discount_amt`, `AGGCELSE` = `ss_net_paid`, `RC.01` = `74129`, `RC.02` = `122840`, `RC.03` = `56580`, `RC.04` = `10097`, `RC.05` = `165306`

### query10.tpl

- Appendix B values: `YEAR` = `2002`, `MONTH` = `1`, `COUNTY.01` = `Rush County`, `COUNTY.02` = `Toole County`, `COUNTY.03` = `Jefferson County`, `COUNTY.04` = `Dona Ana County`, `COUNTY.05` = `La Porte County`

### query11.tpl

- Appendix B values: `YEAR` = `2001`, `SELECTONE` = `t_s_secyear.customer_preferred_cust_flag`

### query12.tpl

- Appendix B values: `CATEGORY.01` = `Sports`, `CATEGORY.02` = `Books`, `CATEGORY.03` = `Home`, `SDATE` = `1999-02-22`, `YEAR` = `1999` *(not in the query text)*
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query13.tpl

- Appendix B values (15): `STATE.01` = `TX`, `STATE.02` = `OH`, `STATE.03` = `TX`, `STATE.04` = `OR`, `STATE.05` = `NM`, `STATE.06` = `KY`, `STATE.07` = `VA`, `STATE.08` = `TX`, `STATE.09` = `MS`, `ES.01` = `Advanced Degree`, … (5 more of the same list)

### query14.tpl

- Appendix B values: `DAY` = `11`, `YEAR` = `1999`
- Oracle: 2 statements: split into query14_1.tpl and query14_2.tpl
- Files: query14_1.tpl, query14_2.tpl

### query15.tpl

- Appendix B values: `QOY` = `2`, `YEAR` = `2001`

### query16.tpl

- Appendix B values: `COUNTY_E` = `Williamson County`, `COUNTY_D` = `Williamson County`, `COUNTY_C` = `Williamson County`, `COUNTY_B` = `Williamson County`, `COUNTY_A` = `Williamson County`, `STATE` = `GA`, `MONTH` = `2`, `YEAR` = `2002`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: date compared to a string `'YYYY-MM-DD'` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query17.tpl

- Appendix B values: `YEAR` = `2001`

### query18.tpl

- Appendix B values (16): `MONTH.01` = `1`, `MONTH.02` = `6`, `MONTH.03` = `8`, `MONTH.04` = `9`, `MONTH.05` = `12`, `MONTH.06` = `2`, `STATE.01` = `MS`, `STATE.02` = `IN`, `STATE.03` = `ND`, `STATE.04` = `OK`, … (6 more of the same list)

### query19.tpl

- Appendix B values: `MANAGER` = `8`, `MONTH` = `11`, `YEAR` = `1998`

### query20.tpl

- Appendix B values: `CATEGORY.01` = `Sports`, `CATEGORY.02` = `Books`, `CATEGORY.03` = `Home`, `SDATE` = `1999-02-22`, `YEAR` = `1999` *(not in the query text)*
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query21.tpl

- Appendix B values: `SALES_DATE` = `2000-03-11`, `YEAR` = `2000` *(not in the query text)*
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query22.tpl

- Appendix B values: `DMS` = `1200`

### query23.tpl

- Appendix B values: `MONTH` = `2`, `YEAR` = `2000`, `TOPPERCENT` = `50`
- Oracle: 2 statements: split into query23_1.tpl and query23_2.tpl
- Files: query23_1.tpl, query23_2.tpl

### query24.tpl

- Appendix B values: `MARKET` = `8`, `COLOR.01` = `peach`, `COLOR.02` = `saddle`, `AMOUNTONE` = `ss_net_paid`
- Oracle: 2 statements: split into query24_1.tpl and query24_2.tpl
- Files: query24_1.tpl, query24_2.tpl

### query25.tpl

- Appendix B values: `YEAR` = `2001`, `AGG` = `sum`

### query26.tpl

- Appendix B values: `YEAR` = `2000`, `ES` = `College`, `MS` = `S`, `GEN` = `M`

### query27.tpl

- Appendix B values: `STATE_F` = `TN`, `STATE_E` = `TN`, `STATE_D` = `TN`, `STATE_C` = `TN`, `STATE_B` = `TN`, `STATE_A` = `TN`, `ES` = `College`, `MS` = `S`, `GEN` = `M`, `YEAR` = `2002`

### query28.tpl

- Appendix B values (18): `WHOLESALECOST.01` = `57`, `WHOLESALECOST.02` = `31`, `WHOLESALECOST.03` = `79`, `WHOLESALECOST.04` = `38`, `WHOLESALECOST.05` = `17`, `WHOLESALECOST.06` = `7`, `COUPONAMT.01` = `459`, `COUPONAMT.02` = `2323`, `COUPONAMT.03` = `12214`, `COUPONAMT.04` = `6071`, … (8 more of the same list)

### query29.tpl

- Appendix B values: `MONTH` = `9`, `YEAR` = `1999`, `AGG` = `sum`

### query30.tpl

- Appendix B values: `YEAR` = `2002`, `STATE` = `GA`

### query31.tpl

- Appendix B values: `YEAR` = `2000`, `AGG` = `ss1.ca_county`

### query32.tpl

- Appendix B values: `CSDATE` = `2000-01-27`, `YEAR` = `2000` *(not in the query text)*, `IMID` = `977`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: date compared to a string `'YYYY-MM-DD'` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query33.tpl

- Appendix B values: `CATEGORY` = `Electronics`, `GMT` = `-5`, `MONTH` = `5`, `YEAR` = `1998`

### query34.tpl

- Appendix B values: `COUNTY_H` = `Williamson County`, `COUNTY_G` = `Williamson County`, `COUNTY_F` = `Williamson County`, `COUNTY_E` = `Williamson County`, `COUNTY_D` = `Williamson County`, `COUNTY_C` = `Williamson County`, `COUNTY_B` = `Williamson County`, `COUNTY_A` = `Williamson County`, `YEAR` = `1999`, `BPTWO` = `Unknown`, `BPONE` = `>10000`

### query35.tpl

- Appendix B values: `YEAR` = `2002`, `AGGONE` = `min`, `AGGTWO` = `max`, `AGGTHREE` = `avg`

### query36.tpl

- Appendix B values: `STATE_H` = `TN`, `STATE_G` = `TN`, `STATE_F` = `TN`, `STATE_E` = `TN`, `STATE_D` = `TN`, `STATE_C` = `TN`, `STATE_B` = `TN`, `STATE_A` = `TN`, `YEAR` = `2001`

### query37.tpl

- Appendix B values: `PRICE` = `68`, `MANUFACT_ID.01` = `677`, `MANUFACT_ID.02` = `940`, `MANUFACT_ID.03` = `694`, `MANUFACT_ID.04` = `808`, `INVDATE` = `2000-02-01`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query38.tpl

- Appendix B values: `DMS` = `1200`

### query39.tpl

- Appendix B values: `YEAR` = `2001`, `MONTH` = `1`
- Oracle: 2 statements: split into query39_1.tpl and query39_2.tpl
- Files: query39_1.tpl, query39_2.tpl

### query40.tpl

- Appendix B values: `SALES_DATE` = `2000-03-11`, `YEAR` = `2000` *(not in the query text)*
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query41.tpl

- Appendix B values (39): `MANUFACT` = `738`, `SIZE.01` = `medium`, `SIZE.02` = `extra large`, `SIZE.03` = `N/A`, `SIZE.04` = `small`, `SIZE.05` = `petite`, `SIZE.06` = `large`, `UNIT.01` = `Ounce`, `UNIT.02` = `Oz`, `UNIT.03` = `Bunch`, … (29 more of the same list)

### query42.tpl

- Appendix B values: `MONTH` = `11`, `YEAR` = `2000`

### query43.tpl

- Appendix B values: `YEAR` = `2000`, `GMT` = `-5`

### query44.tpl

- Appendix B values: `NULLCOLSS` = `ss_addr_sk`, `STORE` = `4`
- Oracle: `/*+ NO_MERGE */` hints on the ranking subqueries (Oracle 26ai Free returns a wrong `rank() ... desc` when the views are merged)

### query45.tpl

- Appendix B values: `QOY` = `2`, `YEAR` = `2001`, `GBOBC` = `ca_city`

### query46.tpl

- Appendix B values: `CITY_E` = `Fairview`, `CITY_D` = `Fairview`, `CITY_C` = `Fairview`, `CITY_B` = `Midway`, `CITY_A` = `Fairview`, `VEHCNT` = `3`, `YEAR` = `1999`, `DEPCNT` = `4`

### query47.tpl

- Appendix B values: `YEAR` = `1999`, `SELECTONE` = `v1.i_category, v1.i_brand, v1.s_store_name, v1.s_company_name`, `SELECTTWO` = `,v1.d_year, v1.d_moy`, `ORDERBY` = `v1.s_store_name`
- Oracle: `v1.` prefix removed after `from v2` (final ORDER BY): only `v2` is visible there

### query48.tpl

- Appendix B values (16): `MS.01` = `M`, `MS.02` = `D`, `MS.03` = `S`, `ES.01` = `4 yr Degree`, `ES.02` = `2 yr Degree`, `ES.03` = `College`, `STATE.01` = `CO`, `STATE.02` = `OH`, `STATE.03` = `TX`, `STATE.04` = `OR`, … (6 more of the same list)

### query49.tpl

- Appendix B values: `MONTH` = `12`, `YEAR` = `2001`

### query50.tpl

- Appendix B values: `MONTH` = `8`, `YEAR` = `2001`

### query51.tpl

- Appendix B values: `DMS` = `1200`

### query52.tpl

- Appendix B values: `MONTH` = `11`, `YEAR` = `2000`

### query53.tpl

- Appendix B values: `DMS` = `1200`

### query54.tpl

- Appendix B values: `CLASS` = `maternity`, `CATEGORY` = `Women`, `MONTH` = `12`, `YEAR` = `1998`

### query55.tpl

- Appendix B values: `MANAGER` = `28`, `MONTH` = `11`, `YEAR` = `1999`

### query56.tpl

- Appendix B values: `COLOR.01` = `slate`, `COLOR.02` = `blanched`, `COLOR.03` = `burnished`, `GMT` = `-5`, `MONTH` = `2`, `YEAR` = `2001`

### query57.tpl

- Appendix B values: `YEAR` = `1999`, `SELECTONE` = `v1.i_category, v1.i_brand, v1.cc_name`, `SELECTTWO` = `,v1.d_year, v1.d_moy`, `ORDERBY` = `v1.cc_name`
- Oracle: `v1.` prefix removed after `from v2` (final ORDER BY): only `v2` is visible there

### query58.tpl

- Appendix B values: `SALES_DATE` = `2000-01-03`
- Oracle: date compared to a string `'YYYY-MM-DD'` → `DATE 'YYYY-MM-DD'`

### query59.tpl

- Appendix B values: `DMS` = `1212`

### query60.tpl

- Appendix B values: `CATEGORY` = `Music`, `GMT` = `-5`, `MONTH` = `9`, `YEAR` = `1998`

### query61.tpl

- Appendix B values: `GMT` = `-5`, `CATEGORY` = `Jewelry`, `MONTH` = `11`, `YEAR` = `1998`

### query62.tpl

- Appendix B values: `DMS` = `1200`

### query63.tpl

- Appendix B values: `DMS` = `1200`

### query64.tpl

- Appendix B values: `YEAR` = `1999`, `PRICE` = `64`, `COLOR.01` = `purple`, `COLOR.02` = `burlywood`, `COLOR.03` = `indian`, `COLOR.04` = `spring`, `COLOR.05` = `floral`, `COLOR.06` = `medium`

### query65.tpl

- Appendix B values: `DMS` = `1176`

### query66.tpl

- Appendix B values: `SALESTWO` = `cs_sales_price`, `SALESONE` = `ws_ext_sales_price`, `NETTWO` = `cs_net_paid_inc_tax`, `NETONE` = `ws_net_paid`, `SMC.01` = `DHL`, `SMC.02` = `BARIAN`, `TIMEONE` = `30838`, `YEAR` = `2001`

### query67.tpl

- Appendix B values: `DMS` = `1200`

### query68.tpl

- Appendix B values: `CITY_B` = `Midway`, `CITY_A` = `Fairview`, `VEHCNT` = `3`, `YEAR` = `1999`, `DEPCNT` = `4`

### query69.tpl

- Appendix B values: `STATE.01` = `KY`, `STATE.02` = `GA`, `STATE.03` = `NM`, `YEAR` = `2001`, `MONTH` = `4`

### query70.tpl

- Appendix B values: `DMS` = `1200`

### query71.tpl

- Appendix B values: `MANAGER` = `1` *(not in the query text)*, `MONTH` = `11`, `YEAR` = `1999`

### query72.tpl

- Appendix B values: `BP` = `>10000`, `MS` = `D`, `YEAR` = `1999`

### query73.tpl

- Appendix B values: `COUNTY_D` = `Orange County`, `COUNTY_C` = `Bronx County`, `COUNTY_B` = `Franklin Parish`, `COUNTY_A` = `Williamson County`, `YEAR` = `1999`, `BPTWO` = `Unknown`, `BPONE` = `>10000`

### query74.tpl

- Appendix B values: `YEAR` = `2001`, `AGGONE` = `sum`, `ORDERC.01` = `1`, `ORDERC.02` = `1`, `ORDERC.03` = `1`

### query75.tpl

- Appendix B values: `CATEGORY` = `Books`, `YEAR` = `2002`

### query76.tpl

- Appendix B values: `NULLCOLCS` = `cs_ship_addr_sk`, `NULLCOLWS` = `ws_ship_customer_sk`, `NULLCOLSS` = `ss_store_sk`

### query77.tpl

- Appendix B values: `SALES_DATE` = `2000-08-23`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query78.tpl

- Appendix B values: `YEAR` = `2000`, `SELECTONE` = `ss_sold_year, ss_item_sk, ss_customer_sk`

### query79.tpl

- Appendix B values: `VEHCNT` = `2`, `YEAR` = `1999`, `DEPCNT` = `6`

### query80.tpl

- Appendix B values: `SALES_DATE` = `2000-08-23`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query81.tpl

- Appendix B values: `YEAR` = `2000`, `STATE` = `GA`

### query82.tpl

- Appendix B values: `MANUFACT_ID.01` = `129`, `MANUFACT_ID.02` = `270`, `MANUFACT_ID.03` = `821`, `MANUFACT_ID.04` = `423`, `INVDATE` = `2000-05-25`, `PRICE` = `62`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query83.tpl

- Appendix B values: `RETURNED_DATE_THREE` = `2000-11-17`, `RETURNED_DATE_TWO` = `2000-09-27`, `RETURNED_DATE_ONE` = `2000-06-30`
- Oracle: date compared to a string `'YYYY-MM-DD'` → `DATE 'YYYY-MM-DD'`

### query84.tpl

- Appendix B values: `INCOME` = `38128`, `CITY` = `Edgewood`

### query85.tpl

- Appendix B values (16): `YEAR` = `2000`, `STATE.01` = `IN`, `STATE.02` = `OH`, `STATE.03` = `NJ`, `STATE.04` = `WI`, `STATE.05` = `CT`, `STATE.06` = `KY`, `STATE.07` = `LA`, `STATE.08` = `IA`, `STATE.09` = `AR`, … (6 more of the same list)

### query86.tpl

- Appendix B values: `DMS` = `1200`

### query87.tpl

- Appendix B values: `DMS` = `1200`
- Oracle: `EXCEPT` → `MINUS`

### query88.tpl

- Appendix B values: `STORE` = `Unknown` *(not in the query text)*, `HOUR.01` = `4`, `HOUR.02` = `2`, `HOUR.03` = `0`

### query89.tpl

- Appendix B values (13): `CLASS_F` = `dresses`, `CAT_F` = `Women`, `CLASS_E` = `birdal`, `CAT_E` = `Jewelry`, `CLASS_D` = `shirts`, `CAT_D` = `Men`, `CLASS_C` = `football`, `CAT_C` = `Sports`, `CLASS_B` = `stereo`, `CAT_B` = `Electronics`, … (3 more of the same list)

### query90.tpl

- Appendix B values: `HOUR_PM` = `19`, `HOUR_AM` = `8`, `DEPCNT` = `6`

### query91.tpl

- Appendix B values: `YEAR` = `1998`, `MONTH` = `11`, `BUY_POTENTIAL` = `Unknown`, `GMT` = `-7`

### query92.tpl

- Appendix B values: `IMID` = `350`, `WSDATE` = `2000-01-27`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: date compared to a string `'YYYY-MM-DD'` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query93.tpl

- Appendix B values: `REASON` = `reason 28`

### query94.tpl

- Appendix B values: `YEAR` = `1999`, `MONTH` = `2`, `STATE` = `IL`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: date compared to a string `'YYYY-MM-DD'` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query95.tpl

- Appendix B values: `STATE` = `IL`, `MONTH` = `2`, `YEAR` = `1999`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: date compared to a string `'YYYY-MM-DD'` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query96.tpl

- Appendix B values: `HOUR` = `20`, `DEPCNT` = `7`

### query97.tpl

- Appendix B values: `DMS` = `1200`

### query98.tpl

- Appendix B values: `YEAR` = `1999` *(not in the query text)*, `SDATE` = `1999-02-22`, `CATEGORY.01` = `Sports`, `CATEGORY.02` = `Books`, `CATEGORY.03` = `Home`
- Oracle: `cast('YYYY-MM-DD' as date)` → `DATE 'YYYY-MM-DD'`
- Oracle: `+ N days` → `+ N`

### query99.tpl

- Appendix B values: `DMS` = `1200`
