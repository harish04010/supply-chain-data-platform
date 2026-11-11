select s.*, v.vendor_name from {{ ref('stg_skus') }} s left join {{ ref('stg_vendors') }} v using (vendor_id)
