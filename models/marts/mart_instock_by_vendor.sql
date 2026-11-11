-- Connects supplier performance to availability: in-stock for each vendor's SKUs at the DCs and in stores.
-- Stores are buffered by DC stock, so a vendor's problems show up at the DC first.
select s.vendor_id, v.vendor_name,
       avg((i.on_hand > 0)::int) filter (where l.location_type = 'DC') as dc_instock_rate,
       avg((i.on_hand > 0)::int) filter (where l.location_type = 'Store') as instock_rate,
       count(distinct i.sku) as skus
from {{ ref('fct_inventory_daily') }} i
join {{ ref('dim_location') }} l using (location_id)
join {{ ref('dim_sku') }} s using (sku)
join {{ ref('dim_vendor') }} v on v.vendor_id = s.vendor_id
group by all order by dc_instock_rate
