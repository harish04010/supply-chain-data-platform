select sale_date::date as sale_date, store_id, sku, units::int as units, net_sales::decimal(12,2) as net_sales
from read_csv('{{ var("raw_path") }}/pos_sales.csv', header = true, all_varchar = true)
