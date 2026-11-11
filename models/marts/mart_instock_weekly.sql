-- In-stock: share of store x SKU x day with on-hand above zero.
select d.week_start, l.region, s.category,
       avg((i.on_hand > 0)::int) as instock_rate, count(*) as store_sku_days
from {{ ref('fct_inventory_daily') }} i
join {{ ref('dim_location') }} l using (location_id)
join {{ ref('dim_sku') }} s using (sku)
join {{ ref('dim_date') }} d on d.date_day = i.date_day
where l.location_type = 'Store'
group by all order by 1, 2, 3
