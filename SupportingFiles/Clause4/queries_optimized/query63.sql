with items as (
    -- dynamic sampling: Oracle counts the selected items (about 1900) instead of estimating 5
    select /*+ dynamic_sampling(item 4) */ i_item_sk, i_manager_id
    from item
    where (i_category in ('Books','Children','Electronics')
           and i_class in ('personal','portable','reference','self-help')
           and i_brand in ('scholaramalgamalg #14','scholaramalgamalg #7',
                           'exportiunivamalg #9','scholaramalgamalg #9'))
       or (i_category in ('Women','Music','Men')
           and i_class in ('accessories','classical','fragrances','pants')
           and i_brand in ('amalgimporto #1','edu packscholar #1','exportiimporto #1',
                           'importoamalg #1'))),
months as (
    select d_date_sk, d_moy
    from date_dim
    where d_month_seq between 1200 and 1211),
monthly as (
    -- the join with store only removed sales without a store
    select i.i_manager_id, m.d_moy, sum(ss.ss_sales_price) sum_sales
    from store_sales ss
    join items i on ss.ss_item_sk = i.i_item_sk
    join months m on ss.ss_sold_date_sk = m.d_date_sk
    where ss.ss_store_sk is not null
    group by i.i_manager_id, m.d_moy),
with_avg as (
    select i_manager_id, sum_sales,
           avg(sum_sales) over (partition by i_manager_id) avg_monthly_sales
    from monthly)
select i_manager_id, sum_sales, avg_monthly_sales
from with_avg
where avg_monthly_sales > 0
  and abs(sum_sales - avg_monthly_sales) > 0.1 * avg_monthly_sales
order by i_manager_id, avg_monthly_sales, sum_sales
fetch first 100 rows only;
