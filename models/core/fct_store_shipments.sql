select ship_date as date_day, from_dc, store_id, sku, units from {{ ref('stg_store_shipments') }}
