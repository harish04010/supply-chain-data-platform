select ship_date::date as ship_date, from_dc, store_id, sku, units::int as units
from read_csv('{{ var("raw_path") }}/store_shipments.csv', header = true, all_varchar = true)
