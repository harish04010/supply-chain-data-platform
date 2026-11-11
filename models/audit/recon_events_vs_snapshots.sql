-- Source-to-target reconciliation: the day-over-day change in each snapshot must equal
-- the net of that day's movement events. Any row here is an unexplained difference.
with snap as (
    select date_day, location_id, sku, on_hand - lag(on_hand) over (partition by location_id, sku order by date_day) as snapshot_change
    from {{ ref('fct_inventory_daily') }}),
ev as (
    select event_date as date_day, location_id, sku, sum(quantity) as event_change
    from {{ ref('stg_inventory_events') }} group by all)
select s.date_day, s.location_id, s.sku, s.snapshot_change, coalesce(e.event_change, 0) as event_change
from snap s left join ev e using (date_day, location_id, sku)
where s.snapshot_change is not null and s.snapshot_change <> coalesce(e.event_change, 0)
