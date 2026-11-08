-- Reusable TPC-DS qualification summaries.
-- These views intentionally do not filter on a specific year, customer trait,
-- product category, or address offset.


CREATE MATERIALIZED VIEW mv_cust_year_store
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT c.c_customer_id,
       c.c_first_name,
       c.c_last_name,
       c.c_preferred_cust_flag,
       c.c_birth_country,
       c.c_login,
       c.c_email_address,
       d.d_year,
       SUM(((ss.ss_ext_list_price - ss.ss_ext_wholesale_cost
             - ss.ss_ext_discount_amt) + ss.ss_ext_sales_price) / 2)
           AS q4_total,
       SUM(ss.ss_ext_list_price - ss.ss_ext_discount_amt)
           AS q11_total,
       SUM(ss.ss_net_paid) AS q74_total
FROM store_sales ss
JOIN customer c ON c.c_customer_sk = ss.ss_customer_sk
JOIN date_dim d ON d.d_date_sk = ss.ss_sold_date_sk
GROUP BY c.c_customer_id,
         c.c_first_name,
         c.c_last_name,
         c.c_preferred_cust_flag,
         c.c_birth_country,
         c.c_login,
         c.c_email_address,
         d.d_year;



CREATE MATERIALIZED VIEW mv_cust_year_catalog
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT c.c_customer_id,
       c.c_first_name,
       c.c_last_name,
       c.c_preferred_cust_flag,
       c.c_birth_country,
       c.c_login,
       c.c_email_address,
       d.d_year,
       SUM(((cs.cs_ext_list_price - cs.cs_ext_wholesale_cost
             - cs.cs_ext_discount_amt) + cs.cs_ext_sales_price) / 2)
           AS q4_total,
       SUM(cs.cs_ext_list_price - cs.cs_ext_discount_amt)
           AS q11_total,
       SUM(cs.cs_net_paid) AS q74_total
FROM catalog_sales cs
JOIN customer c ON c.c_customer_sk = cs.cs_bill_customer_sk
JOIN date_dim d ON d.d_date_sk = cs.cs_sold_date_sk
GROUP BY c.c_customer_id,
         c.c_first_name,
         c.c_last_name,
         c.c_preferred_cust_flag,
         c.c_birth_country,
         c.c_login,
         c.c_email_address,
         d.d_year;


CREATE MATERIALIZED VIEW mv_cust_year_web
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT c.c_customer_id,
       c.c_first_name,
       c.c_last_name,
       c.c_preferred_cust_flag,
       c.c_birth_country,
       c.c_login,
       c.c_email_address,
       d.d_year,
       SUM(((ws.ws_ext_list_price - ws.ws_ext_wholesale_cost
             - ws.ws_ext_discount_amt) + ws.ws_ext_sales_price) / 2)
           AS q4_total,
       SUM(ws.ws_ext_list_price - ws.ws_ext_discount_amt)
           AS q11_total,
       SUM(ws.ws_net_paid) AS q74_total
FROM web_sales ws
JOIN customer c ON c.c_customer_sk = ws.ws_bill_customer_sk
JOIN date_dim d ON d.d_date_sk = ws.ws_sold_date_sk
GROUP BY c.c_customer_id,
         c.c_first_name,
         c.c_last_name,
         c.c_preferred_cust_flag,
         c.c_birth_country,
         c.c_login,
         c.c_email_address,
         d.d_year;





CREATE MATERIALIZED VIEW mv_item_month_store
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT i.i_item_id,
       i.i_item_sk,
       i.i_color,
       i.i_category,
       d.d_year,
       d.d_moy,
       ca.ca_gmt_offset,
       SUM(ss.ss_ext_sales_price) AS total_sales
FROM store_sales ss
JOIN item i ON i.i_item_sk = ss.ss_item_sk
JOIN date_dim d ON d.d_date_sk = ss.ss_sold_date_sk
JOIN customer_address ca ON ca.ca_address_sk = ss.ss_addr_sk
GROUP BY i.i_item_id,
         i.i_item_sk,
         i.i_color,
         i.i_category,
         d.d_year,
         d.d_moy,
         ca.ca_gmt_offset;


CREATE MATERIALIZED VIEW mv_item_month_catalog
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT i.i_item_id,
       i.i_item_sk,
       i.i_color,
       i.i_category,
       d.d_year,
       d.d_moy,
       ca.ca_gmt_offset,
       SUM(cs.cs_ext_sales_price) AS total_sales
FROM catalog_sales cs
JOIN item i ON i.i_item_sk = cs.cs_item_sk
JOIN date_dim d ON d.d_date_sk = cs.cs_sold_date_sk
JOIN customer_address ca ON ca.ca_address_sk = cs.cs_bill_addr_sk
GROUP BY i.i_item_id,
         i.i_item_sk,
         i.i_color,
         i.i_category,
         d.d_year,
         d.d_moy,
         ca.ca_gmt_offset;



CREATE MATERIALIZED VIEW mv_item_month_web
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
ENABLE QUERY REWRITE
AS
SELECT i.i_item_id,
       i.i_item_sk,
       i.i_color,
       i.i_category,
       d.d_year,
       d.d_moy,
       ca.ca_gmt_offset,
       SUM(ws.ws_ext_sales_price) AS total_sales
FROM web_sales ws
JOIN item i ON i.i_item_sk = ws.ws_item_sk
JOIN date_dim d ON d.d_date_sk = ws.ws_sold_date_sk
JOIN customer_address ca ON ca.ca_address_sk = ws.ws_bill_addr_sk
GROUP BY i.i_item_id,
         i.i_item_sk,
         i.i_color,
         i.i_category,
         d.d_year,
         d.d_moy,
         ca.ca_gmt_offset;

