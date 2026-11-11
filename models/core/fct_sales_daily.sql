select sale_date as date_day, store_id as location_id, sku, units, net_sales from {{ ref('stg_pos_sales') }}
