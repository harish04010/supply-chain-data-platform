-- Weeks of supply at the latest snapshot: on hand / average weekly sales over the trailing 4 weeks.
with latest as (select max(date_day) as d from {{ ref('fct_inventory_daily') }}),
onhand as (
    select s.category, l.location_type, sum(i.on_hand) as on_hand
    from {{ ref('fct_inventory_daily') }} i join latest on i.date_day = latest.d
    join {{ ref('dim_sku') }} s using (sku) join {{ ref('dim_location') }} l using (location_id) group by all),
rate as (
    select s.category, sum(f.units) / 4.0 as weekly_units
    from {{ ref('fct_sales_daily') }} f join latest on f.date_day > latest.d - interval 28 day
    join {{ ref('dim_sku') }} s using (sku) group by all)
select o.category, o.location_type, o.on_hand, r.weekly_units, o.on_hand / nullif(r.weekly_units, 0) as weeks_of_supply
from onhand o join rate r using (category) order by 1, 2
