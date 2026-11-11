select * from {{ ref('fct_inventory_daily') }} where on_hand < 0
