select receipt_id, po_number, sku, dc_id, receipt_date::date as receipt_date, received_qty::int as received_qty
from read_csv('{{ var("raw_path") }}/dc_receipts.csv', header = true, all_varchar = true)
