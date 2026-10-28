-- TPC-DS Data Maintenance views (spec 5.3.11.1 to 5.3.11.7), adapted for Oracle.
-- Changes from the spec (minor query modifications, spec 4.2.3):
--   1. cast(x as date) -> to_date(x, 'YYYY-MM-DD')  (Oracle default NLS_DATE_FORMAT is DD-MON-RR)
--   2. ticket/order numbers + offset from dm_offset: dsdgen 4.0.0 restarts the ids at 1
--      in every refresh set, which collides with the primary keys of the fact tables.
--      data_maintenance.py sets the offset to the current max id before the inserts.
--   3. csv: catalog_page joined on its surrogate key (see the comment in csv).
--   4. wsv, csv, iv join item_latest (latest version of each item) instead of
--      i_rec_end_date IS NULL: at SF2 dsdgen writes an item whose only version is
--      closed (i_item_sk 26000), the refresh data uses it, and the insert fails
--      on the NOT NULL item_sk.

create or replace view item_latest as
SELECT * FROM item
WHERE i_item_sk IN (SELECT max(i_item_sk) FROM item GROUP BY i_item_id);

create or replace view ssv as
SELECT d_date_sk ss_sold_date_sk,
       t_time_sk ss_sold_time_sk,
       i_item_sk ss_item_sk,
       c_customer_sk ss_customer_sk,
       c_current_cdemo_sk ss_cdemo_sk,
       c_current_hdemo_sk ss_hdemo_sk,
       c_current_addr_sk ss_addr_sk,
       s_store_sk ss_store_sk,
       p_promo_sk ss_promo_sk,
       purc_purchase_id + (SELECT ss_k FROM dm_offset) ss_ticket_number,
       plin_quantity ss_quantity,
       i_wholesale_cost ss_wholesale_cost,
       i_current_price ss_list_price,
       plin_sale_price ss_sales_price,
       (i_current_price-plin_sale_price)*plin_quantity ss_ext_discount_amt,
       plin_sale_price * plin_quantity ss_ext_sales_price,
       i_wholesale_cost * plin_quantity ss_ext_wholesale_cost,
       i_current_price * plin_quantity ss_ext_list_price,
       i_current_price * s_tax_precentage ss_ext_tax,
       plin_coupon_amt ss_coupon_amt,
       (plin_sale_price * plin_quantity)-plin_coupon_amt ss_net_paid,
       ((plin_sale_price * plin_quantity)-plin_coupon_amt)*(1+s_tax_precentage) ss_net_paid_inc_tax,
       ((plin_sale_price * plin_quantity)-plin_coupon_amt)-(plin_quantity*i_wholesale_cost) ss_net_profit
FROM s_purchase
LEFT OUTER JOIN customer ON (purc_customer_id = c_customer_id)
LEFT OUTER JOIN store ON (purc_store_id = s_store_id)
LEFT OUTER JOIN date_dim ON (to_date(purc_purchase_date, 'YYYY-MM-DD') = d_date)
LEFT OUTER JOIN time_dim ON (purc_purchase_time = t_time)
JOIN s_purchase_lineitem ON (purc_purchase_id = plin_purchase_id)
LEFT OUTER JOIN promotion ON plin_promotion_id = p_promo_id
LEFT OUTER JOIN item ON plin_item_id = i_item_id
WHERE purc_purchase_id = plin_purchase_id
  AND i_rec_end_date is NULL
  AND s_rec_end_date is NULL;

create or replace view srv as
SELECT d_date_sk sr_returned_date_sk
      ,t_time_sk sr_return_time_sk
      ,i_item_sk sr_item_sk
      ,c_customer_sk sr_customer_sk
      ,c_current_cdemo_sk sr_cdemo_sk
      ,c_current_hdemo_sk sr_hdemo_sk
      ,c_current_addr_sk sr_addr_sk
      ,s_store_sk sr_store_sk
      ,r_reason_sk sr_reason_sk
      ,to_number(sret_ticket_number) + (SELECT ss_k FROM dm_offset) sr_ticket_number
      ,sret_return_qty sr_return_quantity
      ,sret_return_amt sr_return_amt
      ,sret_return_tax sr_return_tax
      ,sret_return_amt + sret_return_tax sr_return_amt_inc_tax
      ,sret_return_fee sr_fee
      ,sret_return_ship_cost sr_return_ship_cost
      ,sret_refunded_cash sr_refunded_cash
      ,sret_reversed_charge sr_reversed_charge
      ,sret_store_credit sr_store_credit
      ,sret_return_amt+sret_return_tax+sret_return_fee
       -sret_refunded_cash-sret_reversed_charge-sret_store_credit sr_net_loss
FROM s_store_returns
LEFT OUTER JOIN date_dim
  ON (to_date(sret_return_date, 'YYYY-MM-DD') = d_date)
LEFT OUTER JOIN time_dim
  ON (( cast(substr(sret_return_time,1,2) AS integer)*3600
       +cast(substr(sret_return_time,4,2) AS integer)*60
       +cast(substr(sret_return_time,7,2) AS integer)) = t_time)
LEFT OUTER JOIN item ON (sret_item_id = i_item_id)
LEFT OUTER JOIN customer ON (sret_customer_id = c_customer_id)
LEFT OUTER JOIN store ON (sret_store_id = s_store_id)
LEFT OUTER JOIN reason ON (sret_reason_id = r_reason_id)
WHERE i_rec_end_date IS NULL
  AND s_rec_end_date IS NULL;

create or replace view wsv as
SELECT d1.d_date_sk ws_sold_date_sk,
       t_time_sk ws_sold_time_sk,
       d2.d_date_sk ws_ship_date_sk,
       i_item_sk ws_item_sk,
       c1.c_customer_sk ws_bill_customer_sk,
       c1.c_current_cdemo_sk ws_bill_cdemo_sk,
       c1.c_current_hdemo_sk ws_bill_hdemo_sk,
       c1.c_current_addr_sk ws_bill_addr_sk,
       c2.c_customer_sk ws_ship_customer_sk,
       c2.c_current_cdemo_sk ws_ship_cdemo_sk,
       c2.c_current_hdemo_sk ws_ship_hdemo_sk,
       c2.c_current_addr_sk ws_ship_addr_sk,
       wp_web_page_sk ws_web_page_sk,
       web_site_sk ws_web_site_sk,
       sm_ship_mode_sk ws_ship_mode_sk,
       w_warehouse_sk ws_warehouse_sk,
       p_promo_sk ws_promo_sk,
       word_order_id + (SELECT ws_k FROM dm_offset) ws_order_number,
       wlin_quantity ws_quantity,
       i_wholesale_cost ws_wholesale_cost,
       i_current_price ws_list_price,
       wlin_sales_price ws_sales_price,
       (i_current_price-wlin_sales_price)*wlin_quantity ws_ext_discount_amt,
       wlin_sales_price * wlin_quantity ws_ext_sales_price,
       i_wholesale_cost * wlin_quantity ws_ext_wholesale_cost,
       i_current_price * wlin_quantity ws_ext_list_price,
       i_current_price * web_tax_percentage ws_ext_tax,
       wlin_coupon_amt ws_coupon_amt,
       wlin_ship_cost * wlin_quantity ws_ext_ship_cost,
       (wlin_sales_price * wlin_quantity)-wlin_coupon_amt ws_net_paid,
       ((wlin_sales_price * wlin_quantity)-wlin_coupon_amt)*(1+web_tax_percentage) ws_net_paid_inc_tax,
       ((wlin_sales_price * wlin_quantity)-wlin_coupon_amt)-(wlin_quantity*i_wholesale_cost) ws_net_paid_inc_ship,
       (wlin_sales_price * wlin_quantity)-wlin_coupon_amt + (wlin_ship_cost * wlin_quantity)
       + i_current_price * web_tax_percentage ws_net_paid_inc_ship_tax,
       ((wlin_sales_price * wlin_quantity)-wlin_coupon_amt)-(i_wholesale_cost * wlin_quantity) ws_net_profit
FROM s_web_order
LEFT OUTER JOIN date_dim d1 ON (to_date(word_order_date, 'YYYY-MM-DD') = d1.d_date)
LEFT OUTER JOIN time_dim ON (word_order_time = t_time)
LEFT OUTER JOIN customer c1 ON (word_bill_customer_id = c1.c_customer_id)
LEFT OUTER JOIN customer c2 ON (word_ship_customer_id = c2.c_customer_id)
LEFT OUTER JOIN web_site ON (word_web_site_id = web_site_id AND web_rec_end_date IS NULL)
LEFT OUTER JOIN ship_mode ON (word_ship_mode_id = sm_ship_mode_id)
JOIN s_web_order_lineitem ON (word_order_id = wlin_order_id)
LEFT OUTER JOIN date_dim d2 ON (to_date(wlin_ship_date, 'YYYY-MM-DD') = d2.d_date)
LEFT OUTER JOIN item_latest item ON (wlin_item_id = i_item_id)
LEFT OUTER JOIN web_page ON (wlin_web_page_id = wp_web_page_id AND wp_rec_end_date IS NULL)
LEFT OUTER JOIN warehouse ON (wlin_warehouse_id = w_warehouse_id)
LEFT OUTER JOIN promotion ON (wlin_promotion_id = p_promo_id);

create or replace view wrv as
SELECT d_date_sk wr_return_date_sk
      ,t_time_sk wr_return_time_sk
      ,i_item_sk wr_item_sk
      ,c1.c_customer_sk wr_refunded_customer_sk
      ,c1.c_current_cdemo_sk wr_refunded_cdemo_sk
      ,c1.c_current_hdemo_sk wr_refunded_hdemo_sk
      ,c1.c_current_addr_sk wr_refunded_addr_sk
      ,c2.c_customer_sk wr_returning_customer_sk
      ,c2.c_current_cdemo_sk wr_returning_cdemo_sk
      ,c2.c_current_hdemo_sk wr_returning_hdemo_sk
      ,c2.c_current_addr_sk wr_returing_addr_sk
      ,wp_web_page_sk wr_web_page_sk
      ,r_reason_sk wr_reason_sk
      ,wret_order_id + (SELECT ws_k FROM dm_offset) wr_order_number
      ,wret_return_qty wr_return_quantity
      ,wret_return_amt wr_return_amt
      ,wret_return_tax wr_return_tax
      ,wret_return_amt + wret_return_tax AS wr_return_amt_inc_tax
      ,wret_return_fee wr_fee
      ,wret_return_ship_cost wr_return_ship_cost
      ,wret_refunded_cash wr_refunded_cash
      ,wret_reversed_charge wr_reversed_charge
      ,wret_account_credit wr_account_credit
      ,wret_return_amt+wret_return_tax+wret_return_fee
       -wret_refunded_cash-wret_reversed_charge-wret_account_credit wr_net_loss
FROM s_web_returns
LEFT OUTER JOIN date_dim ON (to_date(wret_return_date, 'YYYY-MM-DD') = d_date)
LEFT OUTER JOIN time_dim ON ((CAST(SUBSTR(wret_return_time,1,2) AS integer)*3600
  +CAST(SUBSTR(wret_return_time,4,2) AS integer)*60
  +CAST(SUBSTR(wret_return_time,7,2) AS integer)) = t_time)
LEFT OUTER JOIN item ON (wret_item_id = i_item_id)
LEFT OUTER JOIN customer c1 ON (wret_return_customer_id = c1.c_customer_id)
LEFT OUTER JOIN customer c2 ON (wret_refund_customer_id = c2.c_customer_id)
LEFT OUTER JOIN reason ON (wret_reason_id = r_reason_id)
LEFT OUTER JOIN web_page ON (wret_web_page_id = wp_web_page_id)
WHERE i_rec_end_date IS NULL AND wp_rec_end_date IS NULL;

create or replace view csv as
SELECT d1.d_date_sk cs_sold_date_sk
      ,t_time_sk cs_sold_time_sk
      ,d2.d_date_sk cs_ship_date_sk
      ,c1.c_customer_sk cs_bill_customer_sk
      ,c1.c_current_cdemo_sk cs_bill_cdemo_sk
      ,c1.c_current_hdemo_sk cs_bill_hdemo_sk
      ,c1.c_current_addr_sk cs_bill_addr_sk
      ,c2.c_customer_sk cs_ship_customer_sk
      ,c2.c_current_cdemo_sk cs_ship_cdemo_sk
      ,c2.c_current_hdemo_sk cs_ship_hdemo_sk
      ,c2.c_current_addr_sk cs_ship_addr_sk
      ,cc_call_center_sk cs_call_center_sk
      ,cp_catalog_page_sk cs_catalog_page_sk
      ,sm_ship_mode_sk cs_ship_mode_sk
      ,w_warehouse_sk cs_warehouse_sk
      ,i_item_sk cs_item_sk
      ,p_promo_sk cs_promo_sk
      ,cord_order_id + (SELECT cs_k FROM dm_offset) cs_order_number
      ,clin_quantity cs_quantity
      ,i_wholesale_cost cs_wholesale_cost
      ,i_current_price cs_list_price
      ,clin_sales_price cs_sales_price
      ,(i_current_price-clin_sales_price)*clin_quantity cs_ext_discount_amt
      ,clin_sales_price * clin_quantity cs_ext_sales_price
      ,i_wholesale_cost * clin_quantity cs_ext_wholesale_cost
      ,i_current_price * clin_quantity cs_ext_list_price
      ,i_current_price * cc_tax_percentage cs_ext_tax
      ,clin_coupon_amt cs_coupon_amt
      ,clin_ship_cost * clin_quantity cs_ext_ship_cost
      ,(clin_sales_price * clin_quantity)-clin_coupon_amt cs_net_paid
      ,((clin_sales_price * clin_quantity)-clin_coupon_amt)*(1+cc_tax_percentage) cs_net_paid_inc_tax
      ,(clin_sales_price * clin_quantity)-clin_coupon_amt + (clin_ship_cost * clin_quantity) cs_net_paid_inc_ship
      ,(clin_sales_price * clin_quantity)-clin_coupon_amt + (clin_ship_cost * clin_quantity)
       + i_current_price * cc_tax_percentage cs_net_paid_inc_ship_tax
      ,((clin_sales_price * clin_quantity)-clin_coupon_amt)-(clin_quantity*i_wholesale_cost) cs_net_profit
FROM s_catalog_order
LEFT OUTER JOIN date_dim d1 ON (to_date(cord_order_date, 'YYYY-MM-DD') = d1.d_date)
LEFT OUTER JOIN time_dim ON (cord_order_time = t_time)
LEFT OUTER JOIN customer c1 ON (cord_bill_customer_id = c1.c_customer_id)
LEFT OUTER JOIN customer c2 ON (cord_ship_customer_id = c2.c_customer_id)
LEFT OUTER JOIN call_center ON (cord_call_center_id = cc_call_center_id AND cc_rec_end_date IS NULL)
LEFT OUTER JOIN ship_mode ON (cord_ship_mode_id = sm_ship_mode_id)
JOIN s_catalog_order_lineitem ON (cord_order_id = clin_order_id)
LEFT OUTER JOIN date_dim d2 ON (to_date(clin_ship_date, 'YYYY-MM-DD') = d2.d_date)
-- dsdgen writes the catalog_page surrogate key in clin_catalog_page_number
-- (s_catalog_order_lineitem.c: mk_join(..., CATALOG_PAGE, ...)), so join on cp_catalog_page_sk
LEFT OUTER JOIN catalog_page ON (clin_catalog_page_number = cp_catalog_page_sk)
LEFT OUTER JOIN warehouse ON (clin_warehouse_id = w_warehouse_id)
LEFT OUTER JOIN item_latest item ON (clin_item_id = i_item_id)
LEFT OUTER JOIN promotion ON (clin_promotion_id = p_promo_id);

create or replace view crv as
SELECT d_date_sk cr_returned_date_sk
      ,t_time_sk cr_returned_time_sk
      ,i_item_sk cr_item_sk
      ,c1.c_customer_sk cr_refunded_customer_sk
      ,c1.c_current_cdemo_sk cr_refunded_cdemo_sk
      ,c1.c_current_hdemo_sk cr_refunded_hdemo_sk
      ,c1.c_current_addr_sk cr_refunded_addr_sk
      ,c2.c_customer_sk cr_returning_customer_sk
      ,c2.c_current_cdemo_sk cr_returning_cdemo_sk
      ,c2.c_current_hdemo_sk cr_returning_hdemo_sk
      ,c2.c_current_addr_sk cr_returing_addr_sk
      ,cc_call_center_sk cr_call_center_sk
      ,cp_catalog_page_sk cr_catalog_page_sk
      ,sm_ship_mode_sk cr_ship_mode_sk
      ,w_warehouse_sk cr_warehouse_sk
      ,r_reason_sk cr_reason_sk
      ,cret_order_id + (SELECT cs_k FROM dm_offset) cr_order_number
      ,cret_return_qty cr_return_quantity
      ,cret_return_amt cr_return_amt
      ,cret_return_tax cr_return_tax
      ,cret_return_amt + cret_return_tax AS cr_return_amt_inc_tax
      ,cret_return_fee cr_fee
      ,cret_return_ship_cost cr_return_ship_cost
      ,cret_refunded_cash cr_refunded_cash
      ,cret_reversed_charge cr_reversed_charge
      ,cret_merchant_credit cr_merchant_credit
      ,cret_return_amt+cret_return_tax+cret_return_fee
       -cret_refunded_cash-cret_reversed_charge-cret_merchant_credit cr_net_loss
FROM s_catalog_returns
LEFT OUTER JOIN date_dim ON (to_date(cret_return_date, 'YYYY-MM-DD') = d_date)
LEFT OUTER JOIN time_dim ON ((CAST(substr(cret_return_time,1,2) AS integer)*3600
  +CAST(substr(cret_return_time,4,2) AS integer)*60
  +CAST(substr(cret_return_time,7,2) AS integer)) = t_time)
LEFT OUTER JOIN item ON (cret_item_id = i_item_id)
LEFT OUTER JOIN customer c1 ON (cret_return_customer_id = c1.c_customer_id)
LEFT OUTER JOIN customer c2 ON (cret_refund_customer_id = c2.c_customer_id)
LEFT OUTER JOIN reason ON (cret_reason_id = r_reason_id)
LEFT OUTER JOIN call_center ON (cret_call_center_id = cc_call_center_id)
LEFT OUTER JOIN catalog_page ON (cret_catalog_page_id = cp_catalog_page_id)
LEFT OUTER JOIN ship_mode ON (cret_shipmode_id = sm_ship_mode_id)
LEFT OUTER JOIN warehouse ON (cret_warehouse_id = w_warehouse_id)
WHERE i_rec_end_date IS NULL AND cc_rec_end_date IS NULL;

create or replace view iv as
SELECT d_date_sk inv_date_sk,
       i_item_sk inv_item_sk,
       w_warehouse_sk inv_warehouse_sk,
       invn_qty_on_hand inv_quantity_on_hand
FROM s_inventory
LEFT OUTER JOIN warehouse ON (invn_warehouse_id = w_warehouse_id)
LEFT OUTER JOIN item_latest item ON (invn_item_id = i_item_id)
LEFT OUTER JOIN date_dim ON (d_date = to_date(invn_date, 'YYYY-MM-DD'));
