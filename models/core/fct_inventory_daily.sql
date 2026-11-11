select snapshot_date as date_day, location_id, sku, on_hand from {{ ref('stg_inventory_snapshots') }}
