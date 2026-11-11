select sku, category, description, vendor_id, unit_cost::decimal(10,2) as unit_cost, retail_price::decimal(10,2) as retail_price
from read_csv('{{ var("raw_path") }}/skus.csv', header = true, all_varchar = true)
