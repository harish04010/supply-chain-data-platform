-- Source-level check: snapshot rows that arrived more than once per date, location and SKU.
select snapshot_date::date as snapshot_date, location_id, sum(n) as rows_loaded, count(distinct sku) as skus
from (select snapshot_date, location_id, sku, count(*) as n
      from read_csv('{{ var("raw_path") }}/inventory_snapshots.csv', header = true, all_varchar = true)
      group by all having count(*) > 1)
group by all
