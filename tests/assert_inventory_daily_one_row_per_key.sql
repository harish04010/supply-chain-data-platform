select date_day, location_id, sku, count(*) from {{ ref('fct_inventory_daily') }} group by all having count(*) > 1
