select po_number, po_line::int as po_line, vendor_id, sku, dc_id, order_date::date as order_date,
       promised_date::date as promised_date, ordered_qty::int as ordered_qty, unit_cost::decimal(10,2) as unit_cost
from read_csv('{{ var("raw_path") }}/purchase_orders.csv', header = true, all_varchar = true)
