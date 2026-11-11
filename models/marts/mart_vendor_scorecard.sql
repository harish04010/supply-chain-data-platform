select v.vendor_id, v.vendor_name, count(*) as po_lines,
       count(*) filter (where is_received) as received_lines,
       avg(is_otif::int) filter (where is_received) as otif_rate,
       avg(is_on_time::int) filter (where is_received) as on_time_rate,
       sum(received_qty) / sum(ordered_qty) filter (where is_received) as fill_rate,
       avg(days_late) filter (where is_received) as avg_days_late,
       avg(asn_mismatch::int) filter (where is_received) as asn_mismatch_rate
from {{ ref('fct_po_lines') }} p join {{ ref('dim_vendor') }} v using (vendor_id)
group by all order by otif_rate
