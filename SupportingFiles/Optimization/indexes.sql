-- CREATE INDEX
CREATE INDEX idx_inv_date_item
ON inventory (inv_date_sk, inv_item_sk);

CREATE INDEX idx_cs_sold_date
ON catalog_sales (cs_sold_date_sk);

CREATE INDEX idx_cs_demo_item
ON catalog_sales (
    cs_bill_cdemo_sk,
    cs_item_sk
);

--CHECK USAGE
SELECT
    OWNER,
    NAME AS INDEX_NAME,
    TOTAL_ACCESS_COUNT,
    TOTAL_EXEC_COUNT,
    TOTAL_ROWS_RETURNED,
    LAST_USED
FROM DBA_INDEX_USAGE
WHERE OWNER = 'TPCDS'
ORDER BY TOTAL_ACCESS_COUNT DESC;