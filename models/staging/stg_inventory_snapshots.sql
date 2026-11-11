-- The WMS snapshot feed sometimes loads the same day twice. Keep one row per
-- date, location and SKU; audit_snapshot_duplicates records what was dropped.
select snapshot_date::date as snapshot_date, location_id, sku, on_hand::int as on_hand
from read_csv('{{ var("raw_path") }}/inventory_snapshots.csv', header = true, all_varchar = true)
qualify row_number() over (partition by snapshot_date, location_id, sku order by on_hand) = 1
