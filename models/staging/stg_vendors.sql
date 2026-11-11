select vendor_id, vendor_name, lead_time_days::int as lead_time_days
from read_csv('{{ var("raw_path") }}/vendors.csv', header = true, all_varchar = true)
