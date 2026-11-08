-- 
-- Legal Notice 
-- 
-- This document and associated source code (the "Work") is a part of a 
-- benchmark specification maintained by the TPC. 
-- 
-- The TPC reserves all right, title, and interest to the Work as provided 
-- under U.S. and international laws, including without limitation all patent 
-- and trademark rights therein. 
-- 
-- No Warranty 
-- 
-- 1.1 TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE INFORMATION 
--     CONTAINED HEREIN IS PROVIDED "AS IS" AND WITH ALL FAULTS, AND THE 
--     AUTHORS AND DEVELOPERS OF THE WORK HEREBY DISCLAIM ALL OTHER 
--     WARRANTIES AND CONDITIONS, EITHER EXPRESS, IMPLIED OR STATUTORY, 
--     INCLUDING, BUT NOT LIMITED TO, ANY (IF ANY) IMPLIED WARRANTIES, 
--     DUTIES OR CONDITIONS OF MERCHANTABILITY, OF FITNESS FOR A PARTICULAR 
--     PURPOSE, OF ACCURACY OR COMPLETENESS OF RESPONSES, OF RESULTS, OF 
--     WORKMANLIKE EFFORT, OF LACK OF VIRUSES, AND OF LACK OF NEGLIGENCE. 
--     ALSO, THERE IS NO WARRANTY OR CONDITION OF TITLE, QUIET ENJOYMENT, 
--     QUIET POSSESSION, CORRESPONDENCE TO DESCRIPTION OR NON-INFRINGEMENT 
--     WITH REGARD TO THE WORK. 
-- 1.2 IN NO EVENT WILL ANY AUTHOR OR DEVELOPER OF THE WORK BE LIABLE TO 
--     ANY OTHER PARTY FOR ANY DAMAGES, INCLUDING BUT NOT LIMITED TO THE 
--     COST OF PROCURING SUBSTITUTE GOODS OR SERVICES, LOST PROFITS, LOSS 
--     OF USE, LOSS OF DATA, OR ANY INCIDENTAL, CONSEQUENTIAL, DIRECT, 
--     INDIRECT, OR SPECIAL DAMAGES WHETHER UNDER CONTRACT, TORT, WARRANTY,
--     OR OTHERWISE, ARISING IN ANY WAY OUT OF THIS OR ANY OTHER AGREEMENT 
--     RELATING TO THE WORK, WHETHER OR NOT SUCH AUTHOR OR DEVELOPER HAD 
--     ADVANCE NOTICE OF THE POSSIBILITY OF SUCH DAMAGES. 
-- 
-- Contributors:
-- Gradient Systems
--
alter table call_center add constraint cc_d1 foreign key  (cc_closed_date_sk) references date_dim (d_date_sk);
alter table call_center add constraint cc_d2 foreign key  (cc_open_date_sk) references date_dim (d_date_sk);
alter table catalog_page add constraint cp_d1 foreign key  (cp_end_date_sk) references date_dim (d_date_sk);
-- alter table catalog_page add constraint cp_p foreign key  (cp_promo_id) references promotion (p_promo_sk);
alter table catalog_page add constraint cp_d2 foreign key  (cp_start_date_sk) references date_dim (d_date_sk);
alter table catalog_returns add constraint cr_cc foreign key  (cr_call_center_sk) references call_center (cc_call_center_sk);
alter table catalog_returns add constraint cr_cp foreign key  (cr_catalog_page_sk) references catalog_page (cp_catalog_page_sk);
alter table catalog_returns add constraint cr_i foreign key  (cr_item_sk) references item (i_item_sk);
alter table catalog_returns add constraint cr_r foreign key  (cr_reason_sk) references reason (r_reason_sk);
alter table catalog_returns add constraint cr_a1 foreign key  (cr_refunded_addr_sk) references customer_address (ca_address_sk);
alter table catalog_returns add constraint cr_cd1 foreign key  (cr_refunded_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table catalog_returns add constraint cr_c1 foreign key  (cr_refunded_customer_sk) references customer (c_customer_sk);
alter table catalog_returns add constraint cr_hd1 foreign key  (cr_refunded_hdemo_sk) references household_demographics (hd_demo_sk);
alter table catalog_returns add constraint cr_d1 foreign key  (cr_returned_date_sk) references date_dim (d_date_sk);
alter table catalog_returns add constraint cr_t foreign key  (cr_returned_time_sk) references time_dim (t_time_sk);
alter table catalog_returns add constraint cr_a2 foreign key  (cr_returning_addr_sk) references customer_address (ca_address_sk);
alter table catalog_returns add constraint cr_cd2 foreign key  (cr_returning_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table catalog_returns add constraint cr_c2 foreign key  (cr_returning_customer_sk) references customer (c_customer_sk);
alter table catalog_returns add constraint cr_hd2 foreign key  (cr_returning_hdemo_sk) references household_demographics (hd_demo_sk);
-- alter table catalog_returns add constraint cr_d2 foreign key  (cr_ship_date_sk) references date_dim (d_date_sk);
alter table catalog_returns add constraint cr_sm foreign key  (cr_ship_mode_sk) references ship_mode (sm_ship_mode_sk);
alter table catalog_returns add constraint cr_w2 foreign key  (cr_warehouse_sk) references warehouse (w_warehouse_sk);
alter table catalog_sales add constraint cs_b_a foreign key  (cs_bill_addr_sk) references customer_address (ca_address_sk);
alter table catalog_sales add constraint cs_b_cd foreign key  (cs_bill_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table catalog_sales add constraint cs_b_c foreign key  (cs_bill_customer_sk) references customer (c_customer_sk);
alter table catalog_sales add constraint cs_b_hd foreign key  (cs_bill_hdemo_sk) references household_demographics (hd_demo_sk);
alter table catalog_sales add constraint cs_cc foreign key  (cs_call_center_sk) references call_center (cc_call_center_sk); 
alter table catalog_sales add constraint cs_cp foreign key  (cs_catalog_page_sk) references catalog_page (cp_catalog_page_sk);
alter table catalog_sales add constraint cs_i foreign key  (cs_item_sk) references item (i_item_sk);
alter table catalog_sales add constraint cs_p foreign key  (cs_promo_sk) references promotion (p_promo_sk);
alter table catalog_sales add constraint cs_s_a foreign key  (cs_ship_addr_sk) references customer_address (ca_address_sk);
alter table catalog_sales add constraint cs_s_cd foreign key  (cs_ship_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table catalog_sales add constraint cs_s_c foreign key  (cs_ship_customer_sk) references customer (c_customer_sk);
alter table catalog_sales add constraint cs_d1 foreign key  (cs_ship_date_sk) references date_dim (d_date_sk);
alter table catalog_sales add constraint cs_s_hd foreign key  (cs_ship_hdemo_sk) references household_demographics (hd_demo_sk);
alter table catalog_sales add constraint cs_sm foreign key  (cs_ship_mode_sk) references ship_mode (sm_ship_mode_sk);
alter table catalog_sales add constraint cs_d2 foreign key  (cs_sold_date_sk) references date_dim (d_date_sk);
alter table catalog_sales add constraint cs_t foreign key  (cs_sold_time_sk) references time_dim (t_time_sk);
alter table catalog_sales add constraint cs_w foreign key  (cs_warehouse_sk) references warehouse (w_warehouse_sk);
alter table customer add constraint c_a foreign key  (c_current_addr_sk) references customer_address (ca_address_sk);
alter table customer add constraint c_cd foreign key  (c_current_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table customer add constraint c_hd foreign key  (c_current_hdemo_sk) references household_demographics (hd_demo_sk);
alter table customer add constraint c_fsd foreign key  (c_first_sales_date_sk) references date_dim (d_date_sk);
alter table customer add constraint c_fsd2 foreign key  (c_first_shipto_date_sk) references date_dim (d_date_sk);
alter table household_demographics add constraint hd_ib foreign key  (hd_income_band_sk) references income_band (ib_income_band_sk); 
alter table inventory add constraint inv_d foreign key  (inv_date_sk) references date_dim (d_date_sk);
alter table inventory add constraint inv_i foreign key  (inv_item_sk) references item (i_item_sk);
alter table inventory add constraint inv_w foreign key  (inv_warehouse_sk) references warehouse (w_warehouse_sk);
alter table promotion add constraint p_end_date foreign key  (p_end_date_sk) references date_dim (d_date_sk);
alter table promotion add constraint p_i foreign key  (p_item_sk) references item (i_item_sk);
alter table promotion add constraint p_start_date foreign key  (p_start_date_sk) references date_dim (d_date_sk);
alter table store add constraint s_close_date foreign key  (s_closed_date_sk) references date_dim (d_date_sk);
alter table store_returns add constraint sr_a foreign key  (sr_addr_sk) references customer_address (ca_address_sk);
alter table store_returns add constraint sr_cd foreign key  (sr_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table store_returns add constraint sr_c foreign key  (sr_customer_sk) references customer (c_customer_sk);
alter table store_returns add constraint sr_hd foreign key  (sr_hdemo_sk) references household_demographics (hd_demo_sk);
alter table store_returns add constraint sr_i foreign key  (sr_item_sk) references item (i_item_sk);
alter table store_returns add constraint sr_r foreign key  (sr_reason_sk) references reason (r_reason_sk);
alter table store_returns add constraint sr_ret_d foreign key  (sr_returned_date_sk) references date_dim (d_date_sk);
alter table store_returns add constraint sr_t foreign key  (sr_return_time_sk) references time_dim (t_time_sk);
alter table store_returns add constraint sr_s foreign key  (sr_store_sk) references store (s_store_sk);
alter table store_sales add constraint ss_a foreign key  (ss_addr_sk) references customer_address (ca_address_sk);
alter table store_sales add constraint ss_cd foreign key  (ss_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table store_sales add constraint ss_c foreign key  (ss_customer_sk) references customer (c_customer_sk);
alter table store_sales add constraint ss_hd foreign key  (ss_hdemo_sk) references household_demographics (hd_demo_sk);
alter table store_sales add constraint ss_i foreign key  (ss_item_sk) references item (i_item_sk);
alter table store_sales add constraint ss_p foreign key  (ss_promo_sk) references promotion (p_promo_sk);
alter table store_sales add constraint ss_d foreign key  (ss_sold_date_sk) references date_dim (d_date_sk);
alter table store_sales add constraint ss_t foreign key  (ss_sold_time_sk) references time_dim (t_time_sk);
alter table store_sales add constraint ss_s foreign key  (ss_store_sk) references store (s_store_sk);
alter table web_page add constraint wp_ad foreign key  (wp_access_date_sk) references date_dim (d_date_sk);
alter table web_page add constraint wp_cd foreign key  (wp_creation_date_sk) references date_dim (d_date_sk);
alter table web_returns add constraint wr_i foreign key  (wr_item_sk) references item (i_item_sk);
alter table web_returns add constraint wr_r foreign key  (wr_reason_sk) references reason (r_reason_sk);
alter table web_returns add constraint wr_ref_a foreign key  (wr_refunded_addr_sk) references customer_address (ca_address_sk);
alter table web_returns add constraint wr_ref_cd foreign key  (wr_refunded_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table web_returns add constraint wr_ref_c foreign key  (wr_refunded_customer_sk) references customer (c_customer_sk);
alter table web_returns add constraint wr_ref_hd foreign key  (wr_refunded_hdemo_sk) references household_demographics (hd_demo_sk);
alter table web_returns add constraint wr_ret_d foreign key  (wr_returned_date_sk) references date_dim (d_date_sk);
alter table web_returns add constraint wr_ret_t foreign key  (wr_returned_time_sk) references time_dim (t_time_sk);
alter table web_returns add constraint wr_ret_a foreign key  (wr_returning_addr_sk) references customer_address (ca_address_sk);
alter table web_returns add constraint wr_ret_cd foreign key  (wr_returning_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table web_returns add constraint wr_ret_c foreign key  (wr_returning_customer_sk) references customer (c_customer_sk);
alter table web_returns add constraint wr_ret_hd foreign key  (wr_returning_hdemo_sk) references household_demographics (hd_demo_sk);
alter table web_returns add constraint wr_wp foreign key  (wr_web_page_sk) references web_page (wp_web_page_sk);
alter table web_sales add constraint ws_b_a foreign key  (ws_bill_addr_sk) references customer_address (ca_address_sk);
alter table web_sales add constraint ws_b_cd foreign key  (ws_bill_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table web_sales add constraint ws_b_c foreign key  (ws_bill_customer_sk) references customer (c_customer_sk);
alter table web_sales add constraint ws_b_hd foreign key  (ws_bill_hdemo_sk) references household_demographics (hd_demo_sk);
alter table web_sales add constraint ws_i foreign key  (ws_item_sk) references item (i_item_sk);
alter table web_sales add constraint ws_p foreign key  (ws_promo_sk) references promotion (p_promo_sk);
alter table web_sales add constraint ws_s_a foreign key  (ws_ship_addr_sk) references customer_address (ca_address_sk);
alter table web_sales add constraint ws_s_cd foreign key  (ws_ship_cdemo_sk) references customer_demographics (cd_demo_sk);
alter table web_sales add constraint ws_s_c foreign key  (ws_ship_customer_sk) references customer (c_customer_sk);
alter table web_sales add constraint ws_s_d foreign key  (ws_ship_date_sk) references date_dim (d_date_sk);
alter table web_sales add constraint ws_s_hd foreign key  (ws_ship_hdemo_sk) references household_demographics (hd_demo_sk);
alter table web_sales add constraint ws_sm foreign key  (ws_ship_mode_sk) references ship_mode (sm_ship_mode_sk);
alter table web_sales add constraint ws_d2 foreign key  (ws_sold_date_sk) references date_dim (d_date_sk);
alter table web_sales add constraint ws_t foreign key  (ws_sold_time_sk) references time_dim (t_time_sk);
alter table web_sales add constraint ws_w2 foreign key  (ws_warehouse_sk) references warehouse (w_warehouse_sk);
alter table web_sales add constraint ws_wp foreign key  (ws_web_page_sk) references web_page (wp_web_page_sk);
alter table web_sales add constraint ws_ws foreign key  (ws_web_site_sk) references web_site (web_site_sk);
alter table web_site add constraint web_d1 foreign key  (web_close_date_sk) references date_dim (d_date_sk);
alter table web_site add constraint web_d2 foreign key  (web_open_date_sk) references date_dim (d_date_sk);

-- Legal Notice 
-- 
-- This document and associated source code (the "Work") is a part of a 
-- benchmark specification maintained by the TPC. 
-- 
-- The TPC reserves all right, title, and interest to the Work as provided 
-- under U.S. and international laws, including without limitation all patent 
-- and trademark rights therein. 
-- 
-- No Warranty 
-- 
-- 1.1 TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE INFORMATION 
--     CONTAINED HEREIN IS PROVIDED "AS IS" AND WITH ALL FAULTS, AND THE 
--     AUTHORS AND DEVELOPERS OF THE WORK HEREBY DISCLAIM ALL OTHER 
--     WARRANTIES AND CONDITIONS, EITHER EXPRESS, IMPLIED OR STATUTORY, 
--     INCLUDING, BUT NOT LIMITED TO, ANY (IF ANY) IMPLIED WARRANTIES, 
--     DUTIES OR CONDITIONS OF MERCHANTABILITY, OF FITNESS FOR A PARTICULAR 
--     PURPOSE, OF ACCURACY OR COMPLETENESS OF RESPONSES, OF RESULTS, OF 
--     WORKMANLIKE EFFORT, OF LACK OF VIRUSES, AND OF LACK OF NEGLIGENCE. 
--     ALSO, THERE IS NO WARRANTY OR CONDITION OF TITLE, QUIET ENJOYMENT, 
--     QUIET POSSESSION, CORRESPONDENCE TO DESCRIPTION OR NON-INFRINGEMENT 
--     WITH REGARD TO THE WORK. 
-- 1.2 IN NO EVENT WILL ANY AUTHOR OR DEVELOPER OF THE WORK BE LIABLE TO 
--     ANY OTHER PARTY FOR ANY DAMAGES, INCLUDING BUT NOT LIMITED TO THE 
--     COST OF PROCURING SUBSTITUTE GOODS OR SERVICES, LOST PROFITS, LOSS 
--     OF USE, LOSS OF DATA, OR ANY INCIDENTAL, CONSEQUENTIAL, DIRECT, 
--     INDIRECT, OR SPECIAL DAMAGES WHETHER UNDER CONTRACT, TORT, WARRANTY,
--     OR OTHERWISE, ARISING IN ANY WAY OUT OF THIS OR ANY OTHER AGREEMENT 
--     RELATING TO THE WORK, WHETHER OR NOT SUCH AUTHOR OR DEVELOPER HAD 
--     ADVANCE NOTICE OF THE POSSIBILITY OF SUCH DAMAGES. 
-- 
-- Contributors:
-- Gradient Systems
--
-- Legal Notice 
-- 
-- This document and associated source code (the "Work") is a part of a 
-- benchmark specification maintained by the TPC. 
-- 
-- The TPC reserves all right, title, and interest to the Work as provided 
-- under U.S. and international laws, including without limitation all patent 
-- and trademark rights therein. 
-- 
-- No Warranty 
-- 
-- 1.1 TO THE MAXIMUM EXTENT PERMITTED BY APPLICABLE LAW, THE INFORMATION 
--     CONTAINED HEREIN IS PROVIDED "AS IS" AND WITH ALL FAULTS, AND THE 
--     AUTHORS AND DEVELOPERS OF THE WORK HEREBY DISCLAIM ALL OTHER 
--     WARRANTIES AND CONDITIONS, EITHER EXPRESS, IMPLIED OR STATUTORY, 
--     INCLUDING, BUT NOT LIMITED TO, ANY (IF ANY) IMPLIED WARRANTIES, 
--     DUTIES OR CONDITIONS OF MERCHANTABILITY, OF FITNESS FOR A PARTICULAR 
--     PURPOSE, OF ACCURACY OR COMPLETENESS OF RESPONSES, OF RESULTS, OF 
--     WORKMANLIKE EFFORT, OF LACK OF VIRUSES, AND OF LACK OF NEGLIGENCE. 
--     ALSO, THERE IS NO WARRANTY OR CONDITION OF TITLE, QUIET ENJOYMENT, 
--     QUIET POSSESSION, CORRESPONDENCE TO DESCRIPTION OR NON-INFRINGEMENT 
--     WITH REGARD TO THE WORK. 
-- 1.2 IN NO EVENT WILL ANY AUTHOR OR DEVELOPER OF THE WORK BE LIABLE TO 
--     ANY OTHER PARTY FOR ANY DAMAGES, INCLUDING BUT NOT LIMITED TO THE 
--     COST OF PROCURING SUBSTITUTE GOODS OR SERVICES, LOST PROFITS, LOSS 
--     OF USE, LOSS OF DATA, OR ANY INCIDENTAL, CONSEQUENTIAL, DIRECT, 
--     INDIRECT, OR SPECIAL DAMAGES WHETHER UNDER CONTRACT, TORT, WARRANTY,
--     OR OTHERWISE, ARISING IN ANY WAY OUT OF THIS OR ANY OTHER AGREEMENT 
--     RELATING TO THE WORK, WHETHER OR NOT SUCH AUTHOR OR DEVELOPER HAD 
--     ADVANCE NOTICE OF THE POSSIBILITY OF SUCH DAMAGES. 
-- 
-- Contributors:
-- Gradient Systems
--

alter table call_center drop constraint cc_d1;
alter table call_center drop constraint cc_d2;
alter table catalog_page drop constraint cp_d1;
-- alter table catalog_page drop constraint cp_p;
alter table catalog_page drop constraint cp_d2;
alter table catalog_returns drop constraint cr_cc;
alter table catalog_returns drop constraint cr_cp;
alter table catalog_returns drop constraint cr_i;
alter table catalog_returns drop constraint cr_r;
alter table catalog_returns drop constraint cr_a1;
alter table catalog_returns drop constraint cr_cd1;
alter table catalog_returns drop constraint cr_c1;
alter table catalog_returns drop constraint cr_hd1;
alter table catalog_returns drop constraint cr_d1;
alter table catalog_returns drop constraint cr_t;
alter table catalog_returns drop constraint cr_a2;
alter table catalog_returns drop constraint cr_cd2;
alter table catalog_returns drop constraint cr_c2;
alter table catalog_returns drop constraint cr_hd2;
-- alter table catalog_returns drop constraint cr_d2;
alter table catalog_returns drop constraint cr_sm;
alter table catalog_returns drop constraint cr_w2;
alter table catalog_sales drop constraint cs_b_a;
alter table catalog_sales drop constraint cs_b_cd;
alter table catalog_sales drop constraint cs_b_c;
alter table catalog_sales drop constraint cs_b_hd;
alter table catalog_sales drop constraint cs_cc; 
alter table catalog_sales drop constraint cs_cp;
alter table catalog_sales drop constraint cs_i;
alter table catalog_sales drop constraint cs_p;
alter table catalog_sales drop constraint cs_s_a;
alter table catalog_sales drop constraint cs_s_cd;
alter table catalog_sales drop constraint cs_s_c;
alter table catalog_sales drop constraint cs_d1;
alter table catalog_sales drop constraint cs_s_hd;
alter table catalog_sales drop constraint cs_sm;
alter table catalog_sales drop constraint cs_d2;
alter table catalog_sales drop constraint cs_t;
alter table catalog_sales drop constraint cs_w;
alter table customer drop constraint c_a;
alter table customer drop constraint c_cd;
alter table customer drop constraint c_hd;
alter table customer drop constraint c_fsd;
alter table customer drop constraint c_fsd2;
alter table household_demographics drop constraint hd_ib; 
alter table inventory drop constraint inv_d;
alter table inventory drop constraint inv_i;
alter table inventory drop constraint inv_w;
alter table promotion drop constraint p_end_date;
alter table promotion drop constraint p_i;
alter table promotion drop constraint p_start_date;
alter table store drop constraint s_close_date;
alter table store_returns drop constraint sr_a;
alter table store_returns drop constraint sr_cd;
alter table store_returns drop constraint sr_c;
alter table store_returns drop constraint sr_hd;
alter table store_returns drop constraint sr_i;
alter table store_returns drop constraint sr_r;
alter table store_returns drop constraint sr_ret_d;
alter table store_returns drop constraint sr_t;
alter table store_returns drop constraint sr_s;
alter table store_sales drop constraint ss_a;
alter table store_sales drop constraint ss_cd;
alter table store_sales drop constraint ss_c;
alter table store_sales drop constraint ss_hd;
alter table store_sales drop constraint ss_i;
alter table store_sales drop constraint ss_p;
alter table store_sales drop constraint ss_d;
alter table store_sales drop constraint ss_t;
alter table store_sales drop constraint ss_s;
alter table web_page drop constraint wp_ad;
alter table web_page drop constraint wp_cd;
alter table web_returns drop constraint wr_i;
alter table web_returns drop constraint wr_r;
alter table web_returns drop constraint wr_ref_a;
alter table web_returns drop constraint wr_ref_cd;
alter table web_returns drop constraint wr_ref_c;
alter table web_returns drop constraint wr_ref_hd;
alter table web_returns drop constraint wr_ret_d;
alter table web_returns drop constraint wr_ret_t;
alter table web_returns drop constraint wr_ret_a;
alter table web_returns drop constraint wr_ret_cd;
alter table web_returns drop constraint wr_ret_c;
alter table web_returns drop constraint wr_ret_hd;
alter table web_returns drop constraint wr_wp;
alter table web_sales drop constraint ws_b_a;
alter table web_sales drop constraint ws_b_cd;
alter table web_sales drop constraint ws_b_c;
alter table web_sales drop constraint ws_b_hd;
alter table web_sales drop constraint ws_i;
alter table web_sales drop constraint ws_p;
alter table web_sales drop constraint ws_s_a;
alter table web_sales drop constraint ws_s_cd;
alter table web_sales drop constraint ws_s_c;
alter table web_sales drop constraint ws_s_d;
alter table web_sales drop constraint ws_s_hd;
alter table web_sales drop constraint ws_sm;
alter table web_sales drop constraint ws_d2;
alter table web_sales drop constraint ws_t;
alter table web_sales drop constraint ws_w2;
alter table web_sales drop constraint ws_wp;
alter table web_sales drop constraint ws_ws;
alter table web_site drop constraint web_d1;
alter table web_site drop constraint web_d2;