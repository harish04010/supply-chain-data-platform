-- Sell-through: units sold in the week / (units sold + store on-hand at week end).
with sold as (
    select d.week_start, s.category, sum(f.units) as units_sold
    from {{ ref('fct_sales_daily') }} f join {{ ref('dim_date') }} d using (date_day) join {{ ref('dim_sku') }} s using (sku) group by all),
ending as (
    select d.week_start, s.category, sum(i.on_hand) as ending_on_hand
    from {{ ref('fct_inventory_daily') }} i join {{ ref('dim_date') }} d using (date_day)
    join {{ ref('dim_sku') }} s using (sku) join {{ ref('dim_location') }} l using (location_id)
    where l.location_type = 'Store' and d.day_of_week = 6 group by all)
select week_start, category, units_sold, ending_on_hand, units_sold / (units_sold + ending_on_hand) as sell_through
from sold join ending using (week_start, category) order by 1, 2
