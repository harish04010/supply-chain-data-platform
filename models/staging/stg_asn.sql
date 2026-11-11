select asn_id, po_number, sku, dc_id, ship_date::date as ship_date, shipped_qty::int as shipped_qty
from read_csv('{{ var("raw_path") }}/asn.csv', header = true, all_varchar = true)
